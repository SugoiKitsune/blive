"""ADR-051: IBBroker snaps priced orders to the contract tick grid at submit.

Self-contained (own mock-IB + fake provider) so the snapping behaviour is
tested in isolation from the broker's read-side suite. Injects a fake
:class:`PriceIncrementProvider` so no ``reqContractDetails`` wiring is
needed; the IB source/cache is exercised separately in
``test_price_rules.py``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Sequence
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import eventkit
import ib_async

from blive.adapters.clock.sim import SimClock
from blive.adapters.ib.broker import IBBroker
from blive.adapters.ib.client import IBClient
from blive.adapters.ib.credentials import IBCredentials
from blive.adapters.ib.instrument_resolver import IBInstrumentResolver
from blive.adapters.ib.price_rules import PriceRuleUnavailable
from blive.adapters.shared.price_grid import PriceIncrement, RoundingPolicy
from blive.adapters.shared.rate_limiter import (
    RateLimitBucket,
    RateLimitConfig,
    TokenBucketRateLimiter,
)
from blive.domain.events import OrderEvent
from blive.domain.types import (
    AssetClass,
    ClientOrderId,
    Instrument,
    Order,
    OrderEventKind,
    OrderSide,
    OrderType,
    TimeInForce,
)


class _FakeProvider:
    """In-memory ``PriceIncrementProvider``: returns a fixed table, or raises."""

    def __init__(
        self, increments: Sequence[PriceIncrement] | None, *, raises: bool = False
    ) -> None:
        self._increments = increments
        self._raises = raises
        self.calls: list[Instrument] = []

    async def increments_for(self, instrument: Instrument) -> Sequence[PriceIncrement]:
        self.calls.append(instrument)
        if self._raises:
            raise PriceRuleUnavailable(f"no grid for {instrument.symbol}")
        assert self._increments is not None
        return self._increments


def _mock_ib() -> MagicMock:
    m = MagicMock(spec=ib_async.IB)
    state = {"connected": False}
    m.isConnected.side_effect = lambda: state["connected"]

    async def _connect(**_kwargs: object) -> None:
        state["connected"] = True

    m.connectAsync = AsyncMock(side_effect=_connect)
    m.disconnect.side_effect = lambda: state.__setitem__("connected", False)
    m.accountValueEvent = eventkit.Event()
    m.errorEvent = eventkit.Event()
    m.accountValues.return_value = []
    return m


def _mock_trade(order: ib_async.Order) -> MagicMock:
    trade = MagicMock(spec=ib_async.Trade)
    trade.contract = ib_async.Contract(
        symbol="QQL3", secType="STK", exchange="SMART", primaryExchange="LSEETF", currency="USD"
    )
    trade.order = order
    trade.order.orderId = 100
    trade.order.permId = 999
    trade.orderStatus = MagicMock(spec=ib_async.OrderStatus)
    trade.orderStatus.status = "PendingSubmit"
    trade.orderStatus.whyHeld = ""
    trade.log = []
    trade.fills = []
    trade.statusEvent = eventkit.Event()
    trade.fillEvent = eventkit.Event()
    trade.commissionReportEvent = eventkit.Event()
    return trade


def _qql3_order(
    *,
    limit_price: Decimal | None,
    side: OrderSide = OrderSide.BUY,
    order_type: OrderType = OrderType.LMT,
) -> Order:
    return Order(
        client_order_id=ClientOrderId(uuid4()),
        strategy_id="test",
        instrument=Instrument(
            symbol="QQL3",
            venue="XLON",
            currency="USD",
            asset_class=AssetClass.ETF,
            multiplier=Decimal("1"),
        ),
        side=side,
        quantity=Decimal("65"),
        order_type=order_type,
        time_in_force=TimeInForce.DAY,
        limit_price=limit_price,
        stop_price=None,
        parent_id=None,
        tags={},
        created_at=datetime(2026, 6, 5, 9, 0, 0, tzinfo=timezone.utc),
    )


async def _connected_broker(
    mock_ib: MagicMock,
    provider: _FakeProvider,
    *,
    policy: RoundingPolicy = RoundingPolicy.NEAREST,
) -> IBBroker:
    clock = SimClock(start=datetime(2026, 6, 5, 9, 0, 0, tzinfo=timezone.utc))
    rate_limiter = TokenBucketRateLimiter(
        clock=clock,
        config=RateLimitConfig(
            buckets={"global": RateLimitBucket(capacity=100, refill_per_second=Decimal("20"))}
        ),
    )
    client = IBClient(
        credentials=IBCredentials(host="127.0.0.1", port=4002, client_id=1, account_id="DUTEST"),
        rate_limiter=rate_limiter,
        clock=clock,
        ib=mock_ib,
    )
    resolver = IBInstrumentResolver(client)
    broker = IBBroker(
        client=client,
        resolver=resolver,
        clock=clock,
        price_rules=provider,
        rounding_policy=policy,
    )
    await broker.connect()
    return broker


async def test_submit_snaps_limit_price_to_tick_grid() -> None:
    """QQL3's 0.10 tick: a 38.52 limit snaps to 38.50 before placeOrder —
    the exact ADR-051 regression (38.52 tripped IB error 110)."""
    mock_ib = _mock_ib()
    mock_ib.placeOrder.return_value = _mock_trade(ib_async.LimitOrder("BUY", 65, 38.52))
    provider = _FakeProvider([PriceIncrement(Decimal("0"), Decimal("0.10"))])
    broker = await _connected_broker(mock_ib, provider)

    await broker.submit(_qql3_order(limit_price=Decimal("38.52")))

    placed = mock_ib.placeOrder.call_args.args[1]
    assert Decimal(str(placed.lmtPrice)) == Decimal("38.50")
    assert provider.calls  # the grid was consulted


async def test_submit_leaves_on_grid_price_unchanged() -> None:
    mock_ib = _mock_ib()
    mock_ib.placeOrder.return_value = _mock_trade(ib_async.LimitOrder("BUY", 65, 39.60))
    provider = _FakeProvider([PriceIncrement(Decimal("0"), Decimal("0.10"))])
    broker = await _connected_broker(mock_ib, provider)

    await broker.submit(_qql3_order(limit_price=Decimal("39.60")))

    placed = mock_ib.placeOrder.call_args.args[1]
    assert Decimal(str(placed.lmtPrice)) == Decimal("39.60")


async def test_submit_mkt_order_skips_grid_lookup() -> None:
    """MKT has no price — the provider is never consulted (no needless fetch)."""
    mock_ib = _mock_ib()
    mock_ib.placeOrder.return_value = _mock_trade(ib_async.MarketOrder("BUY", 65))
    provider = _FakeProvider([PriceIncrement(Decimal("0"), Decimal("0.10"))])
    broker = await _connected_broker(mock_ib, provider)

    await broker.submit(_qql3_order(limit_price=None, order_type=OrderType.MKT))

    assert provider.calls == []


async def test_submit_rejects_when_grid_unavailable() -> None:
    """PriceRuleUnavailable → REJECTED event, order never placed (ADR-051 block)."""
    mock_ib = _mock_ib()
    provider = _FakeProvider(None, raises=True)
    broker = await _connected_broker(mock_ib, provider)
    events_iter = broker.events()
    await events_iter.__anext__()  # drain ConnectionStatus

    order = _qql3_order(limit_price=Decimal("38.52"))
    cid = await broker.submit(order)

    assert cid == order.client_order_id
    event = await events_iter.__anext__()
    assert isinstance(event, OrderEvent)
    assert event.kind == OrderEventKind.REJECTED
    assert "price-rule-unavailable" in (event.reason or "")
    mock_ib.placeOrder.assert_not_called()


async def test_conservative_policy_rounds_buy_down() -> None:
    mock_ib = _mock_ib()
    mock_ib.placeOrder.return_value = _mock_trade(ib_async.LimitOrder("BUY", 65, 44.15))
    provider = _FakeProvider([PriceIncrement(Decimal("0"), Decimal("0.10"))])
    broker = await _connected_broker(mock_ib, provider, policy=RoundingPolicy.CONSERVATIVE)

    await broker.submit(_qql3_order(limit_price=Decimal("44.15"), side=OrderSide.BUY))

    placed = mock_ib.placeOrder.call_args.args[1]
    assert Decimal(str(placed.lmtPrice)) == Decimal("44.10")  # BUY rounds down, never up
