"""Tests for :mod:`blive.adapters.ig.client`.

Covers the IG REST client core per [ADR-036](../../../../../docs/decisions/DECISIONS.md#adr-036--ig-wire-level-driver-roll-our-own-httpx--asyncio-lightstreamer):
3-step auth, token refresh + retry, full-reauth fallback, error mapping
([KB-17 §6](../../../../../docs/kb/ig_pacing_spec.md#6-error-codes-at-the-pacing-boundary)),
rate-limiter integration, environment-based URL routing.

Uses :class:`httpx.MockTransport` to simulate IG responses without the
network. Each test configures its own response handler.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable

import httpx
import pytest

from blive.adapters.clock.sim import SimClock
from blive.adapters.ig.client import (
    IGAuthError,
    IGClient,
    IGOrderRejected,
    IGRateLimited,
    IGRequestInvalid,
    IGSessionExpired,
)
from blive.adapters.ig.credentials import IGCredentials
from blive.adapters.shared.rate_limiter import (
    RateLimitBucket,
    RateLimitConfig,
    TokenBucketRateLimiter,
)

# --- Fixtures ---------------------------------------------------------------


@pytest.fixture
def clock() -> SimClock:
    return SimClock(start=datetime(2026, 4, 28, 9, 0, 0, tzinfo=timezone.utc))


@pytest.fixture
def rate_limiter(clock: SimClock) -> TokenBucketRateLimiter:
    """IG-default-shaped buckets but with generous capacities so tests don't block."""
    return TokenBucketRateLimiter(
        clock=clock,
        config=RateLimitConfig(
            buckets={
                "general": RateLimitBucket(capacity=100, refill_per_second=Decimal("10")),
                "trading": RateLimitBucket(capacity=100, refill_per_second=Decimal("10")),
                "historical_prices": RateLimitBucket(capacity=100, refill_per_second=Decimal("10")),
            }
        ),
    )


@pytest.fixture
def demo_credentials() -> IGCredentials:
    return IGCredentials(
        api_key="test-api-key",
        username="test-user",
        password="test-pwd",
        account_id="ACC123",
        environment="demo",
    )


@pytest.fixture
def live_credentials() -> IGCredentials:
    return IGCredentials(
        api_key="test-api-key",
        username="test-user",
        password="test-pwd",
        account_id="ACC123",
        environment="live",
    )


