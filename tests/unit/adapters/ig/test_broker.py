"""Tests for :mod:`blive.adapters.ig.broker`.

Covers M2-IG.3 read-side surface: connect/disconnect with PUT /session
account switch, positions / account_snapshot / open_orders parsers,
events queue, and NotImplementedError stubs for the M2-IG.4 write
methods. All wire activity mocked via :class:`httpx.MockTransport`.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable
from uuid import uuid4

import httpx
import pytest

from blive.adapters.clock.sim import SimClock
from blive.adapters.ig.broker import (
    IGBroker,
    _epic_to_asset_class,
    _epic_to_symbol,
    _hex_like,
    _ig_order_type_to_blive,
    _ig_tif_to_blive,
    _parse_ig_timestamp,
)
from blive.adapters.ig.client import IGClient
from blive.adapters.ig.credentials import IGCredentials
from blive.adapters.ig.instrument_resolver import IGInstrumentResolver
from blive.adapters.shared.rate_limiter import (
    RateLimitBucket,
    RateLimitConfig,
    TokenBucketRateLimiter,
)
from blive.domain.events import ConnectionStatus
from blive.domain.types import (
    AssetClass,
    Instrument,
    Order,
    OrderEventKind,
    OrderSide,
    OrderType,
    OrderUpdate,
    TimeInForce,
)

# --- Fixtures ---------------------------------------------------------------


def _login_response() -> httpx.Response:
    return httpx.Response(
        status_code=200,
        headers={"CST": "test-cst", "X-SECURITY-TOKEN": "test-token"},
        json={"accountId": "ACC123"},
    )


def _make_broker(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    account_id: str = "ACC123",
) -> tuple[IGBroker, IGClient, SimClock]:
    clock = SimClock(start=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc))
    creds = IGCredentials(
        api_key="k",
        username="u",
        password="p",
        account_id=account_id,
        environment="demo",
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
    resolver = IGInstrumentResolver(client)
    broker = IGBroker(client=client, resolver=resolver, credentials=creds, clock=clock)
    return broker, client, clock


# --- Connect / disconnect ---------------------------------------------------


async def test_connect_calls_client_and_switches_account() -> None:
    requests_seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        requests_seen.append((request.method, path))
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if request.method == "PUT" and path.endswith("/session"):
            body = request.read()
            assert b"ACC123" in body, "PUT /session must carry the account_id"
            return httpx.Response(status_code=200, json={})
        raise AssertionError(f"unexpected request: {request.method} {path}")

    broker, _client, _clock = _make_broker(handler)
    await broker.connect()

    methods = [m for m, _ in requests_seen]
    assert methods == ["POST", "PUT"], f"expected connect+switch, got {requests_seen}"


async def test_connect_idempotent() -> None:
    call_count = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            call_count[0] += 1
            return _login_response()
        if request.method == "PUT" and path.endswith("/session"):
            return httpx.Response(status_code=200, json={})
        raise AssertionError(f"unexpected request: {request.method} {path}")

    broker, _client, _clock = _make_broker(handler)
    await broker.connect()
    await broker.connect()
    assert call_count[0] == 1


async def test_disconnect_logs_out_and_emits_event() -> None:
    deletes: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if request.method == "PUT" and path.endswith("/session"):
            return httpx.Response(status_code=200, json={})
        if request.method == "DELETE" and path.endswith("/session"):
            deletes.append(request)
            return httpx.Response(status_code=204)
        raise AssertionError(f"unexpected request: {request.method} {path}")

    broker, _client, _clock = _make_broker(handler)
    await broker.connect()

    # Drain the connect event before disconnecting so we can verify the
    # disconnect event lands.
    iterator = broker.events()
    first = await iterator.__anext__()
    assert isinstance(first, ConnectionStatus) and first.connected is True

    await broker.disconnect()
    second = await iterator.__anext__()
    assert isinstance(second, ConnectionStatus) and second.connected is False
    assert len(deletes) == 1


# --- positions() ------------------------------------------------------------


def _positions_response(positions: list[dict[str, Any]]) -> httpx.Response:
    return httpx.Response(status_code=200, json={"positions": positions})


async def test_positions_returns_parsed_records() -> None:
    payload = [
        {
            "position": {
                "size": 0.5,
                "direction": "BUY",
                "level": 7100.0,
                "currency": "EUR",
                "createdDateUTC": "2026-04-28T09:00:00",
                "dealId": "DIABC123",
                "dealReference": "REF1",
            },
            "market": {
                "epic": "IX.D.CAC40.CASH.IP",
                "instrumentName": "France 40",
                "currencies": [{"code": "EUR"}],
            },
        }
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if request.method == "PUT" and path.endswith("/session"):
            return httpx.Response(status_code=200, json={})
        if request.method == "GET" and path.endswith("/positions"):
            return _positions_response(payload)
        raise AssertionError(f"unexpected request: {request.method} {path}")

    broker, _client, _clock = _make_broker(handler)
    await broker.connect()
    positions = await broker.positions()

    assert len(positions) == 1
    pos = positions[0]
    assert pos.instrument.symbol == "CAC40"
    assert pos.instrument.asset_class == AssetClass.INDEX
    assert pos.instrument.tradability == "cfd"
    assert pos.instrument.venue == "IG"
    assert pos.instrument.currency == "EUR"
    assert pos.quantity == Decimal("0.5")
    assert pos.avg_cost == Decimal("7100.0")
    assert pos.currency == "EUR"
    assert pos.strategy_id == "ig_ACC123"
    assert pos.opened_at is not None
    assert pos.opened_at.tzinfo == timezone.utc


async def test_positions_short_direction_signs_quantity_negative() -> None:
    payload = [
        {
            "position": {
                "size": 1.0,
                "direction": "SELL",
                "level": 7000.0,
                "currency": "EUR",
            },
            "market": {"epic": "IX.D.CAC40.CASH.IP"},
        }
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if request.method == "PUT" and path.endswith("/session"):
            return httpx.Response(status_code=200, json={})
        if request.method == "GET" and path.endswith("/positions"):
            return _positions_response(payload)
        raise AssertionError(f"unexpected request: {request.method} {path}")

    broker, _client, _clock = _make_broker(handler)
    await broker.connect()
    positions = await broker.positions()
    assert positions[0].quantity == Decimal("-1.0")


async def test_positions_skips_malformed_entries() -> None:
    payload = [
        {"position": "not-a-dict", "market": {"epic": "IX.D.CAC40.CASH.IP"}},
        {  # missing direction
            "position": {"size": 1.0, "level": 7000.0, "currency": "EUR"},
            "market": {"epic": "IX.D.CAC40.CASH.IP"},
        },
        {  # well-formed
            "position": {
                "size": 0.5,
                "direction": "BUY",
                "level": 7100.0,
                "currency": "EUR",
            },
            "market": {"epic": "IX.D.CAC40.CASH.IP"},
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if request.method == "PUT" and path.endswith("/session"):
            return httpx.Response(status_code=200, json={})
        if request.method == "GET" and path.endswith("/positions"):
            return _positions_response(payload)
        raise AssertionError(f"unexpected request: {request.method} {path}")

    broker, _client, _clock = _make_broker(handler)
    await broker.connect()
    positions = await broker.positions()
    assert len(positions) == 1, "only well-formed entry should survive"


async def test_positions_empty_returns_empty_list() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if request.method == "PUT" and path.endswith("/session"):
            return httpx.Response(status_code=200, json={})
        if request.method == "GET" and path.endswith("/positions"):
            return httpx.Response(status_code=200, json={"positions": []})
        raise AssertionError(f"unexpected request: {request.method} {path}")

    broker, _client, _clock = _make_broker(handler)
    await broker.connect()
    assert await broker.positions() == []


async def test_positions_before_connect_raises() -> None:
    broker, _client, _clock = _make_broker(lambda _: _login_response())
    with pytest.raises(RuntimeError, match="before connect"):
        await broker.positions()


# --- account_snapshot() ----------------------------------------------------


def _accounts_response(accounts: list[dict[str, Any]]) -> httpx.Response:
    return httpx.Response(status_code=200, json={"accounts": accounts})


async def test_account_snapshot_filters_to_active_account() -> None:
    payload = [
        {"accountId": "OTHER", "currency": "GBP", "balance": {"available": 100.0}},
        {
            "accountId": "ACC123",
            "currency": "EUR",
            "balance": {
                "available": 5000.0,
                "balance": 10000.0,
                "profitLoss": 234.5,
                "deposit": 1000.0,
            },
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if request.method == "PUT" and path.endswith("/session"):
            return httpx.Response(status_code=200, json={})
        if request.method == "GET" and path.endswith("/accounts"):
            return _accounts_response(payload)
        raise AssertionError(f"unexpected request: {request.method} {path}")

    broker, _client, _clock = _make_broker(handler)
    await broker.connect()
    snap = await broker.account_snapshot()

    assert snap.base_currency == "EUR"
    assert snap.equity == Decimal("10234.5")  # balance + profitLoss
    assert snap.buying_power == Decimal("5000.0")
    assert snap.margin_used == Decimal("1000.0")
    assert snap.cash_by_ccy == {"EUR": Decimal("5000.0")}


async def test_account_snapshot_account_not_found_raises() -> None:
    payload = [{"accountId": "DIFFERENT", "currency": "GBP", "balance": {"available": 0}}]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if request.method == "PUT" and path.endswith("/session"):
            return httpx.Response(status_code=200, json={})
        if request.method == "GET" and path.endswith("/accounts"):
            return _accounts_response(payload)
        raise AssertionError(f"unexpected request: {request.method} {path}")

    broker, _client, _clock = _make_broker(handler)
    await broker.connect()
    with pytest.raises(ValueError, match="not found"):
        await broker.account_snapshot()


async def test_account_snapshot_empty_response_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if request.method == "PUT" and path.endswith("/session"):
            return httpx.Response(status_code=200, json={})
        if request.method == "GET" and path.endswith("/accounts"):
            return httpx.Response(status_code=200, json={"accounts": []})
        raise AssertionError(f"unexpected request: {request.method} {path}")

    broker, _client, _clock = _make_broker(handler)
    await broker.connect()
    with pytest.raises(ValueError, match="no accounts"):
        await broker.account_snapshot()


# --- open_orders() ----------------------------------------------------------


async def test_open_orders_returns_parsed_records() -> None:
    payload = [
        {
            "workingOrderData": {
                "dealId": "FFAA0011",  # hex-like → deterministic UUID
                "dealReference": "REF1",
                "direction": "BUY",
                "orderSize": 0.5,
                "orderLevel": 7000.0,
                "orderType": "LIMIT",
                "timeInForce": "GOOD_TILL_CANCELLED",
                "createdDateUTC": "2026-04-28T08:30:00",
            },
            "marketData": {
                "epic": "IX.D.CAC40.CASH.IP",
                "instrumentName": "France 40",
                "currencies": [{"code": "EUR"}],
            },
        }
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if request.method == "PUT" and path.endswith("/session"):
            return httpx.Response(status_code=200, json={})
        if request.method == "GET" and path.endswith("/workingorders"):
            return httpx.Response(status_code=200, json={"workingOrders": payload})
        raise AssertionError(f"unexpected request: {request.method} {path}")

    broker, _client, _clock = _make_broker(handler)
    await broker.connect()
    orders = await broker.open_orders()
    assert len(orders) == 1
    o = orders[0]
    assert o.instrument.symbol == "CAC40"
    assert o.side == OrderSide.BUY
    assert o.order_type == OrderType.LMT
    assert o.time_in_force == TimeInForce.GTC
    assert o.quantity == Decimal("0.5")
    assert o.limit_price == Decimal("7000.0")
    assert o.stop_price is None
    assert o.tags["ig_deal_id"] == "FFAA0011"
    assert o.strategy_id == "ig_ACC123"


async def test_open_orders_empty_returns_empty_list() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if request.method == "PUT" and path.endswith("/session"):
            return httpx.Response(status_code=200, json={})
        if request.method == "GET" and path.endswith("/workingorders"):
            return httpx.Response(status_code=200, json={"workingOrders": []})
        raise AssertionError(f"unexpected request: {request.method} {path}")

    broker, _client, _clock = _make_broker(handler)
    await broker.connect()
    assert await broker.open_orders() == []


# --- events() ---------------------------------------------------------------


async def test_events_yields_connection_status_on_connect() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if request.method == "PUT" and path.endswith("/session"):
            return httpx.Response(status_code=200, json={})
        raise AssertionError(f"unexpected request: {request.method} {path}")

    broker, _client, _clock = _make_broker(handler)
    iterator = broker.events()
    await broker.connect()
    first = await asyncio.wait_for(iterator.__anext__(), timeout=1.0)
    assert isinstance(first, ConnectionStatus)
    assert first.connected is True
    assert "demo" in first.detail
    assert "ACC123" in first.detail


# --- Write-method tests (M2-IG.4) ------------------------------------------


def _make_market_order(
    *,
    side: OrderSide = OrderSide.BUY,
    quantity: Decimal = Decimal("0.5"),
) -> Order:
    return Order(
        client_order_id=uuid4(),
        strategy_id="tkan_v4_momentum_timing_1x_ig",
        instrument=Instrument(
            symbol="CAC40",
            venue="XPAR",
            currency="EUR",
            asset_class=AssetClass.INDEX,
            tradability="cfd",
        ),
        side=side,
        quantity=quantity,
        order_type=OrderType.MKT,
        time_in_force=TimeInForce.DAY,
        limit_price=None,
        stop_price=None,
        parent_id=None,
        tags={},
        created_at=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
    )


async def test_submit_market_order_happy_path() -> None:
    """Successful submit: POST /positions/otc → confirm ACCEPTED → SUBMITTED + ACCEPTED + FILLED events."""
    requests_seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        requests_seen.append((request.method, path))
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if request.method == "PUT" and path.endswith("/session"):
            return httpx.Response(status_code=200, json={})
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
                    "dealingRules": {"minDealSize": {"value": 0.1, "unit": "POINTS"}},
                    "snapshot": {},
                },
            )
        if request.method == "POST" and path.endswith("/positions/otc"):
            body = request.read()
            assert b'"BUY"' in body and b'"MARKET"' in body
            return httpx.Response(status_code=200, json={"dealReference": "DEALREF1"})
        if request.method == "GET" and path.endswith("/confirms/DEALREF1"):
            return httpx.Response(
                status_code=200,
                json={
                    "dealReference": "DEALREF1",
                    "dealId": "DIDABC123",
                    "dealStatus": "ACCEPTED",
                    "level": 7050.5,
                    "size": 0.5,
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {path}")

    broker, _client, _clock = _make_broker(handler)
    await broker.connect()

    order = _make_market_order()
    returned_id = await broker.submit(order)
    assert returned_id == order.client_order_id

    # Drain events: ConnectionStatus(connected) + SUBMITTED + ACCEPTED + FILLED.
    iterator = broker.events()
    seen: list[Any] = []
    for _ in range(4):
        seen.append(await asyncio.wait_for(iterator.__anext__(), timeout=1.0))

    assert isinstance(seen[0], ConnectionStatus) and seen[0].connected is True
    assert seen[1].kind == OrderEventKind.SUBMITTED
    assert seen[1].venue_order_id == "DEALREF1"
    assert seen[2].kind == OrderEventKind.ACCEPTED
    assert seen[2].venue_order_id == "DIDABC123"
    assert seen[3].kind == OrderEventKind.FILLED
    assert seen[3].fill is not None
    assert seen[3].fill.price == Decimal("7050.5")
    assert seen[3].fill.quantity == Decimal("0.5")
    assert seen[3].fill.venue_exec_id == "DIDABC123"


async def test_submit_market_order_rejected() -> None:
    """Confirm REJECTED → SUBMITTED + REJECTED events; no FILLED."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if request.method == "PUT" and path.endswith("/session"):
            return httpx.Response(status_code=200, json={})
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
                    "dealingRules": {"minDealSize": {"value": 0.1, "unit": "POINTS"}},
                },
            )
        if request.method == "POST" and path.endswith("/positions/otc"):
            return httpx.Response(status_code=200, json={"dealReference": "DEALREF2"})
        if request.method == "GET" and path.endswith("/confirms/DEALREF2"):
            return httpx.Response(
                status_code=200,
                json={
                    "dealReference": "DEALREF2",
                    "dealId": "DIDXYZ",
                    "dealStatus": "REJECTED",
                    "reason": "INSUFFICIENT_FUNDS",
                    "reasonCode": "INSUFFICIENT_FUNDS",
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {path}")

    broker, _client, _clock = _make_broker(handler)
    await broker.connect()
    order = _make_market_order()
    await broker.submit(order)

    # Drain: connect + SUBMITTED + REJECTED.
    iterator = broker.events()
    seen: list[Any] = []
    for _ in range(3):
        seen.append(await asyncio.wait_for(iterator.__anext__(), timeout=1.0))

    assert seen[1].kind == OrderEventKind.SUBMITTED
    assert seen[2].kind == OrderEventKind.REJECTED
    assert "INSUFFICIENT_FUNDS" in (seen[2].reason or "")


async def test_submit_polls_until_confirm_resolves() -> None:
    """Confirm endpoint returns OPEN until 3rd attempt; submit waits."""
    confirm_calls = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response()
        if request.method == "PUT" and path.endswith("/session"):
            return httpx.Response(status_code=200, json={})
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
                    "dealingRules": {"minDealSize": {"value": 0.1}},
                },
            )
        if request.method == "POST" and path.endswith("/positions/otc"):
            return httpx.Response(status_code=200, json={"dealReference": "DEALREF3"})
        if request.method == "GET" and path.endswith("/confirms/DEALREF3"):
            confirm_calls[0] += 1
            if confirm_calls[0] < 3:
                return httpx.Response(status_code=200, json={"dealStatus": "OPEN"})
            return httpx.Response(
                status_code=200,
                json={
                    "dealReference": "DEALREF3",
                    "dealId": "DID3",
                    "dealStatus": "ACCEPTED",
                    "level": 7000,
                    "size": 1.0,
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {path}")

    broker, _client, _clock = _make_broker(handler)
    await broker.connect()
    await broker.submit(_make_market_order(quantity=Decimal("1.0")))
    assert confirm_calls[0] == 3, "should have polled 3 times before resolving"


async def test_submit_non_market_order_raises_not_implemented() -> None:
    broker, _client, _clock = _make_broker(lambda _: _login_response())
    await broker.connect()  # not actually called by handler; using simple lambda
    limit_order = Order(
        client_order_id=uuid4(),
        strategy_id="s",
        instrument=Instrument(
            symbol="CAC40",
            venue="XPAR",
            currency="EUR",
            asset_class=AssetClass.INDEX,
            tradability="cfd",
        ),
        side=OrderSide.BUY,
        quantity=Decimal("1"),
        order_type=OrderType.LMT,
        time_in_force=TimeInForce.DAY,
        limit_price=Decimal("7000"),
        stop_price=None,
        parent_id=None,
        tags={},
        created_at=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc),
    )
    with pytest.raises(NotImplementedError, match="OrderType.MKT only"):
        await broker.submit(limit_order)


async def test_submit_before_connect_raises() -> None:
    broker, _client, _clock = _make_broker(lambda _: _login_response())
    with pytest.raises(RuntimeError, match="before connect"):
        await broker.submit(_make_market_order())


async def test_cancel_raises_not_implemented() -> None:
    broker, _client, _clock = _make_broker(lambda _: _login_response())
    with pytest.raises(NotImplementedError, match="working orders"):
        await broker.cancel(uuid4())  # type: ignore[arg-type]


async def test_replace_raises_not_implemented() -> None:
    broker, _client, _clock = _make_broker(lambda _: _login_response())
    with pytest.raises(NotImplementedError, match="working orders"):
        await broker.replace(uuid4(), OrderUpdate(quantity=Decimal("1")))  # type: ignore[arg-type]


# --- Helper-function tests --------------------------------------------------


def test_epic_to_symbol_extracts_third_segment() -> None:
    assert _epic_to_symbol("IX.D.CAC40.CASH.IP") == "CAC40"
    assert _epic_to_symbol("KC.D.AAPL.CASH.IP") == "AAPL"
    assert _epic_to_symbol("CS.D.EURUSD.CFD.IP") == "EURUSD"


def test_epic_to_symbol_returns_input_on_short_format() -> None:
    """Defensive: unrecognised format gets the input back, not raised."""
    assert _epic_to_symbol("WEIRD") == "WEIRD"


def test_epic_to_asset_class_table() -> None:
    assert _epic_to_asset_class("IX.D.CAC40.CASH.IP") == AssetClass.INDEX
    assert _epic_to_asset_class("KC.D.AAPL.CASH.IP") == AssetClass.EQUITY
    assert _epic_to_asset_class("CS.D.EURUSD.CFD.IP") == AssetClass.FX
    assert _epic_to_asset_class("CC.D.LCO.UNC.IP") == AssetClass.FUTURE
    assert _epic_to_asset_class("KA.D.SPX.OPT.IP") == AssetClass.OPTION


def test_ig_order_type_mapping() -> None:
    blive_type, has_lim, has_stop = _ig_order_type_to_blive("LIMIT")
    assert blive_type == OrderType.LMT and has_lim is True and has_stop is False

    blive_type, has_lim, has_stop = _ig_order_type_to_blive("STOP")
    assert blive_type == OrderType.STP and has_lim is False and has_stop is True

    blive_type, has_lim, has_stop = _ig_order_type_to_blive("MARKET")
    assert blive_type == OrderType.MKT and has_lim is False and has_stop is False


def test_ig_tif_mapping() -> None:
    assert _ig_tif_to_blive("GOOD_TILL_CANCELLED") == TimeInForce.GTC
    assert _ig_tif_to_blive("EXECUTE_AND_ELIMINATE") == TimeInForce.IOC
    assert _ig_tif_to_blive("FILL_OR_KILL") == TimeInForce.FOK
    assert _ig_tif_to_blive("GOOD_TILL_DATE") == TimeInForce.GTC


def test_parse_ig_timestamp_iso_z() -> None:
    dt = _parse_ig_timestamp("2026-04-28T09:00:00Z")
    assert dt == datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc)


def test_parse_ig_timestamp_iso_naive_assumed_utc() -> None:
    dt = _parse_ig_timestamp("2026-04-28T09:00:00")
    assert dt == datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc)


def test_parse_ig_timestamp_slash_format() -> None:
    dt = _parse_ig_timestamp("2026/04/28 09:00:00")
    assert dt == datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc)


def test_parse_ig_timestamp_unrecognised_raises() -> None:
    with pytest.raises(ValueError, match="unrecognised"):
        _parse_ig_timestamp("not-a-date")


def test_hex_like_recognises_hex_strings() -> None:
    assert _hex_like("FFAA00") is True
    assert _hex_like("123abc") is True
    assert _hex_like("") is False
    assert _hex_like("not-hex") is False
