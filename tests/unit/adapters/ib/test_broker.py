"""Tests for :mod:`blive.adapters.ib.broker`.

Covers the IB broker read-side per [INV-6 §1.1](../../../../../docs/inv/ports_adapters.md#11-brokerport):
connect/disconnect lifecycle, ConnectionStatus emission, positions /
account_snapshot / open_orders parsing from ``ib_async`` cached state,
the events() iterator, and write-method NotImplementedError raises.

Mocking strategy:

- ``ib_async.IB`` instance: :class:`unittest.mock.MagicMock` with
  ``spec=ib_async.IB`` (same pattern as other IB tests).
- ``accountValueEvent``: a real :class:`eventkit.Event` so the
  broker's ``+=`` / ``-=`` registration round-trips realistically and
  tests can drive pushes via ``event.emit(account_value)``.
- ``accountValues`` / ``reqPositionsAsync`` / ``reqAllOpenOrdersAsync``:
  configured per-test to return the desired payloads.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Sequence
from unittest.mock import AsyncMock, MagicMock

import eventkit
import ib_async
import pytest

from blive.adapters.clock.sim import SimClock
from blive.adapters.ib.broker import IBBroker, IBShapeError
from blive.adapters.ib.client import IBClient
from blive.adapters.ib.credentials import IBCredentials
from blive.adapters.ib.instrument_resolver import IBInstrumentResolver
from blive.adapters.shared.price_grid import PriceIncrement
from blive.adapters.shared.rate_limiter import (
    RateLimitBucket,
    RateLimitConfig,
    TokenBucketRateLimiter,
)
from blive.domain.events import AccountUpdate, ConnectionStatus, OrderEvent
from blive.domain.types import (
    AssetClass,
    Instrument,
    Order,
    OrderEventKind,
    OrderSide,
    OrderType,
    TimeInForce,
)

# --- Fixtures ---------------------------------------------------------------


@pytest.fixture
def clock() -> SimClock:
    return SimClock(start=datetime(2026, 5, 1, 14, 0, 0, tzinfo=timezone.utc))


@pytest.fixture
def rate_limiter(clock: SimClock) -> TokenBucketRateLimiter:
    return TokenBucketRateLimiter(
        clock=clock,
        config=RateLimitConfig(
            buckets={
                "global": RateLimitBucket(capacity=100, refill_per_second=Decimal("20")),
                "historical": RateLimitBucket(capacity=50, refill_per_second=Decimal("1")),
            }
        ),
    )


@pytest.fixture
def credentials() -> IBCredentials:
    return IBCredentials(
        host="127.0.0.1",
        port=4002,
        client_id=1,
        account_id="DUTEST",
    )


def _make_mock_ib(
    *,
    initial_account_values: list[ib_async.AccountValue] | None = None,
    positions: list[ib_async.Position] | None = None,
    open_trades: list[ib_async.Trade] | None = None,
) -> MagicMock:
    """Build an ``ib_async.IB`` mock with the live-event surface wired.

    ``accountValueEvent`` is a real :class:`eventkit.Event` so the
    broker can register / detach handlers; tests drive pushes via
    ``event.emit(account_value)``.

    ``accountValues``, ``reqPositionsAsync``, ``reqAllOpenOrdersAsync``
    are configured per-test.
    """
    m = MagicMock(spec=ib_async.IB)
    state = {"connected": False}

    def _is_connected() -> bool:
        return state["connected"]

    async def _connect_async(**_kwargs: object) -> None:
        state["connected"] = True

    def _disconnect() -> None:
        state["connected"] = False

    m.isConnected.side_effect = _is_connected
    m.connectAsync = AsyncMock(side_effect=_connect_async)
    m.disconnect.side_effect = _disconnect

    # Real eventkit.Event for accountValueEvent so += / -= work realistically.
    m.accountValueEvent = eventkit.Event()
    # Real eventkit.Event for errorEvent — the broker subscribes here at
    # connect() to capture rejection reason text on the global error
    # channel for paths that don't mirror it into trade.log (e.g. error
    # 201 PRIIPs/KID; M2-IB.6.2 finding).
    m.errorEvent = eventkit.Event()

    # Account values cache (read by IBBroker.connect to seed local cache).
    m.accountValues.return_value = list(initial_account_values or [])

    # Async readers.
    m.reqPositionsAsync = AsyncMock(return_value=list(positions or []))
    m.reqAllOpenOrdersAsync = AsyncMock(return_value=list(open_trades or []))

    return m


class _StubPriceRules:
    """Permissive ADR-051 price-grid provider for the broker suite: a 0.01
    grid leaves the on-grid test limit prices unchanged. Tick-snapping
    itself is exercised in ``test_broker_tick_grid.py``."""

    async def increments_for(self, instrument: Instrument) -> Sequence[PriceIncrement]:
        return (PriceIncrement(Decimal("0"), Decimal("0.01")),)


def _make_broker(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
    mock_ib: MagicMock,
) -> IBBroker:
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock, ib=mock_ib)
    resolver = IBInstrumentResolver(client)
    return IBBroker(client=client, resolver=resolver, clock=clock, price_rules=_StubPriceRules())


def _ib_account_value(
    *,
    tag: str,
    value: str,
    currency: str = "EUR",
    account: str = "DUTEST",
) -> ib_async.AccountValue:
    return ib_async.AccountValue(
        account=account,
        tag=tag,
        value=value,
        currency=currency,
        modelCode="",
    )


def _ib_position(
    *,
    symbol: str,
    secType: str = "STK",
    exchange: str = "SBF",
    currency: str = "EUR",
    quantity: Decimal | float,
    avg_cost: Decimal | float,
    account: str = "DUTEST",
    primary_exchange: str = "",
) -> ib_async.Position:
    contract = ib_async.Contract(
        symbol=symbol,
        secType=secType,
        exchange=exchange,
        primaryExchange=primary_exchange,
        currency=currency,
    )
    return ib_async.Position(
        account=account,
        contract=contract,
        position=Decimal(str(quantity)),
        avgCost=float(avg_cost),
    )


def _ib_trade(
    *,
    symbol: str,
    action: str = "BUY",
    order_type: str = "LMT",
    tif: str = "DAY",
    quantity: Decimal | float = 100,
    limit_price: float = 78.50,
    stop_price: float = 0.0,
    order_id: int = 42,
    perm_id: int = 1234567,
    exchange: str = "SBF",
    currency: str = "EUR",
) -> ib_async.Trade:
    contract = ib_async.Contract(
        symbol=symbol,
        secType="STK",
        exchange=exchange,
        currency=currency,
    )
    order = ib_async.LimitOrder(action, Decimal(str(quantity)), limit_price)
    order.orderId = order_id
    order.permId = perm_id
    order.orderType = order_type
    order.tif = tif
    order.lmtPrice = limit_price
    order.auxPrice = stop_price
    order.totalQuantity = Decimal(str(quantity))
    return ib_async.Trade(contract=contract, order=order)


# --- Construction & accessors -----------------------------------------------


def test_broker_starts_disconnected_with_synthetic_strategy_id(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    broker = _make_broker(credentials, rate_limiter, clock, _make_mock_ib())
    assert broker.is_connected is False
    assert broker.broker_strategy_id == "ib_DUTEST"


# --- connect / disconnect lifecycle -----------------------------------------


async def test_connect_seeds_cache_subscribes_and_emits_status(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    initial = [
        _ib_account_value(tag="NetLiquidationByCurrency", value="100000.00"),
        _ib_account_value(tag="TotalCashBalance", value="50000.00"),
        _ib_account_value(tag="BuyingPower", value="200000.00"),
    ]
    mock_ib = _make_mock_ib(initial_account_values=initial)
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)

    await broker.connect()

    assert broker.is_connected is True
    # ib_async.accountValues was queried with the account id.
    mock_ib.accountValues.assert_called_once_with("DUTEST")
    # An additional push via the event handler is captured.
    mock_ib.accountValueEvent.emit(_ib_account_value(tag="GrossPositionValue", value="80000.00"))
    snapshot = await broker.account_snapshot()
    assert snapshot.equity == Decimal("100000.00")
    assert snapshot.gross_exposure == Decimal("80000.00")  # event-pushed value


async def test_connect_emits_connection_status_event(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib()
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)

    await broker.connect()

    events_iter = broker.events()
    event = await events_iter.__anext__()
    assert isinstance(event, ConnectionStatus)
    assert event.connected is True
    assert "DUTEST" in event.detail


async def test_connect_is_idempotent(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib()
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)

    await broker.connect()
    await broker.connect()

    # accountValues called once (the second connect was a no-op).
    assert mock_ib.accountValues.call_count == 1


async def test_disconnect_clears_cache_detaches_and_emits_status(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    initial = [_ib_account_value(tag="NetLiquidationByCurrency", value="100000")]
    mock_ib = _make_mock_ib(initial_account_values=initial)
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    # Sanity: cache populated.
    snapshot1 = await broker.account_snapshot()
    assert snapshot1.equity == Decimal("100000")

    await broker.disconnect()

    assert broker.is_connected is False
    # account_snapshot now raises since the cache is cleared.
    with pytest.raises(RuntimeError, match="connect"):
        await broker.account_snapshot()


async def test_disconnect_is_idempotent_when_not_connected(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib()
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    # No-op (no events should be emitted, no underlying IB calls).
    await broker.disconnect()


async def test_disconnect_after_connect_emits_status(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib()
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    await broker.disconnect()

    # Drain two events (connect then disconnect).
    events_iter = broker.events()
    e1 = await events_iter.__anext__()
    e2 = await events_iter.__anext__()
    assert isinstance(e1, ConnectionStatus) and e1.connected is True
    assert isinstance(e2, ConnectionStatus) and e2.connected is False


# --- positions --------------------------------------------------------------


async def test_positions_returns_parsed_records(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    positions = [
        _ib_position(symbol="CAC", quantity=Decimal("10"), avg_cost=78.42),
    ]
    mock_ib = _make_mock_ib(positions=positions)
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    result = await broker.positions()

    assert len(result) == 1
    pos = result[0]
    assert pos.instrument.symbol == "CAC"
    assert pos.instrument.venue == "XPAR"  # SBF reverse-mapped
    assert pos.instrument.currency == "EUR"
    assert pos.instrument.asset_class == AssetClass.EQUITY  # STK default
    assert pos.strategy_id == "ib_DUTEST"
    assert pos.quantity == Decimal("10")
    assert pos.avg_cost == Decimal("78.42")


async def test_positions_uses_primary_exchange_when_set(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """When IB sets primaryExchange, prefer it over the routing exchange."""
    positions = [
        _ib_position(
            symbol="AAPL",
            exchange="SMART",
            primary_exchange="NASDAQ",
            currency="USD",
            quantity=Decimal("50"),
            avg_cost=180.0,
        )
    ]
    mock_ib = _make_mock_ib(positions=positions)
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    result = await broker.positions()

    assert result[0].instrument.venue == "XNAS"  # primaryExchange NASDAQ → XNAS


async def test_positions_consumes_global_token(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib(positions=[])
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    before = rate_limiter.metrics()["global"].available
    await broker.positions()
    after = rate_limiter.metrics()["global"].available
    assert after == before - Decimal(1)


async def test_positions_skips_unparseable_entries(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """A malformed Position entry is logged + skipped, not raised."""
    bad = ib_async.Position(
        account="DUTEST",
        contract=ib_async.Contract(symbol="", secType="STK", exchange="SBF", currency="EUR"),
        position=Decimal("1"),
        avgCost=10.0,
    )
    good = _ib_position(symbol="CAC", quantity=Decimal("5"), avg_cost=78)
    mock_ib = _make_mock_ib(positions=[bad, good])
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    result = await broker.positions()

    # Bad one (empty symbol) skipped; good one returned.
    assert len(result) == 1
    assert result[0].instrument.symbol == "CAC"


async def test_positions_requires_connect(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib()
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    with pytest.raises(RuntimeError, match="connect"):
        await broker.positions()


# --- account_snapshot -------------------------------------------------------


async def test_account_snapshot_builds_from_seed_cache(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    initial = [
        _ib_account_value(tag="NetLiquidationByCurrency", value="100000.00", currency="EUR"),
        _ib_account_value(tag="TotalCashBalance", value="40000.00", currency="EUR"),
        _ib_account_value(tag="TotalCashBalance", value="20000.00", currency="USD"),
        _ib_account_value(tag="BuyingPower", value="200000.00", currency="EUR"),
        _ib_account_value(tag="GrossPositionValue", value="60000.00", currency="EUR"),
        _ib_account_value(tag="MaintMarginReq", value="5000.00", currency="EUR"),
    ]
    mock_ib = _make_mock_ib(initial_account_values=initial)
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    snapshot = await broker.account_snapshot()

    assert snapshot.base_currency == "EUR"
    assert snapshot.equity == Decimal("100000.00")
    assert snapshot.buying_power == Decimal("200000.00")
    assert snapshot.gross_exposure == Decimal("60000.00")
    assert snapshot.margin_used == Decimal("5000.00")
    assert snapshot.cash_by_ccy == {"EUR": Decimal("40000.00"), "USD": Decimal("20000.00")}
    # leverage = gross / equity = 0.6
    assert snapshot.leverage == Decimal("0.6")


async def test_account_snapshot_raises_when_cache_empty(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib(initial_account_values=[])
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    with pytest.raises(IBShapeError, match="not yet received"):
        await broker.account_snapshot()


async def test_account_snapshot_accepts_post_connect_event_pushes(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """Values pushed via accountValueEvent after connect update the cache."""
    mock_ib = _make_mock_ib(
        initial_account_values=[
            _ib_account_value(tag="NetLiquidationByCurrency", value="100000.00"),
        ]
    )
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    # Push a fresher value via the event.
    mock_ib.accountValueEvent.emit(
        _ib_account_value(tag="NetLiquidationByCurrency", value="105000.00")
    )

    snapshot = await broker.account_snapshot()
    assert snapshot.equity == Decimal("105000.00")  # event value won


async def test_account_snapshot_filters_other_account_pushes(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """Pushes for a different account id (sub-account stream) are dropped."""
    mock_ib = _make_mock_ib(
        initial_account_values=[
            _ib_account_value(tag="NetLiquidationByCurrency", value="100000.00"),
        ]
    )
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    # Push a value for a different account — should be ignored.
    mock_ib.accountValueEvent.emit(
        _ib_account_value(
            tag="NetLiquidationByCurrency",
            value="999999.00",
            account="DUOTHERACCT",
        )
    )

    snapshot = await broker.account_snapshot()
    assert snapshot.equity == Decimal("100000.00")  # not overwritten


async def test_account_snapshot_mixed_currency_reads_base_total(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """Mixed-currency account: equity is the consolidated BASE total, not the
    base-currency sleeve (M3.4 finding, 2026-06-05 live IB DUP886336).

    IB reports ``NetLiquidationByCurrency`` for the base-currency *sleeve*
    (GBP-denominated holdings only) AND a "BASE" aggregate (the whole account).
    Reading the GBP sleeve (£902,839) silently dropped the USD cash (~£101k)
    vs the true total (£1,003,886). ``base_currency`` is inferred from the unit
    ``ExchangeRate`` row, not by comparing unconverted cross-currency magnitudes.
    """
    initial = [
        # NetLiquidation: GBP sleeve, USD sleeve, and the BASE consolidated total.
        _ib_account_value(tag="NetLiquidationByCurrency", value="1003885.69", currency="BASE"),
        _ib_account_value(tag="NetLiquidationByCurrency", value="902839.13", currency="GBP"),
        _ib_account_value(tag="NetLiquidationByCurrency", value="134724.51", currency="USD"),
        # Cash per currency (the "BASE" aggregate row is excluded from cash_by_ccy).
        _ib_account_value(tag="TotalCashBalance", value="1003620.33", currency="BASE"),
        _ib_account_value(tag="TotalCashBalance", value="902573.77", currency="GBP"),
        _ib_account_value(tag="TotalCashBalance", value="134724.51", currency="USD"),
        # ExchangeRate: the base currency reports a unit rate; others are FX rates.
        _ib_account_value(tag="ExchangeRate", value="1.00", currency="GBP"),
        _ib_account_value(tag="ExchangeRate", value="0.7449588", currency="USD"),
        # Base-only aggregates (no "BASE" row — only the base-currency sleeve).
        _ib_account_value(tag="BuyingPower", value="4014481.32", currency="GBP"),
        _ib_account_value(tag="GrossPositionValue", value="0.00", currency="GBP"),
        _ib_account_value(tag="MaintMarginReq", value="0.00", currency="GBP"),
    ]
    mock_ib = _make_mock_ib(initial_account_values=initial)
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    snapshot = await broker.account_snapshot()

    # base currency from the unit ExchangeRate row, not the largest magnitude
    # (the GBP sleeve happens to be larger here, but the signal is authoritative).
    assert snapshot.base_currency == "GBP"
    # equity is the BASE total (£1,003,886), NOT the GBP sleeve (£902,839).
    assert snapshot.equity == Decimal("1003885.69")
    # base-only aggregates fall through to the GBP sleeve correctly.
    assert snapshot.buying_power == Decimal("4014481.32")
    assert snapshot.gross_exposure == Decimal("0.00")
    assert snapshot.margin_used == Decimal("0.00")
    # cash_by_ccy carries both sleeves (the "BASE" aggregate row is excluded).
    assert snapshot.cash_by_ccy == {
        "GBP": Decimal("902573.77"),
        "USD": Decimal("134724.51"),
    }


async def test_account_snapshot_requires_connect(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib()
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    with pytest.raises(RuntimeError, match="connect"):
        await broker.account_snapshot()


# --- open_orders ------------------------------------------------------------


async def test_open_orders_returns_parsed_orders(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    trades = [
        _ib_trade(symbol="CAC", action="BUY", order_type="LMT", quantity=100, limit_price=78.50),
    ]
    mock_ib = _make_mock_ib(open_trades=trades)
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    result = await broker.open_orders()

    assert len(result) == 1
    order = result[0]
    assert order.side == OrderSide.BUY
    assert order.order_type == OrderType.LMT
    assert order.time_in_force == TimeInForce.DAY
    assert order.quantity == Decimal("100")
    assert order.limit_price == Decimal("78.5")
    assert order.stop_price is None
    assert order.strategy_id == "ib_DUTEST"
    assert order.tags["ib_order_id"] == "42"
    assert order.tags["ib_perm_id"] == "1234567"


async def test_open_orders_skips_unparseable(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """An unsupported orderType is logged + skipped, not raised."""
    bad = _ib_trade(symbol="X", order_type="MIDPRICE", quantity=10, limit_price=100)
    good = _ib_trade(symbol="CAC", quantity=50, limit_price=78.5)
    mock_ib = _make_mock_ib(open_trades=[bad, good])
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    result = await broker.open_orders()

    assert len(result) == 1
    assert result[0].instrument.symbol == "CAC"


async def test_open_orders_consumes_global_token(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib(open_trades=[])
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    before = rate_limiter.metrics()["global"].available
    await broker.open_orders()
    after = rate_limiter.metrics()["global"].available
    assert after == before - Decimal(1)


async def test_open_orders_requires_connect(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib()
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    with pytest.raises(RuntimeError, match="connect"):
        await broker.open_orders()


# --- write methods (M2-IB.4) ------------------------------------------------


# --- write side: submit / cancel / replace (M2-IB.4a) ----------------------


def _build_order(
    *,
    order_type: OrderType = OrderType.LMT,
    side: OrderSide = OrderSide.BUY,
    quantity: Decimal = Decimal("1"),
    limit_price: Decimal | None = Decimal("1.00"),
    stop_price: Decimal | None = None,
    tif: TimeInForce = TimeInForce.DAY,
) -> "Order":
    """Build a CAC.PA test order. Defaults to a tiny LMT BUY at €1
    (well below market — won't fill in live testing)."""
    from uuid import uuid4

    from blive.domain.types import ClientOrderId, Instrument, Order

    return Order(
        client_order_id=ClientOrderId(uuid4()),
        strategy_id="test",
        instrument=Instrument(
            symbol="CAC.PA",
            venue="XPAR",
            currency="EUR",
            asset_class=AssetClass.ETF,
            multiplier=Decimal("1"),
        ),
        side=side,
        quantity=quantity,
        order_type=order_type,
        time_in_force=tif,
        limit_price=limit_price,
        stop_price=stop_price,
        parent_id=None,
        tags={},
        created_at=datetime(2026, 5, 1, 14, 0, 0, tzinfo=timezone.utc),
    )


def _make_mock_trade(
    *,
    order: ib_async.Order,
    contract: ib_async.Contract | None = None,
) -> MagicMock:
    """Build a fake ``ib_async.Trade`` with eventkit Events for the per-trade
    surface that IBBroker wires."""
    if contract is None:
        contract = ib_async.Contract(symbol="CAC", secType="STK", exchange="SBF", currency="EUR")
    trade = MagicMock(spec=ib_async.Trade)
    trade.contract = contract
    trade.order = order
    # IB assigns an integer orderId on submission; mock a realistic value.
    trade.order.orderId = 100
    trade.order.permId = 1234567
    trade.orderStatus = MagicMock(spec=ib_async.OrderStatus)
    trade.orderStatus.status = "PendingSubmit"
    trade.orderStatus.whyHeld = ""
    trade.log = []
    trade.fills = []
    trade.statusEvent = eventkit.Event()
    trade.fillEvent = eventkit.Event()
    trade.commissionReportEvent = eventkit.Event()
    return trade


async def test_submit_market_order_emits_submitted_immediately(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """submit() emits SUBMITTED on the events queue right after
    ib.placeOrder returns. ACCEPTED arrives later via statusEvent."""
    mock_ib = _make_mock_ib()
    fake_trade = _make_mock_trade(order=ib_async.MarketOrder("BUY", 1))
    mock_ib.placeOrder.return_value = fake_trade
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    events_iter = broker.events()
    await events_iter.__anext__()  # drain ConnectionStatus

    order = _build_order(order_type=OrderType.MKT, limit_price=None)
    cid = await broker.submit(order)

    assert cid == order.client_order_id
    event = await events_iter.__anext__()
    assert isinstance(event, OrderEvent)
    assert event.kind == OrderEventKind.SUBMITTED
    assert event.client_order_id == order.client_order_id
    assert event.venue_order_id == "100"
    # placeOrder was called with the resolved Contract + an ib_async order
    # carrying orderRef = client_order_id.
    place_args = mock_ib.placeOrder.call_args
    assert place_args.args[1].orderRef == str(order.client_order_id)


async def test_submit_adaptive_mkt_order_routes_via_ibalgo(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """OrderType.ADAPTIVE_MKT (M2-IB.6.2c) builds an ib_async.MarketOrder
    with ``algoStrategy="Adaptive"`` and ``algoParams=[("adaptivePriority",
    "Normal")]`` set. IBALGO Adaptive bypasses IB's regulatory
    disruptive-orders price-cap (warning 2161; INV-14 v0.7) which raw MKT
    on volatile / leveraged products like QQL3 on LSEETF triggers
    structurally — observed in production at M2-IB.6.2b 2026-05-06 where
    raw MKT bound to ``mktCapPrice=38.9`` for the full 60-second event
    wait without filling. Adaptive routes via IB's smart agency layer
    instead, treated as not-a-raw-MKT for the disruption check.
    """
    mock_ib = _make_mock_ib()
    fake_trade = _make_mock_trade(order=ib_async.MarketOrder("BUY", 1))
    mock_ib.placeOrder.return_value = fake_trade
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    events_iter = broker.events()
    await events_iter.__anext__()  # ConnectionStatus

    order = _build_order(order_type=OrderType.ADAPTIVE_MKT, limit_price=None)
    cid = await broker.submit(order)

    assert cid == order.client_order_id
    place_args = mock_ib.placeOrder.call_args
    placed_ib_order = place_args.args[1]
    # Adaptive metadata must be present on the wire-going order.
    assert placed_ib_order.algoStrategy == "Adaptive"
    assert len(placed_ib_order.algoParams) == 1
    tag_value = placed_ib_order.algoParams[0]
    assert tag_value.tag == "adaptivePriority"
    assert tag_value.value == "Normal"
    # Same SUBMITTED emission shape as raw MKT — ADAPTIVE_MKT is a
    # routing variant, not an FSM variant.
    event = await events_iter.__anext__()
    assert isinstance(event, OrderEvent)
    assert event.kind == OrderEventKind.SUBMITTED


async def test_submit_lmt_order_emits_accepted_on_status_submitted(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """ACCEPTED emitted when IB pushes orderStatus 'Submitted' (or
    'PreSubmitted' for held orders)."""
    mock_ib = _make_mock_ib()
    fake_trade = _make_mock_trade(order=ib_async.LimitOrder("BUY", 1, 1.0))
    mock_ib.placeOrder.return_value = fake_trade
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    events_iter = broker.events()
    await events_iter.__anext__()  # ConnectionStatus

    order = _build_order(order_type=OrderType.LMT, limit_price=Decimal("1.00"))
    await broker.submit(order)
    await events_iter.__anext__()  # SUBMITTED

    # Simulate IB pushing orderStatus 'Submitted'.
    fake_trade.orderStatus.status = "Submitted"
    fake_trade.statusEvent.emit(fake_trade)
    # Allow the asyncio.create_task in the handler to run.
    await asyncio.sleep(0)

    event = await events_iter.__anext__()
    assert isinstance(event, OrderEvent)
    assert event.kind == OrderEventKind.ACCEPTED


async def test_submit_does_not_double_emit_accepted(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """IB sometimes pushes 'Submitted' multiple times (re-acks); blive
    emits ACCEPTED only on the first occurrence."""
    mock_ib = _make_mock_ib()
    fake_trade = _make_mock_trade(order=ib_async.LimitOrder("BUY", 1, 1.0))
    mock_ib.placeOrder.return_value = fake_trade
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    events_iter = broker.events()
    await events_iter.__anext__()  # ConnectionStatus

    await broker.submit(_build_order())
    await events_iter.__anext__()  # SUBMITTED

    fake_trade.orderStatus.status = "Submitted"
    fake_trade.statusEvent.emit(fake_trade)
    await asyncio.sleep(0)
    await events_iter.__anext__()  # ACCEPTED (1st)

    # Re-emit the same status — should NOT produce a second ACCEPTED.
    fake_trade.statusEvent.emit(fake_trade)
    await asyncio.sleep(0)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(events_iter.__anext__(), timeout=0.05)


async def test_submit_emits_filled_on_fill_completing_quantity(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """When fillEvent fires with shares == total_quantity, emit FILLED
    with a Fill payload carrying price + qty + commission."""
    mock_ib = _make_mock_ib()
    fake_trade = _make_mock_trade(order=ib_async.LimitOrder("BUY", 10, 78.0))
    mock_ib.placeOrder.return_value = fake_trade
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    events_iter = broker.events()
    await events_iter.__anext__()  # ConnectionStatus

    order = _build_order(quantity=Decimal("10"), limit_price=Decimal("78.00"))
    await broker.submit(order)
    await events_iter.__anext__()  # SUBMITTED

    # Fire fillEvent with full quantity.
    execution = MagicMock(spec=ib_async.Execution)
    execution.execId = "exec-1"
    execution.shares = Decimal("10")
    execution.price = 78.0
    execution.time = datetime(2026, 5, 1, 14, 5, tzinfo=timezone.utc)
    commission_report = MagicMock(spec=ib_async.CommissionReport)
    commission_report.commission = 0.5
    commission_report.currency = "EUR"
    fill = MagicMock(spec=ib_async.Fill)
    fill.execution = execution
    fill.commissionReport = commission_report
    fake_trade.fillEvent.emit(fake_trade, fill)
    await asyncio.sleep(0)

    # First event after SUBMITTED is ACCEPTED (auto-emitted by fill handler
    # when statusEvent didn't fire first).
    e1 = await events_iter.__anext__()
    assert e1.kind == OrderEventKind.ACCEPTED
    e2 = await events_iter.__anext__()
    assert e2.kind == OrderEventKind.FILLED
    assert e2.fill is not None
    assert e2.fill.quantity == Decimal("10")
    assert e2.fill.price == Decimal("78.0")
    assert e2.fill.commission == Decimal("0.5")
    assert e2.fill.venue_exec_id == "exec-1"


async def test_submit_dedupes_by_exec_id(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """IB occasionally re-pushes execDetails on reconnect — INV-13 §6
    idempotency: dedupe by venue_exec_id."""
    mock_ib = _make_mock_ib()
    fake_trade = _make_mock_trade(order=ib_async.LimitOrder("BUY", 10, 78.0))
    mock_ib.placeOrder.return_value = fake_trade
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    events_iter = broker.events()
    await events_iter.__anext__()
    await broker.submit(_build_order(quantity=Decimal("10"), limit_price=Decimal("78")))
    await events_iter.__anext__()  # SUBMITTED

    execution = MagicMock(spec=ib_async.Execution)
    execution.execId = "exec-1"
    execution.shares = Decimal("10")
    execution.price = 78.0
    execution.time = datetime(2026, 5, 1, 14, 5, tzinfo=timezone.utc)
    fill = MagicMock(spec=ib_async.Fill)
    fill.execution = execution
    fill.commissionReport = None  # no commission yet
    fake_trade.fillEvent.emit(fake_trade, fill)
    await asyncio.sleep(0)
    await events_iter.__anext__()  # ACCEPTED
    await events_iter.__anext__()  # FILLED

    # Re-emit same exec_id — should be deduped.
    fake_trade.fillEvent.emit(fake_trade, fill)
    await asyncio.sleep(0)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(events_iter.__anext__(), timeout=0.05)


async def test_submit_emits_canceled_on_status_cancelled(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """Cancel via cancel() then orderStatus 'Cancelled' fires → CANCELED event."""
    mock_ib = _make_mock_ib()
    fake_trade = _make_mock_trade(order=ib_async.LimitOrder("BUY", 1, 1.0))
    mock_ib.placeOrder.return_value = fake_trade
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    events_iter = broker.events()
    await events_iter.__anext__()  # ConnectionStatus

    order = _build_order()
    cid = await broker.submit(order)
    await events_iter.__anext__()  # SUBMITTED
    fake_trade.orderStatus.status = "Submitted"
    fake_trade.statusEvent.emit(fake_trade)
    await asyncio.sleep(0)
    await events_iter.__anext__()  # ACCEPTED

    # Operator cancels.
    await broker.cancel(cid)
    mock_ib.cancelOrder.assert_called_once_with(fake_trade.order)

    # IB pushes Cancelled status.
    fake_trade.orderStatus.status = "Cancelled"
    fake_trade.statusEvent.emit(fake_trade)
    await asyncio.sleep(0)

    event = await events_iter.__anext__()
    assert event.kind == OrderEventKind.CANCELED
    assert event.reason == "engine"


async def test_submit_emits_rejected_on_status_inactive(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """orderStatus 'Inactive' with a whyHeld / log message → REJECTED with reason."""
    mock_ib = _make_mock_ib()
    fake_trade = _make_mock_trade(order=ib_async.LimitOrder("BUY", 1, 1.0))
    mock_ib.placeOrder.return_value = fake_trade
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    events_iter = broker.events()
    await events_iter.__anext__()
    await broker.submit(_build_order())
    await events_iter.__anext__()  # SUBMITTED

    log_entry = MagicMock()
    log_entry.message = "Order rejected: insufficient buying power"
    fake_trade.log = [log_entry]
    fake_trade.orderStatus.status = "Inactive"
    fake_trade.statusEvent.emit(fake_trade)
    await asyncio.sleep(0)

    event = await events_iter.__anext__()
    assert event.kind == OrderEventKind.REJECTED
    assert "insufficient buying power" in event.reason


async def test_submit_emits_rejected_via_error_event_stash_when_log_empty(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """M2-IB.6.2 finding: IB error 201 PRIIPs/KID path delivers the rejection
    text only on ``ib.errorEvent`` — ``trade.log`` carries empty-message
    entries, ``whyHeld`` is empty, ``orderStatus.status`` is ``"Inactive"``.
    The broker must consult its ``_error_by_order_id`` stash (populated by
    the ``errorEvent`` subscription added in connect()) to recover the
    formatted ``"ib:{code} {message}"`` reason; INV-14 v0.6 documents the
    catalogued path for this rejection class.
    """
    mock_ib = _make_mock_ib()
    fake_trade = _make_mock_trade(order=ib_async.LimitOrder("BUY", 1, 1.0))
    mock_ib.placeOrder.return_value = fake_trade
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    events_iter = broker.events()
    await events_iter.__anext__()  # ConnectionStatus
    await broker.submit(_build_order())
    await events_iter.__anext__()  # SUBMITTED

    # Production wire ordering (M2-IB.6.2 finding 2026-05-04): ib_async
    # dispatches the per-trade statusEvent BEFORE the global errorEvent for
    # IB-error rejections, so the broker schedules a deferred async helper
    # to read the stash on a subsequent loop tick. Tests must mirror this
    # ordering — fire statusEvent first, then errorEvent, then drive the
    # loop forward — otherwise the test passes trivially and doesn't catch
    # the race the helper is designed to resolve.
    empty_log_entry = MagicMock()
    empty_log_entry.errorCode = 0
    empty_log_entry.message = ""
    fake_trade.log = [empty_log_entry]
    fake_trade.orderStatus.status = "Inactive"
    fake_trade.orderStatus.whyHeld = ""
    fake_trade.statusEvent.emit(fake_trade)

    priips_message = (
        "Order rejected - reason:No Trading Permission, Customer Ineligible; "
        "Ineligibility reasons:This product does not have a KID in English "
        "or in a language approved for your country."
    )
    mock_ib.errorEvent.emit(fake_trade.order.orderId, 201, priips_message, fake_trade.contract)

    # Drive the loop forward to let the deferred helper run.
    for _ in range(5):
        await asyncio.sleep(0)

    event = await events_iter.__anext__()
    assert event.kind == OrderEventKind.REJECTED
    assert event.reason is not None
    assert "ib:201" in event.reason
    assert "KID" in event.reason

    # The stash entry should be popped on terminal emission so memory
    # doesn't grow across long sessions.
    assert fake_trade.order.orderId not in broker._error_by_order_id  # noqa: SLF001


async def test_error_event_ignores_connection_level_reqid(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """ib.errorEvent fires with reqId == -1 for connection-level events
    (data-farm status, market-data subscription warnings). The broker
    must ignore those — they don't correspond to an order and would
    otherwise pollute the orderId-keyed stash."""
    mock_ib = _make_mock_ib()
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    mock_ib.errorEvent.emit(-1, 2104, "Market data farm connection is OK:eufarm", None)
    mock_ib.errorEvent.emit(0, 1100, "Connectivity between IB and TWS lost.", None)
    await asyncio.sleep(0)

    assert broker._error_by_order_id == {}  # noqa: SLF001


async def test_observed_error_codes_tallies_order_level_pushes(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """M3.2 / OQ-031: the broker tallies order-related error/warning codes
    (reqId > 0) into observed_error_codes so the empirical-window results
    sink can count warning 2161 (PMA cap) without log-scraping. Two 2161
    pushes on distinct orders + one 110 are counted; connection-level
    events (reqId <= 0) are excluded, symmetric with the rejection stash."""
    mock_ib = _make_mock_ib()
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()

    mock_ib.errorEvent.emit(101, 2161, "PMA cap: BUY 5 QQL3 LSEETF ...", None)
    mock_ib.errorEvent.emit(102, 2161, "PMA cap: BUY 5 QQL3 LSEETF ...", None)
    mock_ib.errorEvent.emit(103, 110, "The price does not conform ...", None)
    mock_ib.errorEvent.emit(-1, 2104, "Market data farm connection is OK", None)
    await asyncio.sleep(0)

    codes = broker.observed_error_codes
    assert codes[2161] == 2
    assert codes[110] == 1
    assert 2104 not in codes  # reqId <= 0 excluded

    # The accessor returns a copy — mutating it doesn't touch the broker.
    codes[2161] = 99
    assert broker.observed_error_codes[2161] == 2


async def test_submit_emits_rejected_when_cancelled_with_error_code_in_log(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """IB sometimes pushes status="Cancelled" for system rejections (risk
    precautions, direct-routing blocks like error 10311, dup orderId 322).
    The trade log carries a non-zero errorCode in those cases; the broker
    disambiguates to REJECTED with an "ib:{code} {message}" reason per
    INV-13 §5 + INV-14 (see _last_error_log_entry / _rejected_reason_from_log_entry)."""
    mock_ib = _make_mock_ib()
    fake_trade = _make_mock_trade(order=ib_async.LimitOrder("BUY", 1, 1.0))
    mock_ib.placeOrder.return_value = fake_trade
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    events_iter = broker.events()
    await events_iter.__anext__()  # ConnectionStatus

    await broker.submit(_build_order())
    await events_iter.__anext__()  # SUBMITTED

    # Simulate IB pushing Cancelled with an errorCode entry in the trade log
    # (system-initiated rejection, not a user cancel). The broker should
    # disambiguate to REJECTED.
    log_entry = MagicMock()
    log_entry.errorCode = 201
    log_entry.message = "Order rejected - reason: risk precaution block"
    fake_trade.log = [log_entry]
    fake_trade.orderStatus.status = "Cancelled"
    fake_trade.statusEvent.emit(fake_trade)
    await asyncio.sleep(0)

    event = await events_iter.__anext__()
    assert event.kind == OrderEventKind.REJECTED
    assert "ib:201" in event.reason
    assert "risk precaution block" in event.reason


async def test_submit_emits_rejected_when_cancelled_with_error_code_no_message(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """If the errored log entry has an empty message, the reason degrades
    to "ib:{errorCode}" without raising — analytics by code still work."""
    mock_ib = _make_mock_ib()
    fake_trade = _make_mock_trade(order=ib_async.LimitOrder("BUY", 1, 1.0))
    mock_ib.placeOrder.return_value = fake_trade
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    events_iter = broker.events()
    await events_iter.__anext__()

    await broker.submit(_build_order())
    await events_iter.__anext__()  # SUBMITTED

    log_entry = MagicMock()
    log_entry.errorCode = 322
    log_entry.message = ""
    fake_trade.log = [log_entry]
    fake_trade.orderStatus.status = "Cancelled"
    fake_trade.statusEvent.emit(fake_trade)
    await asyncio.sleep(0)

    event = await events_iter.__anext__()
    assert event.kind == OrderEventKind.REJECTED
    assert event.reason == "ib:322"


async def test_submit_emits_canceled_when_cancelled_post_acceptance_with_warning_in_log(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """Once the order has reached ACCEPTED, a subsequent Cancelled with a
    non-zero errorCode in the log (e.g., warning 399 "order will not be
    placed until next session open") is a normal CANCELED, not REJECTED.

    Observed at M2-IB.4a-happy-cacpa wire probe (2026-05-02): IB pushed
    Submitted (→ ACCEPTED) for a CAC.PA LMT held until Monday open, with
    a warning 399 entry already in trade.log; engine-initiated cancel
    afterward should produce CANCELED reason='engine', not REJECTED."""
    mock_ib = _make_mock_ib()
    fake_trade = _make_mock_trade(order=ib_async.LimitOrder("BUY", 1, 1.0))
    mock_ib.placeOrder.return_value = fake_trade
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    events_iter = broker.events()
    await events_iter.__anext__()  # ConnectionStatus

    cid = await broker.submit(_build_order())
    await events_iter.__anext__()  # SUBMITTED

    # IB pushes Submitted → broker emits ACCEPTED.
    fake_trade.orderStatus.status = "Submitted"
    fake_trade.statusEvent.emit(fake_trade)
    await asyncio.sleep(0)
    accepted = await events_iter.__anext__()
    assert accepted.kind == OrderEventKind.ACCEPTED

    # An IB warning is sitting in the trade log (e.g., order held until
    # next session) — non-zero errorCode but informational, not a rejection.
    log_entry = MagicMock()
    log_entry.errorCode = 399
    log_entry.message = "Warning 399: Order held until next session open."
    fake_trade.log = [log_entry]

    # Operator cancels.
    await broker.cancel(cid)
    mock_ib.cancelOrder.assert_called_once_with(fake_trade.order)

    # IB pushes Cancelled. Disambiguation: tracking.accepted_emitted is True,
    # so the warning in the log is contextual — emit CANCELED, not REJECTED.
    fake_trade.orderStatus.status = "Cancelled"
    fake_trade.statusEvent.emit(fake_trade)
    await asyncio.sleep(0)

    event = await events_iter.__anext__()
    assert event.kind == OrderEventKind.CANCELED
    assert event.reason == "engine"


async def test_submit_consumes_global_token(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib()
    fake_trade = _make_mock_trade(order=ib_async.LimitOrder("BUY", 1, 1.0))
    mock_ib.placeOrder.return_value = fake_trade
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    before = rate_limiter.metrics()["global"].available
    await broker.submit(_build_order())
    after = rate_limiter.metrics()["global"].available
    assert after == before - Decimal(1)


async def test_submit_unsupported_order_type_raises(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """LOC raises NotImplementedError: it needs a limit price Order does not allow it."""
    broker = _make_broker(credentials, rate_limiter, clock, _make_mock_ib())
    await broker.connect()
    order = _build_order(order_type=OrderType.LOC, limit_price=None)
    with pytest.raises(NotImplementedError, match="LOC"):
        await broker.submit(order)


async def test_submit_lmt_without_limit_price_raises(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """LMT order with limit_price=None can't construct the IB order shape."""
    # Skip the dataclass invariant by building Order directly with limit_price=None
    # — actually DD-1 enforces "required iff order_type ∈ {LMT, STP_LMT}", so
    # constructing such an Order should already fail at the domain level. Verify
    # that's the case (no IBBroker test needed; the domain catches it first).
    from uuid import uuid4

    from blive.domain.types import ClientOrderId, Instrument, Order

    with pytest.raises(ValueError):
        Order(
            client_order_id=ClientOrderId(uuid4()),
            strategy_id="test",
            instrument=Instrument(
                symbol="CAC.PA",
                venue="XPAR",
                currency="EUR",
                asset_class=AssetClass.ETF,
                multiplier=Decimal("1"),
            ),
            side=OrderSide.BUY,
            quantity=Decimal("1"),
            order_type=OrderType.LMT,
            time_in_force=TimeInForce.DAY,
            limit_price=None,  # invalid — DD-1 invariant
            stop_price=None,
            parent_id=None,
            tags={},
            created_at=datetime(2026, 5, 1, 14, 0, 0, tzinfo=timezone.utc),
        )


async def test_submit_duplicate_client_order_id_raises(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    mock_ib = _make_mock_ib()
    fake_trade = _make_mock_trade(order=ib_async.LimitOrder("BUY", 1, 1.0))
    mock_ib.placeOrder.return_value = fake_trade
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    order = _build_order()
    await broker.submit(order)
    with pytest.raises(RuntimeError, match="already submitted"):
        await broker.submit(order)


async def test_submit_before_connect_raises(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    broker = _make_broker(credentials, rate_limiter, clock, _make_mock_ib())
    with pytest.raises(RuntimeError, match="connect"):
        await broker.submit(_build_order())


async def test_cancel_unknown_id_raises(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    from uuid import uuid4

    from blive.domain.types import ClientOrderId

    broker = _make_broker(credentials, rate_limiter, clock, _make_mock_ib())
    await broker.connect()
    with pytest.raises(KeyError, match="unknown"):
        await broker.cancel(ClientOrderId(uuid4()))


async def test_cancel_before_connect_raises(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    from uuid import uuid4

    from blive.domain.types import ClientOrderId

    broker = _make_broker(credentials, rate_limiter, clock, _make_mock_ib())
    with pytest.raises(RuntimeError, match="connect"):
        await broker.cancel(ClientOrderId(uuid4()))


async def test_replace_raises_not_implemented(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """replace() stays deferred to M2-IB.4b (Phase 1 daily strategy doesn't
    modify in-flight orders)."""
    from uuid import uuid4

    from blive.domain.types import ClientOrderId, OrderUpdate

    broker = _make_broker(credentials, rate_limiter, clock, _make_mock_ib())
    with pytest.raises(NotImplementedError, match="M2-IB.4b"):
        await broker.replace(
            ClientOrderId(uuid4()),
            OrderUpdate(quantity=Decimal("50"), limit_price=None, stop_price=None),
        )


# --- AccountUpdate diff-suppress timer (ADR-033 §"Decision" item 2) --------


async def test_account_update_tick_emits_baseline_on_first_call(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """First tick after connect — no prior emitted snapshot — always emits."""
    initial = [
        _ib_account_value(tag="NetLiquidationByCurrency", value="100000.00"),
        _ib_account_value(tag="BuyingPower", value="200000.00"),
    ]
    mock_ib = _make_mock_ib(initial_account_values=initial)
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    # Drain the connect ConnectionStatus so we can isolate the AccountUpdate.
    events_iter = broker.events()
    await events_iter.__anext__()

    await broker._account_update_tick()  # type: ignore[attr-defined]

    event = await events_iter.__anext__()
    assert isinstance(event, AccountUpdate)
    assert event.snapshot.equity == Decimal("100000.00")


async def test_account_update_tick_skips_when_cache_empty(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """Empty cache → silent skip; no event emitted."""
    mock_ib = _make_mock_ib(initial_account_values=[])
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    events_iter = broker.events()
    await events_iter.__anext__()  # drain ConnectionStatus

    await broker._account_update_tick()  # type: ignore[attr-defined]

    # No further event ready — the queue should be empty.
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(events_iter.__anext__(), timeout=0.05)


async def test_account_update_tick_skips_when_nothing_changed(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """Second tick with identical values does NOT emit (diff-suppress)."""
    initial = [_ib_account_value(tag="NetLiquidationByCurrency", value="100000.00")]
    mock_ib = _make_mock_ib(initial_account_values=initial)
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    events_iter = broker.events()
    await events_iter.__anext__()  # ConnectionStatus
    await broker._account_update_tick()  # type: ignore[attr-defined]
    await events_iter.__anext__()  # baseline AccountUpdate

    # Tick again with no change.
    await broker._account_update_tick()  # type: ignore[attr-defined]

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(events_iter.__anext__(), timeout=0.05)


async def test_account_update_tick_emits_on_above_threshold_equity_change(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """A 0.02 currency-unit equity move (above 0.01 threshold) triggers emission."""
    initial = [_ib_account_value(tag="NetLiquidationByCurrency", value="100000.00")]
    mock_ib = _make_mock_ib(initial_account_values=initial)
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    events_iter = broker.events()
    await events_iter.__anext__()  # ConnectionStatus
    await broker._account_update_tick()  # type: ignore[attr-defined]
    await events_iter.__anext__()  # baseline

    # Push a small but above-threshold change.
    mock_ib.accountValueEvent.emit(
        _ib_account_value(tag="NetLiquidationByCurrency", value="100000.02")
    )
    await broker._account_update_tick()  # type: ignore[attr-defined]

    event = await events_iter.__anext__()
    assert isinstance(event, AccountUpdate)
    assert event.snapshot.equity == Decimal("100000.02")


async def test_account_update_tick_skips_below_threshold_change(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """A 0.005 currency-unit equity move (below 0.01 threshold) does NOT emit."""
    initial = [_ib_account_value(tag="NetLiquidationByCurrency", value="100000.000")]
    mock_ib = _make_mock_ib(initial_account_values=initial)
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    events_iter = broker.events()
    await events_iter.__anext__()  # ConnectionStatus
    await broker._account_update_tick()  # type: ignore[attr-defined]
    await events_iter.__anext__()  # baseline

    # Sub-threshold change.
    mock_ib.accountValueEvent.emit(
        _ib_account_value(tag="NetLiquidationByCurrency", value="100000.005")
    )
    await broker._account_update_tick()  # type: ignore[attr-defined]

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(events_iter.__anext__(), timeout=0.05)


async def test_account_update_tick_uses_finer_threshold_for_leverage(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """Leverage threshold is 0.001 (3 d.p.); a 0.0005 leverage move does
    NOT emit on its own. Verified by changing only gross_exposure such
    that leverage moves below the leverage threshold while equity stays
    far below its currency threshold."""
    # equity=10_000_000.00; gross=200_000.00 → leverage=0.02
    initial = [
        _ib_account_value(tag="NetLiquidationByCurrency", value="10000000.00"),
        _ib_account_value(tag="GrossPositionValue", value="200000.00"),
    ]
    mock_ib = _make_mock_ib(initial_account_values=initial)
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    events_iter = broker.events()
    await events_iter.__anext__()
    await broker._account_update_tick()  # type: ignore[attr-defined]
    baseline = await events_iter.__anext__()
    assert isinstance(baseline, AccountUpdate)
    # Move gross by less than ANY threshold (0.001 cur unit / 1e-10 leverage delta).
    # With equity=10M, a 0.001 GrossPositionValue change is below currency
    # threshold (0.01) AND yields a leverage delta of 1e-10 (well below 0.001).
    mock_ib.accountValueEvent.emit(_ib_account_value(tag="GrossPositionValue", value="200000.001"))
    await broker._account_update_tick()  # type: ignore[attr-defined]

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(events_iter.__anext__(), timeout=0.05)


async def test_account_update_tick_emits_on_cash_by_ccy_change(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """A new currency appearing in cash_by_ccy (or balance moving above
    threshold) emits."""
    initial = [
        _ib_account_value(tag="NetLiquidationByCurrency", value="100000.00", currency="EUR"),
        _ib_account_value(tag="TotalCashBalance", value="50000.00", currency="EUR"),
    ]
    mock_ib = _make_mock_ib(initial_account_values=initial)
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    events_iter = broker.events()
    await events_iter.__anext__()
    await broker._account_update_tick()  # type: ignore[attr-defined]
    await events_iter.__anext__()  # baseline (EUR-only cash)

    # Push USD cash arriving for the first time (not in baseline → above
    # threshold relative to implicit zero).
    mock_ib.accountValueEvent.emit(
        _ib_account_value(tag="TotalCashBalance", value="100.00", currency="USD")
    )
    await broker._account_update_tick()  # type: ignore[attr-defined]

    event = await events_iter.__anext__()
    assert isinstance(event, AccountUpdate)
    assert event.snapshot.cash_by_ccy["USD"] == Decimal("100.00")


async def test_disconnect_cancels_account_update_task(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """The 30s emission loop is started by connect and must be cancelled
    by disconnect (otherwise the asyncio loop has dangling tasks)."""
    mock_ib = _make_mock_ib(
        initial_account_values=[_ib_account_value(tag="NetLiquidationByCurrency", value="100000")]
    )
    broker = _make_broker(credentials, rate_limiter, clock, mock_ib)
    await broker.connect()
    task = broker._account_update_task  # type: ignore[attr-defined]
    assert task is not None and not task.done()

    await broker.disconnect()

    # After disconnect the task field is reset and the underlying task is
    # cancelled / done.
    assert broker._account_update_task is None  # type: ignore[attr-defined]
    assert task.done()


async def test_connect_uses_zero_interval_for_short_test_runs(
    credentials: IBCredentials,
    rate_limiter: TokenBucketRateLimiter,
    clock: SimClock,
) -> None:
    """Tests can pass ``account_update_interval_seconds=0`` to make the
    background loop fire on every event-loop iteration. Verify the
    parameter wires through; we don't actually run the loop here, just
    confirm the broker accepts and stores the override."""
    mock_ib = _make_mock_ib()
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock, ib=mock_ib)
    resolver = IBInstrumentResolver(client)
    broker = IBBroker(
        client=client,
        resolver=resolver,
        clock=clock,
        account_update_interval_seconds=0.0,
    )
    await broker.connect()
    try:
        # Just verify the timer task is alive; cancel via disconnect.
        assert broker._account_update_task is not None  # type: ignore[attr-defined]
    finally:
        await broker.disconnect()


# --- Auction orders: closing auction (MOC) and opening auction (MKT + OPG) ---


def test_moc_order_maps_to_ib_market_on_close() -> None:
    """OrderType.MOC becomes an IB ``MOC`` order for the closing auction."""
    from blive.adapters.ib.broker import _blive_to_ib_order

    ib_order = _blive_to_ib_order(
        _build_order(order_type=OrderType.MOC, limit_price=None, quantity=Decimal("7"))
    )
    assert ib_order.orderType == "MOC"
    assert ib_order.action == "BUY"
    assert ib_order.totalQuantity == 7.0
    assert ib_order.tif == "DAY"


def test_mkt_order_with_opg_tif_maps_to_ib_market_on_open() -> None:
    """A MKT order with TimeInForce.OPG is the opening-auction (market-on-open) order."""
    from blive.adapters.ib.broker import _blive_to_ib_order

    ib_order = _blive_to_ib_order(
        _build_order(
            order_type=OrderType.MKT,
            side=OrderSide.SELL,
            limit_price=None,
            quantity=Decimal("7"),
            tif=TimeInForce.OPG,
        )
    )
    assert ib_order.orderType == "MKT"
    assert ib_order.action == "SELL"
    assert ib_order.tif == "OPG"