def _make_client(
    handler: Callable[[httpx.Request], httpx.Response],
    credentials: IGCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> IGClient:
    transport = httpx.MockTransport(handler)
    return IGClient(
        credentials=credentials,
        rate_limiter=rate_limiter,
        clock=clock,
        transport=transport,
    )


def _login_response(cst: str = "test-cst", token: str = "test-token") -> httpx.Response:
    """Build a successful POST /session response with valid auth headers."""
    return httpx.Response(
        status_code=200,
        headers={"CST": cst, "X-SECURITY-TOKEN": token},
        json={"accountId": "ACC123", "accountType": "CFD"},
    )


# --- URL routing -------------------------------------------------------------


def test_demo_credentials_use_demo_base_url(
    demo_credentials: IGCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    client = _make_client(lambda _: _login_response(), demo_credentials, rate_limiter, clock)
    assert client.base_url == "https://demo-api.ig.com/gateway/deal"


def test_live_credentials_use_live_base_url(
    live_credentials: IGCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    client = _make_client(lambda _: _login_response(), live_credentials, rate_limiter, clock)
    assert client.base_url == "https://api.ig.com/gateway/deal"


# --- Connect / disconnect ----------------------------------------------------


async def test_connect_performs_3_step_auth_and_stores_tokens(
    demo_credentials: IGCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return _login_response(cst="cst-from-server", token="token-from-server")

    client = _make_client(handler, demo_credentials, rate_limiter, clock)
    assert client.is_connected is False
    await client.connect()

    assert client.is_connected is True
    assert len(captured) == 1
    req = captured[0]
    assert req.method == "POST"
    assert req.url.path == "/gateway/deal/session"
    assert req.headers["X-IG-API-KEY"] == "test-api-key"
    assert req.headers["Version"] == "2"
    body = req.read()
    assert b"test-user" in body
    assert b"test-pwd" in body


async def test_connect_idempotent_when_already_connected(
    demo_credentials: IGCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    call_count = [0]

    def handler(_: httpx.Request) -> httpx.Response:
        call_count[0] += 1
        return _login_response()

    client = _make_client(handler, demo_credentials, rate_limiter, clock)
    await client.connect()
    await client.connect()
    assert call_count[0] == 1, "second connect() should be a no-op"


async def test_connect_invalid_credentials_raises_ig_auth_error(
    demo_credentials: IGCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=401,
            json={"errorCode": "error.security.invalid-details"},
        )

    client = _make_client(handler, demo_credentials, rate_limiter, clock)
    with pytest.raises(IGAuthError):
        await client.connect()
    assert client.is_connected is False


async def test_connect_missing_headers_raises_auth_error(
    demo_credentials: IGCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """200 OK but no CST / X-SECURITY-TOKEN — IG returned malformed auth."""

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json={"accountId": "ACC"})  # no headers

    client = _make_client(handler, demo_credentials, rate_limiter, clock)
    with pytest.raises(IGAuthError, match="missing CST"):
        await client.connect()


async def test_disconnect_calls_delete_session_and_clears_state(
    demo_credentials: IGCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    deletes: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "DELETE" and request.url.path.endswith("/session"):
            deletes.append(request)
            return httpx.Response(status_code=204)
        return _login_response()

    client = _make_client(handler, demo_credentials, rate_limiter, clock)
    await client.connect()
    await client.disconnect()
    assert client.is_connected is False
    assert len(deletes) == 1
    assert "CST" in deletes[0].headers


# --- Request methods --------------------------------------------------------


async def test_get_sends_auth_and_version_headers(
    demo_credentials: IGCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/session"):
            return _login_response()
        captured.append(request)
        return httpx.Response(status_code=200, json={"hello": "world"})

    client = _make_client(handler, demo_credentials, rate_limiter, clock)
    await client.connect()
    body = await client.get("/accounts", version=1)
    assert body == {"hello": "world"}
    assert len(captured) == 1
    req = captured[0]
    assert req.headers["CST"] == "test-cst"
    assert req.headers["X-SECURITY-TOKEN"] == "test-token"
    assert req.headers["Version"] == "1"


async def test_get_before_connect_raises(
    demo_credentials: IGCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    client = _make_client(lambda _: _login_response(), demo_credentials, rate_limiter, clock)
    with pytest.raises(IGAuthError, match="before connect"):
        await client.get("/accounts")


async def test_post_uses_trading_bucket_by_default(
    demo_credentials: IGCredentials,
    clock: SimClock,
) -> None:
    """Drain the trading bucket before connect; verify POST blocks until refill."""
    rate_limiter = TokenBucketRateLimiter(
        clock=clock,
        config=RateLimitConfig(
            buckets={
                "general": RateLimitBucket(capacity=10, refill_per_second=Decimal("10")),
                "trading": RateLimitBucket(capacity=1, refill_per_second=Decimal("1")),
            }
        ),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/session"):
            return _login_response()
        return httpx.Response(status_code=200, json={})

    client = _make_client(handler, demo_credentials, rate_limiter, clock)
    await client.connect()

    # Drain the trading bucket.
    await rate_limiter.acquire("trading")
    before = clock.now()
    await client.post("/positions/otc")
    elapsed = (clock.now() - before).total_seconds()
    assert elapsed >= 1.0, f"POST should wait for trading bucket refill (~1s), got {elapsed}"


# --- Error mapping ----------------------------------------------------------


async def test_rate_limit_response_raises_ig_rate_limited(
    demo_credentials: IGCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/session"):
            return _login_response()
        return httpx.Response(
            status_code=403,
            json={"errorCode": "error.public-api.exceeded-account-allowance"},
        )

    client = _make_client(handler, demo_credentials, rate_limiter, clock)
    await client.connect()
    with pytest.raises(IGRateLimited) as excinfo:
        await client.get("/positions")
    assert excinfo.value.error_code == "error.public-api.exceeded-account-allowance"
    assert excinfo.value.http_status == 403


async def test_invalid_instrument_raises_request_invalid(
    demo_credentials: IGCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/session"):
            return _login_response()
        return httpx.Response(
            status_code=404,
            json={"errorCode": "error.invalid.instrument"},
        )

    client = _make_client(handler, demo_credentials, rate_limiter, clock)
    await client.connect()
    with pytest.raises(IGRequestInvalid):
        await client.get("/markets/BAD.EPIC")


async def test_deal_rejected_raises_order_rejected(
    demo_credentials: IGCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/session"):
            return _login_response()
        return httpx.Response(
            status_code=400,
            json={"errorCode": "error.confirms.deal-rejected"},
        )

    client = _make_client(handler, demo_credentials, rate_limiter, clock)
    await client.connect()
    with pytest.raises(IGOrderRejected):
        await client.post("/positions/otc")


# --- Token refresh ----------------------------------------------------------


async def test_session_expired_triggers_refresh_and_retry(
    demo_credentials: IGCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """First GET fails with session-expired → client refreshes → second GET succeeds."""
    request_log: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            request_log.append("connect")
            return _login_response(cst="cst-1", token="token-1")
        if request.method == "POST" and path.endswith("/session/refresh-token"):
            request_log.append("refresh")
            return httpx.Response(
                status_code=200,
                headers={"CST": "cst-2", "X-SECURITY-TOKEN": "token-2"},
                json={},
            )
        if request.method == "GET" and path.endswith("/accounts"):
            request_log.append(f"get-{request.headers.get('CST')}")
            if request.headers.get("CST") == "cst-1":
                # First call with stale token — return session-expired.
                return httpx.Response(
                    status_code=401,
                    json={"errorCode": "error.security.client-token-invalid"},
                )
            # Second call with refreshed token — succeed.
            return httpx.Response(status_code=200, json={"accountId": "ACC123"})
        raise AssertionError(f"unexpected request: {request.method} {path}")

    client = _make_client(handler, demo_credentials, rate_limiter, clock)
    await client.connect()
    body = await client.get("/accounts")

    assert body == {"accountId": "ACC123"}
    assert request_log == ["connect", "get-cst-1", "refresh", "get-cst-2"]


async def test_failed_refresh_falls_back_to_full_reauth(
    demo_credentials: IGCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """Refresh-token endpoint also returns session-expired → client re-auths fully."""
    request_log: list[str] = []
    connect_seq = ["cst-A", "cst-B"]  # two connects: original + post-failed-refresh

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            cst = connect_seq.pop(0)
            request_log.append(f"connect-{cst}")
            return _login_response(cst=cst, token=f"token-{cst[-1]}")
        if request.method == "POST" and path.endswith("/session/refresh-token"):
            request_log.append("refresh-fails")
            return httpx.Response(
                status_code=401,
                json={"errorCode": "error.security.client-token-invalid"},
            )
        if request.method == "GET" and path.endswith("/accounts"):
            cst_header = request.headers.get("CST")
            request_log.append(f"get-{cst_header}")
            if cst_header == "cst-A":
                return httpx.Response(
                    status_code=401,
                    json={"errorCode": "error.security.client-token-invalid"},
                )
            return httpx.Response(status_code=200, json={"ok": True})
        raise AssertionError(f"unexpected request: {request.method} {path}")

    client = _make_client(handler, demo_credentials, rate_limiter, clock)
    await client.connect()
    body = await client.get("/accounts")

    assert body == {"ok": True}
    assert request_log == [
        "connect-cst-A",
        "get-cst-A",
        "refresh-fails",
        "connect-cst-B",
        "get-cst-B",
    ]


async def test_persistent_auth_failure_raises_ig_auth_error(
    demo_credentials: IGCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """Refresh fails AND full re-auth's first request also gets session-expired."""
    request_log: list[str] = []
    connect_count = [0]

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            connect_count[0] += 1
            request_log.append(f"connect-{connect_count[0]}")
            return _login_response(cst=f"cst-{connect_count[0]}", token=f"tok-{connect_count[0]}")
        if request.method == "POST" and path.endswith("/session/refresh-token"):
            request_log.append("refresh-fails")
            return httpx.Response(
                status_code=401,
                json={"errorCode": "error.security.client-token-invalid"},
            )
        if request.method == "GET" and path.endswith("/accounts"):
            # Always return session-expired regardless of CST.
            request_log.append("get-fails")
            return httpx.Response(
                status_code=401,
                json={"errorCode": "error.security.client-token-invalid"},
            )
        raise AssertionError(f"unexpected request: {request.method} {path}")

    client = _make_client(handler, demo_credentials, rate_limiter, clock)
    await client.connect()
    with pytest.raises(IGAuthError, match="re-established"):
        await client.get("/accounts")


# --- IGSessionExpired is internal (not raised to caller) --------------------


async def test_ig_session_expired_not_raised_to_caller_when_recoverable(
    demo_credentials: IGCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """A session-expired response on a regular request is caught internally
    and recovered via refresh; the caller sees only the eventual success."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/session"):
            return _login_response(cst="cst-1", token="token-1")
        if request.method == "POST" and path.endswith("/session/refresh-token"):
            return httpx.Response(
                status_code=200,
                headers={"CST": "cst-2", "X-SECURITY-TOKEN": "token-2"},
                json={},
            )
        if request.headers.get("CST") == "cst-1":
            return httpx.Response(
                status_code=401,
                json={"errorCode": "error.security.client-token-invalid"},
            )
        return httpx.Response(status_code=200, json={"recovered": True})

    client = _make_client(handler, demo_credentials, rate_limiter, clock)
    await client.connect()
    # Session expired raises only if the client EXPOSES it to caller; it shouldn't.
    body = await client.get("/positions")
    assert body == {"recovered": True}


# --- Direct exception-classification spot checks ---------------------------


def test_classify_error_table() -> None:
    """Sanity-check the KB-17 §6 table mapping inside _classify_error."""
    from blive.adapters.ig.client import _classify_error

    assert _classify_error("error.security.invalid-details", 401) is IGAuthError
    assert _classify_error("error.security.api-key-revoked", 403) is IGAuthError
    assert _classify_error("error.security.client-token-invalid", 401) is IGSessionExpired
    assert _classify_error("error.public-api.exceeded-trading-allowance", 403) is IGRateLimited
    assert _classify_error("error.confirms.deal-rejected", 400) is IGOrderRejected
    assert _classify_error("error.invalid.instrument", 404) is IGRequestInvalid
    assert _classify_error(None, 500) is IGRequestInvalid.__bases__[0] or True  # see below
    # 5xx without errorCode → IGConnectionError per the implementation.
    from blive.adapters.ig.client import IGConnectionError

    assert _classify_error(None, 500) is IGConnectionError
    assert _classify_error(None, 502) is IGConnectionError
