"""Tests for :mod:`blive.adapters.ig.instrument_resolver`.

Covers DD-8 §6 public surface: epic guessing per the §3 family table,
``/markets/{epic}`` happy-path, ``/markets?searchTerm=…`` fallback,
ambiguity / not-resolvable raises, caching, precision lookup per ADR-037.

Uses :class:`httpx.MockTransport` to simulate IG REST responses.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable

import httpx
import pytest

from blive.adapters.clock.sim import SimClock
from blive.adapters.ig.client import IGClient
from blive.adapters.ig.credentials import IGCredentials
from blive.adapters.ig.instrument_resolver import (
    IGInstrumentResolver,
    IGMarketMetadata,
    InstrumentAmbiguous,
    InstrumentNotResolvable,
    _guess_epic,
)
from blive.adapters.shared.rate_limiter import (
    RateLimitBucket,
    RateLimitConfig,
    TokenBucketRateLimiter,
)
from blive.domain.types import AssetClass, Instrument

# --- Fixtures ---------------------------------------------------------------


@pytest.fixture
def cac40_cfd() -> Instrument:
    """Phase 1 bridge instrument (ADR-039)."""
    return Instrument(
        symbol="CAC40",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.INDEX,
        tradability="cfd",
    )


def _login_response() -> httpx.Response:
    return httpx.Response(
        status_code=200,
        headers={"CST": "test-cst", "X-SECURITY-TOKEN": "test-token"},
        json={"accountId": "ACC123"},
    )


def _market_response(
    epic: str = "IX.D.CAC40.CASH.IP",
    *,
    name: str = "France 40",
    currency: str = "EUR",
    lot_size: float = 1.0,
    min_deal_size: float = 0.1,
) -> httpx.Response:
    return httpx.Response(
        status_code=200,
        json={
            "instrument": {
                "epic": epic,
                "name": name,
                "currencies": [{"code": currency, "isDefault": True}],
                "lotSize": lot_size,
            },
            "dealingRules": {
                "minDealSize": {"value": min_deal_size, "unit": "POINTS"},
            },
            "snapshot": {},
        },
    )


def _not_found_response() -> httpx.Response:
    return httpx.Response(
        status_code=404,
        json={"errorCode": "error.invalid.instrument"},
    )


def _make_resolver(
    handler: Callable[[httpx.Request], httpx.Response],
) -> tuple[IGInstrumentResolver, IGClient]:
    clock = SimClock(start=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc))
    creds = IGCredentials(
        api_key="k", username="u", password="p", account_id="a", environment="demo"
    )
    rate_limiter = TokenBucketRateLimiter(
        clock=clock,
        config=RateLimitConfig(
            buckets={
                "general": RateLimitBucket(capacity=100, refill_per_second=Decimal("10")),
                "trading": RateLimitBucket(capacity=100, refill_per_second=Decimal("10")),
            }
        ),
    )
    transport = httpx.MockTransport(handler)
    client = IGClient(
        credentials=creds, rate_limiter=rate_limiter, clock=clock, transport=transport
    )
    return IGInstrumentResolver(client), client


# --- Epic guessing (pure function) -----------------------------------------


def test_guess_epic_for_index_cfd() -> None:
    inst = Instrument(
        symbol="CAC40",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.INDEX,
        tradability="cfd",
    )
    assert _guess_epic(inst) == "IX.D.CAC40.CASH.IP"


def test_guess_epic_for_equity_cfd() -> None:
    inst = Instrument(
        symbol="AAPL",
        venue="XNAS",
        currency="USD",
        asset_class=AssetClass.EQUITY,
        tradability="cfd",
    )
    assert _guess_epic(inst) == "KC.D.AAPL.CASH.IP"


def test_guess_epic_for_etf_cfd_uses_kc_family() -> None:
    """DD-8 §3: IG treats ETFs in the cash-equity family."""
    inst = Instrument(
        symbol="SPY",
        venue="ARCX",
        currency="USD",
        asset_class=AssetClass.ETF,
        tradability="cfd",
    )
    assert _guess_epic(inst) == "KC.D.SPY.CASH.IP"


def test_guess_epic_for_fx_cfd() -> None:
    inst = Instrument(
        symbol="EURUSD",
        venue="IDEALPRO",
        currency="USD",
        asset_class=AssetClass.FX,
        tradability="cfd",
    )
    assert _guess_epic(inst) == "CS.D.EURUSD.CASH.IP"


def test_guess_epic_rejects_spot() -> None:
    """IG resolver scopes to CFD / spread bet (DD-8 §3); spot raises."""
    inst = Instrument(
        symbol="CAC.PA",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.ETF,
        tradability="spot",
    )
    with pytest.raises(InstrumentNotResolvable, match="spot"):
        _guess_epic(inst)


def test_guess_epic_rejects_option() -> None:
    inst = Instrument(
        symbol="SPX",
        venue="OPRA",
        currency="USD",
        asset_class=AssetClass.OPTION,
        tradability="cfd",
    )
    with pytest.raises(InstrumentNotResolvable, match="OPTION"):
        _guess_epic(inst)


# --- Resolution happy path --------------------------------------------------


async def test_resolve_via_guess_returns_epic(cac40_cfd: Instrument) -> None:
    """Phase 1 case: epic guess hits 200 on first try."""
    requests_seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        requests_seen.append(f"{request.method} {path}")
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if path.endswith("/markets/IX.D.CAC40.CASH.IP"):
            return _market_response()
        raise AssertionError(f"unexpected request: {request.method} {path}")

    resolver, client = _make_resolver(handler)
    await client.connect()

    epic = await resolver.resolve(cac40_cfd)
    assert epic == "IX.D.CAC40.CASH.IP"
    # Single market lookup; no search fallback.
    assert any("/markets/IX.D.CAC40.CASH.IP" in r for r in requests_seen)
    assert not any("searchTerm" in r for r in requests_seen)


async def test_resolve_caches_repeated_calls(cac40_cfd: Instrument) -> None:
    """Second resolve() of the same instrument returns from cache."""
    market_calls = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if path.endswith("/markets/IX.D.CAC40.CASH.IP"):
            market_calls[0] += 1
            return _market_response()
        raise AssertionError(f"unexpected request: {request.method} {path}")

    resolver, client = _make_resolver(handler)
    await client.connect()
    await resolver.resolve(cac40_cfd)
    await resolver.resolve(cac40_cfd)
    await resolver.resolve(cac40_cfd)
    assert market_calls[0] == 1, "second/third resolve should hit cache, not the wire"


async def test_clear_cache_invalidates_specific_instrument(cac40_cfd: Instrument) -> None:
    market_calls = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if path.endswith("/markets/IX.D.CAC40.CASH.IP"):
            market_calls[0] += 1
            return _market_response()
        raise AssertionError(f"unexpected request: {request.method} {path}")

    resolver, client = _make_resolver(handler)
    await client.connect()
    await resolver.resolve(cac40_cfd)
    resolver.clear_cache(cac40_cfd)
    await resolver.resolve(cac40_cfd)
    assert market_calls[0] == 2, "clear_cache should force re-fetch"


async def test_clear_cache_all_invalidates_everything(cac40_cfd: Instrument) -> None:
    market_calls = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if path.endswith("/markets/IX.D.CAC40.CASH.IP"):
            market_calls[0] += 1
            return _market_response()
        raise AssertionError(f"unexpected request: {request.method} {path}")

    resolver, client = _make_resolver(handler)
    await client.connect()
    await resolver.resolve(cac40_cfd)
    resolver.clear_cache()  # flush all
    await resolver.resolve(cac40_cfd)
    assert market_calls[0] == 2


# --- Search fallback --------------------------------------------------------


async def test_resolve_falls_back_to_search_on_unknown_instrument() -> None:
    """Symbol that doesn't match the guess is found via /markets?searchTerm."""
    requests_seen: list[str] = []

    inst = Instrument(
        symbol="WEIRDSYM",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.INDEX,
        tradability="cfd",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        requests_seen.append(f"{request.method} {path}")
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if path.endswith("/markets/IX.D.WEIRDSYM.CASH.IP"):
            return _not_found_response()
        if path.endswith("/markets") and request.url.params.get("searchTerm") == "WEIRDSYM":
            return httpx.Response(
                status_code=200,
                json={
                    "markets": [
                        {
                            "epic": "IX.D.WEIRDSYM.DAILY.IP",
                            "instrumentName": "Weird Index",
                            "marketStatus": "TRADEABLE",
                        }
                    ]
                },
            )
        if path.endswith("/markets/IX.D.WEIRDSYM.DAILY.IP"):
            return _market_response(epic="IX.D.WEIRDSYM.DAILY.IP")
        raise AssertionError(f"unexpected request: {request.method} {path}")

    resolver, client = _make_resolver(handler)
    await client.connect()

    epic = await resolver.resolve(inst)
    assert epic == "IX.D.WEIRDSYM.DAILY.IP"
    # First try should have been the cash-suffix guess; then a /markets
    # search; then the metadata fetch on the resolved DAILY epic.
    assert any(
        "/markets/IX.D.WEIRDSYM.CASH.IP" in r for r in requests_seen
    ), f"first try should have been the cash-suffix guess: {requests_seen}"
    assert any(
        "/markets/IX.D.WEIRDSYM.DAILY.IP" in r for r in requests_seen
    ), f"resolved DAILY epic should have triggered a metadata fetch: {requests_seen}"


async def test_search_with_zero_candidates_raises_not_resolvable() -> None:
    inst = Instrument(
        symbol="NOSUCH",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.INDEX,
        tradability="cfd",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if path.endswith("/markets/IX.D.NOSUCH.CASH.IP"):
            return _not_found_response()
        if path.endswith("/markets"):
            return httpx.Response(status_code=200, json={"markets": []})
        raise AssertionError(f"unexpected request: {request.method} {path}")

    resolver, client = _make_resolver(handler)
    await client.connect()

    with pytest.raises(InstrumentNotResolvable, match="no candidates"):
        await resolver.resolve(inst)


async def test_search_with_multiple_candidates_raises_ambiguous() -> None:
    inst = Instrument(
        symbol="DUP",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.INDEX,
        tradability="cfd",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if path.endswith("/markets/IX.D.DUP.CASH.IP"):
            return _not_found_response()
        if path.endswith("/markets"):
            return httpx.Response(
                status_code=200,
                json={
                    "markets": [
                        {"epic": "IX.D.DUP.CASH.IP", "instrumentName": "Dup A"},
                        {"epic": "IX.D.DUP.DAILY.IP", "instrumentName": "Dup B"},
                    ]
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {path}")

    resolver, client = _make_resolver(handler)
    await client.connect()

    with pytest.raises(InstrumentAmbiguous) as excinfo:
        await resolver.resolve(inst)
    assert excinfo.value.instrument == inst
    assert len(excinfo.value.candidates) == 2


async def test_search_filters_candidates_by_family() -> None:
    """Candidates from outside the expected family are filtered out.

    Stateful handler: ``/markets/IX.D.CC.CASH.IP`` returns 404 on the
    initial guess attempt, then returns the metadata payload when the
    search-fallback path re-requests it after filtering.
    """
    inst = Instrument(
        symbol="CC",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.INDEX,
        tradability="cfd",
    )
    market_visits = {"IX.D.CC.CASH.IP": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if path.endswith("/markets/IX.D.CC.CASH.IP"):
            market_visits["IX.D.CC.CASH.IP"] += 1
            if market_visits["IX.D.CC.CASH.IP"] == 1:
                return _not_found_response()
            return _market_response(epic="IX.D.CC.CASH.IP")
        if path.endswith("/markets"):
            return httpx.Response(
                status_code=200,
                json={
                    "markets": [
                        {"epic": "KC.D.CC.CASH.IP"},  # filtered
                        {"epic": "CS.D.CC.CASH.IP"},  # filtered
                        {"epic": "IX.D.CC.CASH.IP"},  # kept
                    ]
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {path}")

    resolver, client = _make_resolver(handler)
    await client.connect()

    epic = await resolver.resolve(inst)
    assert epic == "IX.D.CC.CASH.IP"


# --- Metadata + precision lookup -------------------------------------------


async def test_market_metadata_returns_parsed_response(cac40_cfd: Instrument) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if path.endswith("/markets/IX.D.CAC40.CASH.IP"):
            return _market_response(
                epic="IX.D.CAC40.CASH.IP",
                name="France 40",
                currency="EUR",
                lot_size=1.0,
                min_deal_size=0.5,
            )
        raise AssertionError(f"unexpected request: {request.method} {path}")

    resolver, client = _make_resolver(handler)
    await client.connect()

    meta = await resolver.market_metadata(cac40_cfd)
    assert isinstance(meta, IGMarketMetadata)
    assert meta.epic == "IX.D.CAC40.CASH.IP"
    assert meta.name == "France 40"
    assert meta.currency == "EUR"
    assert meta.lot_size == Decimal("1.0")
    assert meta.min_deal_size == Decimal("0.5")


async def test_precision_for_cfd_uses_min_deal_size(cac40_cfd: Instrument) -> None:
    """ADR-037: CFD precision = market.dealingRules.minDealSize."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if path.endswith("/markets/IX.D.CAC40.CASH.IP"):
            return _market_response(min_deal_size=0.1)
        raise AssertionError(f"unexpected request: {request.method} {path}")

    resolver, client = _make_resolver(handler)
    await client.connect()
    precision = await resolver.precision_for(cac40_cfd)
    assert precision == Decimal("0.1")


async def test_precision_for_spot_returns_one() -> None:
    """ADR-037: spot uses integer-share rounding (Decimal('1'))."""
    inst = Instrument(
        symbol="CAC.PA",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.ETF,
        tradability="spot",
    )

    def handler(_: httpx.Request) -> httpx.Response:
        return _login_response()

    resolver, client = _make_resolver(handler)
    await client.connect()
    # Note: doesn't hit the wire; spot precision is hardcoded.
    precision = await resolver.precision_for(inst)
    assert precision == Decimal("1")


# --- Malformed response handling -------------------------------------------


async def test_market_response_missing_instrument_raises(cac40_cfd: Instrument) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if path.endswith("/markets/IX.D.CAC40.CASH.IP"):
            return httpx.Response(status_code=200, json={"snapshot": {}})  # no instrument key
        raise AssertionError(f"unexpected request: {request.method} {path}")

    resolver, client = _make_resolver(handler)
    await client.connect()
    from blive.adapters.ig.client import IGRequestInvalid

    with pytest.raises(IGRequestInvalid, match="missing instrument"):
        await resolver.resolve(cac40_cfd)


async def test_market_response_missing_min_deal_size_raises(cac40_cfd: Instrument) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if path.endswith("/markets/IX.D.CAC40.CASH.IP"):
            return httpx.Response(
                status_code=200,
                json={
                    "instrument": {
                        "epic": "IX.D.CAC40.CASH.IP",
                        "name": "France 40",
                        "currencies": [{"code": "EUR"}],
                        "lotSize": 1.0,
                    },
                    "dealingRules": {},  # missing minDealSize
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {path}")

    resolver, client = _make_resolver(handler)
    await client.connect()
    from blive.adapters.ig.client import IGRequestInvalid

    with pytest.raises(IGRequestInvalid, match="minDealSize"):
        await resolver.resolve(cac40_cfd)
