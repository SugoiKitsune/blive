"""IB broker adapter — :class:`BrokerPort` implementation, read side.

M2-IB.3b-i ships the **read side**: ``connect`` / ``disconnect`` /
``positions`` / ``account_snapshot`` / ``open_orders`` / ``events``,
plus the 30s diff-suppress :class:`AccountUpdate` emission timer per
[ADR-033](../../../../docs/decisions/DECISIONS.md#adr-033--accountupdate-event-shape-and-sampling-cadence).
The write side (``submit`` / ``cancel`` / ``replace``) lands at M2-IB.4
and currently raises :class:`NotImplementedError`.

Connection model (per [KB-2 §1](../../../../docs/kb/ib_capability_matrix.md#1-connectivity-surface)):
the underlying :class:`IBClient` does the TCP handshake at :meth:`connect`,
then this class subscribes to ``ib.accountValueEvent`` so account values
stream in via ``ib_async``'s eventkit and accumulate locally for
:meth:`account_snapshot` to compose. Positions and open orders are
queried on demand via ``reqPositionsAsync`` / ``reqAllOpenOrdersAsync``;
each consumes one ``global`` token from the rate limiter per [KB-3 §1](../../../../docs/kb/ib_pacing_spec.md#1-the-50-msgsec-client-throttle).

A background task started in :meth:`connect` (cancelled in :meth:`disconnect`)
ticks every ``account_update_interval_seconds`` (default 30s) and emits
an :class:`AccountUpdate` onto the :meth:`events` iterator if any field
crossed its diff-suppress threshold (currency-unit 0.01 / leverage 0.001
per ADR-033 §"Decision" item 2).

Position-mapping note: IB's view is per-account, not per-strategy. blive's
:class:`Position` requires a ``strategy_id``; this adapter tags positions
with the synthetic id ``f"ib_{account_id}"`` to mark them as
"broker-level positions on this IB account". Engine-side reconciliation
(M5) translates between this broker-level view and per-strategy views.
This mirrors the IGBroker convention.

What this module owns:

- TCP-handshake plumbing via :class:`IBClient`.
- Account-values accumulation (the cache underpinning :meth:`account_snapshot`).
- AccountUpdate emission timer + diff-suppress logic (ADR-033).
- IB ``Position`` / ``Trade`` parsing into broker-neutral
  :class:`blive.domain.types.Position` / :class:`Order` records.
- ConnectionStatus emission on connect/disconnect.

What is **not** here yet:

- Order-event FSM emission via ``orderStatusEvent`` /
  ``execDetailsEvent`` / ``commissionReportEvent`` — M2-IB.4 (write
  side).
- IBMarketData (``subscribe_bars`` / ``historical_bars``) — sibling
  module M2-IB.3b-ii.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, AsyncIterator
from uuid import uuid4

import ib_async

from blive.adapters.ib.client import IBClient
from blive.adapters.ib.instrument_resolver import IBInstrumentResolver
from blive.domain.events import AccountUpdate, ConnectionStatus, OrderEvent
from blive.domain.ports import BrokerEvent, ClockPort
from blive.domain.types import (
    AccountSnapshot,
    AssetClass,
    ClientOrderId,
    Fill,
    Instrument,
    Order,
    OrderEventKind,
    OrderSide,
    OrderType,
    OrderUpdate,
    Position,
    TimeInForce,
    Tradability,
)

log = logging.getLogger(__name__)


# --- DD-7 §3 reverse map: IB exchange → MIC ---------------------------------
#
# Used by the read side to synthesise broker-neutral :class:`Instrument`
# records from IB ``Contract`` fields. Values are the inverse of
# :data:`blive.adapters.ib.instrument_resolver._MIC_TO_IB_EXCHANGE`.
# A sparse table is fine — unknown IB exchanges fall back to the IB
# exchange string itself, which the M5 reconciliation refines as needed.
_IB_EXCHANGE_TO_MIC: dict[str, str] = {
    "SBF": "XPAR",
    "NASDAQ": "XNAS",
    "ISLAND": "XNAS",  # NASDAQ legacy
    "NYSE": "XNYS",
    "ARCA": "ARCX",
    "BATS": "BATS",
    "LSE": "XLON",
    "IBIS": "XETR",
}


# IB ``secType`` → :class:`AssetClass`. Disambiguation is intentional
# best-effort — IB collapses EQUITY and ETF into "STK", so the reverse
# defaults to EQUITY (more general); strategies that need to distinguish
# (e.g. ADR-027 integer-share rounding scopes) carry the canonical
# :class:`Instrument` with ``asset_class=ETF`` from their original
# construction site, not from this reverse lookup.
_SEC_TYPE_TO_ASSET_CLASS: dict[str, AssetClass] = {
    "STK": AssetClass.EQUITY,
    "IND": AssetClass.INDEX,
    "CASH": AssetClass.FX,
    "FUT": AssetClass.FUTURE,
    "OPT": AssetClass.OPTION,
}


# IB AccountValue tags relevant to :class:`AccountSnapshot`.
#
# IB pushes account state as individual (tag, value, currency) tuples.
# We accumulate on ``accountValuesEvent`` and rebuild the snapshot in
# :meth:`account_snapshot`. The "BASE" pseudo-currency carries the
# account's aggregate values; per-currency rows carry the per-currency
# breakdown (used for ``cash_by_ccy``).
_TAG_NET_LIQUIDATION = "NetLiquidationByCurrency"
_TAG_TOTAL_CASH = "TotalCashBalance"
_TAG_BUYING_POWER = "BuyingPower"
_TAG_GROSS_POSITION = "GrossPositionValue"
_TAG_MAINT_MARGIN = "MaintMarginReq"


# Per-field thresholds for the AccountUpdate diff-suppress timer per
# [ADR-033](../../../../docs/decisions/DECISIONS.md#adr-033--accountupdate-event-shape-and-sampling-cadence)
# §"Decision" item 2. Currency-unit fields (equity, cash_by_ccy[ccy],
# buying_power, gross_exposure, net_exposure, margin_used) use 0.01;
# the dimensionless ``leverage`` ratio uses 0.001 (3 d.p.).
_ACCOUNT_VALUE_THRESHOLD: Decimal = Decimal("0.01")
_LEVERAGE_THRESHOLD: Decimal = Decimal("0.001")


class IBShapeError(Exception):
    """Raised when an IB-side response (positions, account values, orders)
    cannot be parsed into a broker-neutral domain object — typically a
    missing field, unexpected type, or unknown enum value. The fault is
    on the IB side (or in our parser); the connection itself is fine."""


# IB orderStatus values that indicate venue acceptance (the FSM moves
# SUBMITTED → ACCEPTED on first occurrence).
_ACCEPTED_STATUSES = frozenset({"Submitted", "PreSubmitted"})

# IB orderStatus values that indicate user-/system-initiated cancellation.
_CANCELLED_STATUSES = frozenset({"Cancelled", "ApiCancelled"})

# IB orderStatus value indicating the order was rejected (or otherwise
# inactivated). IB also uses "Inactive" for orders held during pre-market;
# for those, an explicit "Submitted" follows; we only emit REJECTED if a
# whyHeld / lastFillPrice rejection signal is set.
_REJECTED_STATUS = "Inactive"


@dataclass
class _OrderTrackingState:
    """Per-order tracking maintained between submit and a terminal event.

    Each blive submit() registers a fresh entry; the per-trade event
    handlers consult and update it to decide which FSM event to emit.
    Cleared when the order reaches a terminal state (FILLED / CANCELED /
    REJECTED) — but we keep the entry around for cancel-path lookup; M5
    reconciliation may revisit.
    """

    client_order_id: ClientOrderId
    total_quantity: Decimal
    instrument: Instrument
    side: OrderSide
    accepted_emitted: bool = False
    terminal_emitted: bool = False
    seen_exec_ids: set[str] = field(default_factory=set)
    cumulative_filled: Decimal = Decimal("0")


class IBBroker:
    """`BrokerPort` adapter for IB Paper / live, read side.

    Wraps a single :class:`IBClient` (TCP handshake + rate limiter) plus
    an :class:`IBInstrumentResolver` (Instrument↔Contract). Account
    values accumulate on ``ib.accountValuesEvent``; positions and
    open orders are fetched on demand. The events() iterator yields
    :class:`ConnectionStatus` records for M2-IB.3b-i; richer events
    (AccountUpdate, OrderEvent) land at the 3b-i timer follow-up and
    M2-IB.4 respectively.
    """

    def __init__(
        self,
        *,
        client: IBClient,
        resolver: IBInstrumentResolver,
        clock: ClockPort,
        account_update_interval_seconds: float = 30.0,
    ) -> None:
        self._client = client
        self._resolver = resolver
        self._clock = clock
        self._account_update_interval_seconds = account_update_interval_seconds
        self._connected = False
        self._events: asyncio.Queue[BrokerEvent] = asyncio.Queue()
        # Latest accumulated AccountValue tuples, keyed by (currency, tag).
        # Currency "" means "BASE" / aggregate. Cleared on disconnect.
        self._account_values: dict[tuple[str, str], str] = {}
        # Cached event handler reference — needed so disconnect can detach
        # via ``-=`` symmetrically with the ``+=`` registration in connect.
        self._account_value_handler = self._on_account_value
        # Last-emitted snapshot for the 30s diff-suppress timer per ADR-033.
        # None until the first tick; reset on disconnect.
        self._last_emitted_snapshot: AccountSnapshot | None = None
        # Background task running :meth:`_account_update_loop`. Cancelled on
        # disconnect; recreated on connect.
        self._account_update_task: asyncio.Task[None] | None = None
        # Active orders submitted via this broker. Used by :meth:`cancel` to
        # look up the underlying ``ib_async.Trade`` for ``ib.cancelOrder``,
        # and by per-trade event handlers to correlate FSM transitions back
        # to the originating ``client_order_id``.
        self._trades_by_client_id: dict[ClientOrderId, ib_async.Trade] = {}
        self._order_tracking: dict[ClientOrderId, _OrderTrackingState] = {}
        # Latest IB error keyed by ``reqId`` (which equals ``orderId`` for
        # order-related errors). Some IB rejection paths — observed at
        # M2-IB.6.2 with error 201 PRIIPs/KID — deliver the error text
        # *only* on ``ib.errorEvent`` (not into ``trade.log``), so the
        # per-trade ``statusEvent`` handler has no message to surface.
        # The stash bridges the global error channel to the Inactive-status
        # rejection path (see :meth:`_on_order_status`); entries are popped
        # on terminal-event emission to bound memory.
        self._error_by_order_id: dict[int, tuple[int, str]] = {}
        # Cached handler reference for ``ib.errorEvent`` subscription —
        # symmetric with :attr:`_account_value_handler` so disconnect can
        # detach via ``-=``.
        self._ib_error_handler = self._on_ib_error

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def broker_strategy_id(self) -> str:
        """Synthetic strategy id used for IB-side positions read back from
        the broker. Engine-side reconciliation (M5) translates between
        this broker-level view and per-strategy views."""
        return f"ib_{self._client.credentials.account_id}"

    # --- BrokerPort: connect / disconnect -----------------------------------

    async def connect(self) -> None:
        """Open the IB connection and start streaming account values.

        Idempotent: re-calling on a connected broker is a no-op.
        ``ib_async.IB.connectAsync`` (called inside :meth:`IBClient.connect`)
        already triggers ``reqAccountUpdatesAsync(account)`` + ``reqPositionsAsync``
        + ``reqOpenOrdersAsync`` and waits for the initial batch — so by
        the time this returns, ``ib.accountValues(account)`` is populated.
        We copy that initial state into our local cache, then attach
        ``ib.accountValueEvent`` so subsequent IB pushes update us.

        Emits a :class:`ConnectionStatus(connected=True)` event on the
        :meth:`events` iterator.
        """
        if self._connected:
            return
        await self._client.connect()
        ib = self._client.ib
        # Seed local cache from ib_async's internal cache (populated by
        # connectAsync's `reqAccountUpdatesAsync` initial batch).
        for av in ib.accountValues(self._client.credentials.account_id):
            self._on_account_value(av)
        # Subscribe for future updates.
        ib.accountValueEvent += self._account_value_handler
        # Subscribe to the global error channel so we can recover error
        # text for rejection paths that don't mirror it into ``trade.log``
        # (M2-IB.6.2 finding — error 201 PRIIPs/KID is one such path).
        ib.errorEvent += self._ib_error_handler
        self._connected = True
        # Start the 30s diff-suppress AccountUpdate emission timer per
        # ADR-033 §"Decision" item 2.
        self._account_update_task = asyncio.create_task(
            self._account_update_loop(),
            name=f"ib-broker-account-update-{self._client.credentials.account_id}",
        )
        await self._events.put(
            ConnectionStatus(
                connected=True,
                detail=(
                    f"IB broker connected (account "
                    f"{self._client.credentials.account_id} via "
                    f"{self._client.credentials.host}:{self._client.credentials.port})"
                ),
                time_utc=self._clock.now(),
            )
        )

    async def disconnect(self) -> None:
        """Close the IB connection and stop streaming account values.

        Idempotent: calling on a disconnected broker is a no-op.
        Best-effort cleanup — any underlying error is logged and
        suppressed (the broker still transitions to disconnected state
        and emits the corresponding :class:`ConnectionStatus`).

        Clears the accumulated account-value cache so a fresh
        :meth:`connect` starts from a clean slate (matches IB's own
        re-subscription behaviour).
        """
        if not self._connected:
            return
        # Cancel the AccountUpdate emission timer first so it doesn't
        # interleave with cache teardown.
        task = self._account_update_task
        self._account_update_task = None
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as exc:  # noqa: BLE001 — best-effort cleanup
                log.warning("AccountUpdate loop raised on cancel; suppressing: %s", exc)
        ib = self._client.ib
        try:
            ib.accountValueEvent -= self._account_value_handler
        except Exception as exc:  # noqa: BLE001 — best-effort cleanup
            log.warning("Detaching ib.accountValueEvent handler raised; suppressing: %s", exc)
        try:
            ib.errorEvent -= self._ib_error_handler
        except Exception as exc:  # noqa: BLE001 — best-effort cleanup
            log.warning("Detaching ib.errorEvent handler raised; suppressing: %s", exc)
        # Note: no explicit reqAccountUpdates(False, ...) — ib_async's TWS
        # API wrapping doesn't expose an unsubscribe path; the subscription
        # is torn down implicitly when the underlying socket disconnects.
        await self._client.disconnect()
        self._connected = False
        self._account_values.clear()
        self._last_emitted_snapshot = None
        self._error_by_order_id.clear()
        await self._events.put(
            ConnectionStatus(
                connected=False,
                detail=(
                    f"IB broker disconnected (account " f"{self._client.credentials.account_id})"
                ),
                time_utc=self._clock.now(),
            )
        )

    # --- BrokerPort: read methods -------------------------------------------

    async def positions(self) -> list[Position]:
        """Return IB's view of the account's open positions.

        Calls ``ib.reqPositionsAsync`` (consumes one ``global`` token);
        each returned ``ib_async.Position`` is parsed into a broker-neutral
        :class:`Position` tagged with :attr:`broker_strategy_id`.
        """
        self._require_connected()
        await self._client.rate_limiter.acquire("global")
        ib_positions = await self._client.ib.reqPositionsAsync()
        now = self._clock.now()
        out: list[Position] = []
        acct = self._client.credentials.account_id
        for ib_pos in ib_positions:
            if ib_pos is None:
                continue
            # A login can serve SEVERAL accounts (the live one serves U3481003 + U23454308): positions of any other
            # account are not ours to size against or sell.
            if getattr(ib_pos, "account", None) and ib_pos.account != acct:
                continue
            try:
                position = self._parse_ib_position(ib_pos, updated_at=now)
            except (IBShapeError, ValueError, AttributeError, TypeError) as exc:
                log.warning("IB Position skipped (parse failure): %s", exc)
                continue
            out.append(position)
        return out

    async def account_snapshot(self) -> AccountSnapshot:
        """Compose an :class:`AccountSnapshot` from accumulated account values.

        Reads the cache populated by ``accountValuesEvent`` since
        :meth:`connect`. Raises :class:`IBShapeError` if the cache is
        empty (no values pushed yet — caller should retry after a brief
        wait, or call this method only after the first account-update
        batch has arrived).

        Does **not** issue a wire request — the data is push-streamed.
        Cadence-based emission (30s diff-suppress per [ADR-033](../../../../docs/decisions/DECISIONS.md#adr-033--accountupdate-event-shape-and-sampling-cadence))
        is the M2-IB.3b-i follow-up.
        """
        self._require_connected()
        if not self._account_values:
            raise IBShapeError(
                "IB account values not yet received — accountValuesEvent has "
                "not pushed any values since connect(). The first batch "
                "typically arrives within ~500ms of connect(); retry after a "
                "brief wait."
            )
        return self._build_account_snapshot(taken_at=self._clock.now())

    async def open_orders(self) -> list[Order]:
        """Return IB's view of working orders.

        Calls ``ib.reqAllOpenOrdersAsync`` (consumes one ``global``
        token); each returned ``ib_async.Trade`` is parsed into a
        broker-neutral :class:`Order` tagged with
        :attr:`broker_strategy_id`.
        """
        self._require_connected()
        await self._client.rate_limiter.acquire("global")
        ib_trades = await self._client.ib.reqAllOpenOrdersAsync()
        out: list[Order] = []
        for trade in ib_trades:
            if trade is None:
                continue
            try:
                order = self._parse_ib_trade_to_order(trade)
            except (IBShapeError, ValueError, AttributeError, TypeError) as exc:
                log.warning("IB Trade skipped (parse failure): %s", exc)
                continue
            out.append(order)
        return out

    def events(self) -> AsyncIterator[BrokerEvent]:
        """Async iterator over connection-state + (M2-IB.3b-i timer) account
        update events.

        For M2-IB.3b-i the iterator yields :class:`ConnectionStatus`
        records (connect / disconnect) plus :class:`AccountUpdate` records
        emitted by the 30s diff-suppress timer per [ADR-033](../../../../docs/decisions/DECISIONS.md#adr-033--accountupdate-event-shape-and-sampling-cadence).
        :class:`OrderEvent` events arrive at M2-IB.4 (write side).
        """
        return self._events_stream()

    async def _events_stream(self) -> AsyncIterator[BrokerEvent]:
        while True:
            event = await self._events.get()
            yield event

    # --- BrokerPort: write methods (M2-IB.4) --------------------------------

    async def submit(self, order: Order) -> ClientOrderId:
        """Place ``order`` on IB and emit the SUBMITTED event.

        Maps the broker-neutral :class:`Order` to ``ib_async.Order``, calls
        :meth:`ib.placeOrder` (consumes one ``global`` rate-limit token),
        registers per-trade event handlers (statusEvent / fillEvent), and
        emits an :class:`OrderEvent(SUBMITTED)` immediately. Subsequent
        FSM transitions (ACCEPTED / PARTIAL_FILL / FILLED / CANCELED /
        REJECTED) emit asynchronously as the per-trade events fire.

        Returns the original ``client_order_id`` so the caller can
        correlate across :meth:`events`. Idempotent on the
        ``client_order_id`` — re-submitting an already-tracked id raises
        :class:`RuntimeError` (matches REQUIREMENTS §5.3 idempotency
        framing — the engine, not the FSM, owns the dedup).

        Raises :class:`NotImplementedError` for ``MOC`` / ``LOC`` / ``OPG``
        order types pending v1.1 (the v1 path needs only ``MKT`` / ``LMT``
        / ``STP`` / ``STP_LMT`` per REQUIREMENTS §5.3).
        """
        self._require_connected()
        # Order.client_order_id is typed as UUID per DD-1 §2.4; the BrokerPort
        # surface uses the ClientOrderId NewType. Cast at the boundary so
        # the broker's dict keys + return type align with the Port.
        client_order_id = ClientOrderId(order.client_order_id)

        if client_order_id in self._trades_by_client_id:
            raise RuntimeError(
                f"client_order_id {client_order_id} already submitted. "
                f"REQUIREMENTS §5.3 idempotency: re-submission must be a "
                f"no-op at the engine layer; the broker treats it as an "
                f"error since the FSM is in SUBMITTED+ already."
            )

        contract = self._resolver.to_contract(order.instrument)
        ib_order = _blive_to_ib_order(order)
        # Stamp the client_order_id into the IB orderRef so reconciliation
        # (M5) can correlate persisted-state events back to the originating
        # blive order without depending on this in-process map.
        ib_order.orderRef = str(client_order_id)
        # Name the account on every order: a multi-account login rejects an order without one (IB-435 "You must
        # specify an account"), and naming it means the order can only ever land in the configured account.
        ib_order.account = self._client.credentials.account_id

        await self._client.rate_limiter.acquire("global")
        # ib_async.IB.placeOrder is sync (returns a Trade immediately and
        # the wire send is async-internal). The asyncio loop dispatches
        # the wire send on the next iteration; no await needed here.
        trade = self._client.ib.placeOrder(contract, ib_order)

        tracking = _OrderTrackingState(
            client_order_id=client_order_id,
            total_quantity=order.quantity,
            instrument=order.instrument,
            side=order.side,
        )
        self._trades_by_client_id[client_order_id] = trade
        self._order_tracking[client_order_id] = tracking

        # Wire per-trade handlers. Closures capture client_order_id so
        # there's no global routing table needed; ib_async fires events
        # on this specific Trade object as IB pushes orderStatus /
        # execDetails / commissionReport messages.
        trade.statusEvent += self._make_status_handler(client_order_id)
        trade.fillEvent += self._make_fill_handler(client_order_id)

        await self._events.put(
            OrderEvent(
                client_order_id=client_order_id,
                venue_order_id=str(trade.order.orderId) if trade.order.orderId else None,
                kind=OrderEventKind.SUBMITTED,
                reason=None,
                time_utc=self._clock.now(),
            )
        )
        return client_order_id

    async def cancel(self, client_order_id: ClientOrderId) -> None:
        """Cancel a pending or working order.

        Looks up the underlying ``ib_async.Trade`` and calls
        :meth:`ib.cancelOrder`. The CANCELED event emission happens
        asynchronously when IB pushes the resulting orderStatus
        ``Cancelled`` event (handled by the per-trade status handler
        registered in :meth:`submit`).

        Raises :class:`KeyError` if ``client_order_id`` is unknown to
        this broker instance (e.g., the order was submitted in a prior
        session and not yet reconciled — M5 work).
        """
        self._require_connected()
        trade = self._trades_by_client_id.get(client_order_id)
        if trade is None:
            raise KeyError(
                f"client_order_id {client_order_id} unknown to IBBroker; "
                f"not in the active-orders map. Reconciliation (M5) is "
                f"required to cancel orders submitted in a prior session."
            )
        await self._client.rate_limiter.acquire("global")
        # ib_async.IB.cancelOrder is sync — submits the cancel request
        # over the wire; the resulting Cancelled / ApiCancelled status
        # arrives via trade.statusEvent.
        self._client.ib.cancelOrder(trade.order)

    async def replace(self, client_order_id: ClientOrderId, new: OrderUpdate) -> None:
        """Replace a pending order's fields (quantity / limit / stop).

        Not implemented at M2-IB.4a. IB's TWS API doesn't support atomic
        replace for all order types; the standard pattern is
        cancel-then-new with a fresh ``client_order_id`` per
        REQUIREMENTS §5.3. M2-IB.4b ships the cancel-then-new wrapper
        if a Phase 1 strategy needs in-flight order modification (the
        Phase 1 daily strategy doesn't — submits at rebalance, no in-day
        changes).
        """
        raise NotImplementedError(
            "IBBroker.replace lands at M2-IB.4b. Phase 1 daily-rebalance "
            "strategy doesn't modify in-flight orders; cancel-then-new "
            "wrapper deferred until a strategy needs it."
        )

    # --- Internals: per-trade order-event handlers --------------------------

    def _make_status_handler(self, client_order_id: ClientOrderId) -> Any:
        """Build a closure that handles ``trade.statusEvent`` for the
        order identified by ``client_order_id``.

        ib_async fires ``trade.statusEvent`` whenever the venue pushes a
        new ``orderStatus`` for this order. We map IB's status string to
        the FSM transition and emit the corresponding
        :class:`OrderEvent` if (a) we haven't already emitted that
        transition (idempotency: IB sometimes re-pushes the same status),
        and (b) the order isn't already in a terminal state.
        """

        def _handler(trade: ib_async.Trade) -> None:
            self._on_order_status(client_order_id, trade)

        return _handler

    def _make_fill_handler(self, client_order_id: ClientOrderId) -> Any:
        """Build a closure that handles ``trade.fillEvent`` for the
        order identified by ``client_order_id``.

        Fires after each ``execDetails`` push from IB. The Fill payload
        carries price + quantity + commission (commission may not yet
        be populated if the corresponding ``commissionReport`` hasn't
        arrived; v1 emits with commission=0 in that case — M5 may
        re-emit with commission once commissionReport arrives).
        """

        def _handler(trade: ib_async.Trade, fill: ib_async.Fill) -> None:
            self._on_order_fill(client_order_id, trade, fill)

        return _handler

    def _on_order_status(self, client_order_id: ClientOrderId, trade: ib_async.Trade) -> None:
        """Handle a ``trade.statusEvent`` push.

        Fires for every IB ``orderStatus`` update. We map the textual
        status to FSM transitions:

        - ``"Submitted"`` / ``"PreSubmitted"`` → emit ACCEPTED (once).
        - ``"Cancelled"`` / ``"ApiCancelled"`` → emit CANCELED.
        - ``"Inactive"`` → emit REJECTED (with the IB whyHeld string as
          reason; defensive — IB also uses Inactive for halted symbols
          where it's transitional, but in practice for blive's adapter
          path this means rejected).
        - ``"Filled"`` / ``"PendingSubmit"`` / ``"PendingCancel"`` →
          ignore (FILLED handled via fillEvent; the others are
          transitional).
        """
        tracking = self._order_tracking.get(client_order_id)
        if tracking is None or tracking.terminal_emitted:
            return
        status = trade.orderStatus.status

        if status in _ACCEPTED_STATUSES and not tracking.accepted_emitted:
            tracking.accepted_emitted = True
            asyncio.create_task(
                self._events.put(
                    OrderEvent(
                        client_order_id=client_order_id,
                        venue_order_id=str(trade.order.orderId) if trade.order.orderId else None,
                        kind=OrderEventKind.ACCEPTED,
                        reason=None,
                        time_utc=self._clock.now(),
                    )
                )
            )
        elif status in _CANCELLED_STATUSES:
            tracking.terminal_emitted = True
            # IB uses status="Cancelled" for several distinct semantic cases:
            #   1. Pre-acceptance system rejections (risk precautions,
            #      direct-routing blocks like error 10311) — REJECTED.
            #   2. Post-acceptance engine-initiated cancels — CANCELED.
            # The discriminator is `tracking.accepted_emitted`: if the order
            # never reached ACCEPTED, a non-zero errorCode in the trade log
            # is the rejection signal. Once ACCEPTED has been emitted, any
            # errorCode in the log is contextual (e.g., warning 399 "order
            # held until next session open") and the Cancelled status is
            # an ordinary cancel — CANCELED per INV-13 §5.
            # See INV-14 for the catalogued codes; the pre-acceptance
            # disambiguation was the original M2-IB.4a-rejected motivation.
            error_log = _last_error_log_entry(trade) if not tracking.accepted_emitted else None
            if error_log is not None:
                reason = _rejected_reason_from_log_entry(error_log)
                kind = OrderEventKind.REJECTED
            else:
                reason = _cancel_reason_from_status(status, trade)
                kind = OrderEventKind.CANCELED
            self._error_by_order_id.pop(int(trade.order.orderId), None)
            asyncio.create_task(
                self._events.put(
                    OrderEvent(
                        client_order_id=client_order_id,
                        venue_order_id=str(trade.order.orderId) if trade.order.orderId else None,
                        kind=kind,
                        reason=reason,
                        time_utc=self._clock.now(),
                    )
                )
            )
        elif status == _REJECTED_STATUS:
            tracking.terminal_emitted = True
            # Deferred emission via :meth:`_emit_rejected_via_inactive` —
            # ib_async dispatches ``statusEvent`` BEFORE ``errorEvent`` for
            # IB-error rejections (M2-IB.6.2 wire-finding 2026-05-04), so a
            # synchronous reason-lookup here would read the per-orderId
            # error stash before it has been populated. Yielding once via
            # the async helper lets the errorEvent handler run first.
            asyncio.create_task(self._emit_rejected_via_inactive(client_order_id, trade))

    def _on_order_fill(
        self,
        client_order_id: ClientOrderId,
        trade: ib_async.Trade,
        fill: ib_async.Fill,
    ) -> None:
        """Handle a ``trade.fillEvent`` push.

        Constructs a broker-neutral :class:`Fill` and emits PARTIAL_FILL
        (cumulative < total) or FILLED (cumulative == total). Dedupes
        via ``execDetails.execId`` since IB occasionally re-pushes
        execDetails on reconnect (per [INV-13 §6](../../../../docs/inv/order_state_transitions.md#6-idempotency)).
        """
        tracking = self._order_tracking.get(client_order_id)
        if tracking is None or tracking.terminal_emitted:
            return

        execution = fill.execution
        exec_id = execution.execId if execution is not None else ""
        if not exec_id:
            log.warning(
                "IB fillEvent without execId; skipping for client_order_id=%s", client_order_id
            )
            return
        if exec_id in tracking.seen_exec_ids:
            return  # dedupe
        tracking.seen_exec_ids.add(exec_id)

        # ACCEPTED is implied by the first fill if statusEvent didn't
        # fire first (rare but observed on fast fills).
        if not tracking.accepted_emitted:
            tracking.accepted_emitted = True
            asyncio.create_task(
                self._events.put(
                    OrderEvent(
                        client_order_id=client_order_id,
                        venue_order_id=str(trade.order.orderId) if trade.order.orderId else None,
                        kind=OrderEventKind.ACCEPTED,
                        reason=None,
                        time_utc=self._clock.now(),
                    )
                )
            )

        fill_qty = Decimal(str(execution.shares)) if execution is not None else Decimal("0")
        fill_price = Decimal(str(execution.price)) if execution is not None else Decimal("0")
        commission_obj = fill.commissionReport
        commission = (
            Decimal(str(commission_obj.commission))
            if commission_obj is not None and commission_obj.commission
            else Decimal("0")
        )
        currency = (
            commission_obj.currency
            if commission_obj is not None and commission_obj.currency
            else tracking.instrument.currency
        )
        fill_time = (
            execution.time
            if execution is not None and isinstance(execution.time, datetime)
            else self._clock.now()
        )

        blive_fill = Fill(
            client_order_id=client_order_id,
            venue_order_id=str(trade.order.orderId) if trade.order.orderId else "",
            venue_exec_id=exec_id,
            instrument=tracking.instrument,
            side=tracking.side,
            quantity=fill_qty,
            price=fill_price,
            commission=commission,
            currency=currency,
            time_utc=fill_time,
        )
        tracking.cumulative_filled += fill_qty
        terminal = tracking.cumulative_filled >= tracking.total_quantity
        kind = OrderEventKind.FILLED if terminal else OrderEventKind.PARTIAL_FILL
        if terminal:
            tracking.terminal_emitted = True
            self._error_by_order_id.pop(int(trade.order.orderId), None)

        asyncio.create_task(
            self._events.put(
                OrderEvent(
                    client_order_id=client_order_id,
                    venue_order_id=str(trade.order.orderId) if trade.order.orderId else None,
                    kind=kind,
                    reason=None,
                    time_utc=self._clock.now(),
                    fill=blive_fill,
                )
            )
        )

    # --- Internals: AccountUpdate emission timer (ADR-033) ------------------

    async def _account_update_loop(self) -> None:
        """Background task: every ``account_update_interval_seconds`` (30s
        wall-clock by default), invoke :meth:`_account_update_tick`.

        Cancelled by :meth:`disconnect`. Uses :func:`asyncio.sleep` rather
        than :meth:`ClockPort.sleep` so the cadence is real-time even
        when tests inject a :class:`SimClock` for timestamps. Tests of
        the tick logic call :meth:`_account_update_tick` directly rather
        than running this loop.
        """
        try:
            while self._connected:
                await asyncio.sleep(self._account_update_interval_seconds)
                if not self._connected:
                    return
                await self._account_update_tick()
        except asyncio.CancelledError:
            raise

    async def _account_update_tick(self) -> None:
        """One iteration of the AccountUpdate emission loop.

        Builds the current snapshot from the accumulated account-values
        cache; if any field has changed beyond its threshold (or this is
        the first tick after connect), emits an
        :class:`AccountUpdate` event and updates :attr:`_last_emitted_snapshot`.
        Empty cache or build failure → silent skip (no event, no error
        propagation; the next tick re-evaluates).
        """
        if not self._account_values:
            return
        try:
            current = self._build_account_snapshot(taken_at=self._clock.now())
        except IBShapeError:
            return
        if not self._should_emit_account_update(current):
            return
        await self._events.put(AccountUpdate(snapshot=current, time_utc=self._clock.now()))
        self._last_emitted_snapshot = current

    def _should_emit_account_update(self, current: AccountSnapshot) -> bool:
        """Per ADR-033 §"Decision" item 2: emit when any field has moved
        beyond its threshold compared to the last emitted snapshot.

        Per-field thresholds (currency-unit values use 0.01; ``leverage``
        uses 0.001 since it is a ratio). On the first tick (no
        ``_last_emitted_snapshot``), always emit — there is no baseline
        to diff against and the consumer (UI / persistence) needs the
        initial state.
        """
        last = self._last_emitted_snapshot
        if last is None:
            return True

        if abs(current.equity - last.equity) >= _ACCOUNT_VALUE_THRESHOLD:
            return True
        if abs(current.buying_power - last.buying_power) >= _ACCOUNT_VALUE_THRESHOLD:
            return True
        if abs(current.gross_exposure - last.gross_exposure) >= _ACCOUNT_VALUE_THRESHOLD:
            return True
        if abs(current.net_exposure - last.net_exposure) >= _ACCOUNT_VALUE_THRESHOLD:
            return True
        if abs(current.margin_used - last.margin_used) >= _ACCOUNT_VALUE_THRESHOLD:
            return True
        if abs(current.leverage - last.leverage) >= _LEVERAGE_THRESHOLD:
            return True

        # cash_by_ccy: union of currencies; treat absent currency as zero.
        all_ccys = set(current.cash_by_ccy) | set(last.cash_by_ccy)
        for ccy in all_ccys:
            delta = abs(
                current.cash_by_ccy.get(ccy, Decimal("0")) - last.cash_by_ccy.get(ccy, Decimal("0"))
            )
            if delta >= _ACCOUNT_VALUE_THRESHOLD:
                return True
        return False

    # --- Internals: event handlers ------------------------------------------

    def _on_account_value(self, account_value: ib_async.AccountValue) -> None:
        """Accumulate one IB ``AccountValue`` push.

        Called by ``ib.accountValuesEvent``; runs on the asyncio loop
        thread (ib_async dispatches eventkit handlers from the loop).
        Stores the raw string value keyed by (currency, tag); parsing
        deferred to :meth:`_build_account_snapshot`.

        Multiple account values for the same (currency, tag) overwrite —
        the latest push wins, matching IB's "live state" semantics.
        """
        currency = account_value.currency or ""
        tag = account_value.tag or ""
        if not tag:
            return  # malformed push; drop quietly
        # Filter: only the account we subscribed to. ib_async sometimes
        # forwards values for sub-accounts when a master client connects.
        if account_value.account and account_value.account != self._client.credentials.account_id:
            return
        self._account_values[(currency, tag)] = account_value.value

    def _on_ib_error(
        self,
        reqId: int,
        errorCode: int,
        errorString: str,
        contract: Any = None,
    ) -> None:
        """Stash the latest IB error keyed by ``reqId``.

        ib_async dispatches ``ib.errorEvent`` with ``(reqId, errorCode,
        errorString, contract)`` for every error push from IB. For
        order-related errors, ``reqId`` equals the order's ``orderId``,
        so we can correlate back to the rejected trade in
        :meth:`_on_order_status` when the per-trade ``trade.log`` doesn't
        carry the message (observed at M2-IB.6.2 with error 201
        PRIIPs/KID — IB delivers the rejection text on this channel only,
        the trade transitions to ``status="Inactive"`` with empty
        ``log[-1].message`` and empty ``whyHeld``).

        Connection-level events use ``reqId == -1`` (or other negative
        sentinels); we skip those — the connection lifecycle is handled
        elsewhere and they don't correspond to specific orders.

        ``contract`` is unused by the stash but kept in the signature so
        ib_async's eventkit dispatch matches the published handler shape.
        """
        if reqId <= 0:
            return
        self._error_by_order_id[int(reqId)] = (int(errorCode), errorString or "")

    async def _emit_rejected_via_inactive(
        self,
        client_order_id: ClientOrderId,
        trade: ib_async.Trade,
    ) -> None:
        """Deferred REJECTED emission for the ``status="Inactive"`` path.

        ib_async dispatches the per-trade ``statusEvent`` (which delivers
        ``status="Inactive"``) **before** the global ``errorEvent`` (which
        delivers the error code + message) for IB-error rejections —
        observed at M2-IB.6.2 against IB Paper with error 201 PRIIPs/KID.
        A synchronous reason-lookup at the moment the status handler fires
        therefore reads an empty :attr:`_error_by_order_id` stash and falls
        through to the generic ``"rejected"`` placeholder, losing the
        diagnostic detail INV-14 v0.6 documents.

        The fix is to defer the lookup by yielding the event loop a few
        times before consulting the stash. ib_async's eventkit dispatches
        Events synchronously inside a single wire-message tick, so by the
        time control returns to us after ``await asyncio.sleep(0)`` the
        ``errorEvent`` handler has run and populated the stash. Multiple
        yields are belt-and-braces in case ib_async splits dispatch across
        loop ticks under load — fast (microseconds) and tolerant.

        Reason-lookup chain:

        1. Trade-state extraction (``trade.log[-1].message`` / ``whyHeld``)
           per :func:`_rejected_reason_from_trade`.
        2. ``_error_by_order_id`` stash keyed by ``trade.order.orderId``,
           formatted as ``"ib:{code} {message}"`` per INV-14 v0.6.
        3. Generic ``"rejected"`` fallback + warning log so the breadcrumb
           is findable in retrospective analysis when neither channel
           carried text (would indicate an ib_async dispatch regression).
        """
        # Yield enough times for any pending errorEvent dispatch to complete.
        # Three iterations covers the common case (one tick) plus a margin.
        for _ in range(3):
            await asyncio.sleep(0)

        rejected_reason: str | None = _rejected_reason_from_trade(trade)
        if rejected_reason is None:
            rejected_reason = self._reason_from_error_stash(trade.order.orderId)
        if rejected_reason is None:
            log.warning(
                "IBBroker: REJECTED via Inactive with no recoverable reason "
                "(orderId=%s, client_order_id=%s); falling back to 'rejected'. "
                "Inspect ib_async errorEvent dispatch if this surfaces in "
                "production.",
                trade.order.orderId,
                client_order_id,
            )
            rejected_reason = "rejected"
        self._error_by_order_id.pop(int(trade.order.orderId), None)
        await self._events.put(
            OrderEvent(
                client_order_id=client_order_id,
                venue_order_id=str(trade.order.orderId) if trade.order.orderId else None,
                kind=OrderEventKind.REJECTED,
                reason=rejected_reason,
                time_utc=self._clock.now(),
            )
        )

    def _reason_from_error_stash(self, order_id: int) -> str | None:
        """Return the formatted rejection reason for ``order_id`` from the
        ``errorEvent`` stash, or ``None`` if no error is on file.

        Format mirrors :func:`_rejected_reason_from_log_entry` for
        consistency with INV-14 v0.5+: ``"ib:{errorCode} {message}"``.
        Empty message degrades to ``"ib:{errorCode}"``.
        """
        entry = self._error_by_order_id.get(int(order_id))
        if entry is None:
            return None
        code, message = entry
        if message:
            return f"ib:{code} {message}"
        return f"ib:{code}"

    # --- Internals: parsers -------------------------------------------------

    def _require_connected(self) -> None:
        if not self._connected:
            raise RuntimeError("IBBroker.connect() must be called before read / write methods")

    def _parse_ib_position(self, ib_pos: ib_async.Position, *, updated_at: datetime) -> Position:
        """Map ``ib_async.Position`` to broker-neutral :class:`Position`."""
        contract = ib_pos.contract
        if contract is None:
            raise IBShapeError("IB Position has no contract")
        instrument = self._instrument_from_contract(contract)
        quantity = Decimal(str(ib_pos.position))
        avg_cost = Decimal(str(ib_pos.avgCost))
        opened_at = updated_at if quantity != 0 else None
        return Position(
            instrument=instrument,
            strategy_id=self.broker_strategy_id,
            quantity=quantity,
            avg_cost=avg_cost if quantity != 0 else Decimal("0"),
            currency=instrument.currency,
            opened_at=opened_at,
            updated_at=updated_at,
        )

    def _parse_ib_trade_to_order(self, trade: ib_async.Trade) -> Order:
        """Map ``ib_async.Trade`` to broker-neutral :class:`Order`."""
        ib_order = getattr(trade, "order", None)
        contract = getattr(trade, "contract", None)
        if ib_order is None or contract is None:
            raise IBShapeError("IB Trade missing order or contract")

        instrument = self._instrument_from_contract(contract)
        side = _parse_order_side(getattr(ib_order, "action", ""))
        order_type = _parse_order_type(getattr(ib_order, "orderType", ""))
        time_in_force = _parse_time_in_force(getattr(ib_order, "tif", ""))

        # Order ids: IB has its own integer orderId; blive uses UUID. For
        # orders that didn't originate in blive (manual TWS orders, leftover
        # working orders from a prior session), synthesise a UUID and tag
        # the original IB orderId for traceability.
        client_order_id = uuid4()
        ib_order_id = getattr(ib_order, "orderId", None)
        tags: dict[str, str] = {}
        if ib_order_id is not None:
            tags["ib_order_id"] = str(ib_order_id)
        ib_perm_id = getattr(ib_order, "permId", None)
        if ib_perm_id is not None:
            tags["ib_perm_id"] = str(ib_perm_id)

        # Limit / stop prices: IB stores 0.0 as "no price" for non-LMT/STP
        # types; we surface ``None`` to match DD-1 §2.4 invariants.
        limit_price = _decimal_or_none(getattr(ib_order, "lmtPrice", None))
        stop_price = _decimal_or_none(getattr(ib_order, "auxPrice", None))
        if order_type not in (OrderType.LMT, OrderType.STP_LMT):
            limit_price = None
        if order_type not in (OrderType.STP, OrderType.STP_LMT):
            stop_price = None

        quantity = Decimal(str(getattr(ib_order, "totalQuantity", "0")))
        if quantity <= 0:
            raise IBShapeError(f"IB order has non-positive totalQuantity {quantity!r}")

        return Order(
            client_order_id=ClientOrderId(client_order_id),
            strategy_id=self.broker_strategy_id,
            instrument=instrument,
            side=side,
            quantity=quantity,
            order_type=order_type,
            time_in_force=time_in_force,
            limit_price=limit_price,
            stop_price=stop_price,
            parent_id=None,
            tags=tags,
            created_at=self._clock.now(),
        )

    def _instrument_from_contract(self, contract: ib_async.Contract) -> Instrument:
        """Synthesise an :class:`Instrument` from an IB ``Contract``.

        Best-effort: IB collapses EQUITY/ETF into "STK" so the reverse
        defaults to EQUITY. Multi-Yahoo-suffix re-addition is **not**
        attempted here — the strategy that placed the order owns the
        canonical Instrument; this synthesis is for IB-side bookkeeping
        only (positions / open-orders read-back). M5 reconciliation
        translates between the two views.
        """
        symbol = getattr(contract, "symbol", "") or ""
        if not symbol:
            raise IBShapeError("IB Contract has empty symbol")
        sec_type = getattr(contract, "secType", "") or ""
        exchange = getattr(contract, "exchange", "") or ""
        primary_exchange = getattr(contract, "primaryExchange", "") or ""
        # IB reports the *primary* exchange on positions / open orders;
        # if it's set, prefer it over the routing exchange.
        ib_exchange = primary_exchange or exchange
        currency = getattr(contract, "currency", "") or ""
        if not currency:
            raise IBShapeError("IB Contract has empty currency")
        asset_class = _SEC_TYPE_TO_ASSET_CLASS.get(sec_type, AssetClass.EQUITY)
        venue = _IB_EXCHANGE_TO_MIC.get(ib_exchange, ib_exchange)

        multiplier_str = getattr(contract, "multiplier", "") or ""
        multiplier = Decimal(multiplier_str) if multiplier_str else Decimal("1")

        # Tradability: IB retail is spot-only per ADR-040 + ADR-037; CFDs
        # are an IG-side thing.
        tradability: Tradability = "spot"

        return Instrument(
            symbol=symbol,
            venue=venue,
            currency=currency,
            asset_class=asset_class,
            multiplier=multiplier,
            tradability=tradability,
        )

    def _build_account_snapshot(self, *, taken_at: datetime) -> AccountSnapshot:
        """Compose an :class:`AccountSnapshot` from accumulated account values.

        Identifies the base currency from the "BASE" pseudo-currency
        rows (or falls back to the most-frequent currency in the cache).
        Aggregate fields (equity, buying_power, gross_exposure,
        margin_used) come from the BASE rows; per-currency cash from
        per-currency rows.
        """
        # Identify base currency: IB uses an explicit "BASE" pseudo-currency
        # in the account-value stream for aggregate values. The actual
        # base-currency code is reported via the AccountCode tag with no
        # currency, or via per-currency rows.
        base_currency = self._infer_base_currency()

        equity = self._account_value_decimal(
            (base_currency, _TAG_NET_LIQUIDATION),
            fallback_keys=[("BASE", _TAG_NET_LIQUIDATION)],
        )
        buying_power = self._account_value_decimal(
            (base_currency, _TAG_BUYING_POWER),
            fallback_keys=[("BASE", _TAG_BUYING_POWER)],
        )
        gross_exposure = self._account_value_decimal(
            (base_currency, _TAG_GROSS_POSITION),
            fallback_keys=[("BASE", _TAG_GROSS_POSITION)],
        )
        margin_used = self._account_value_decimal(
            (base_currency, _TAG_MAINT_MARGIN),
            fallback_keys=[("BASE", _TAG_MAINT_MARGIN)],
        )

        # cash_by_ccy: per-currency TotalCashBalance rows (excludes the
        # "BASE" aggregate row).
        cash_by_ccy: dict[str, Decimal] = {}
        for (ccy, tag), value in self._account_values.items():
            if tag == _TAG_TOTAL_CASH and ccy and ccy != "BASE":
                try:
                    cash_by_ccy[ccy] = Decimal(value)
                except (ValueError, ArithmeticError):
                    log.warning(
                        "IB account value %s.%s = %r is not a Decimal; skipping",
                        ccy,
                        tag,
                        value,
                    )

        # net_exposure: IB doesn't push a single "net exposure" tag, so we
        # derive it as gross_exposure for v1. Strategies using long/short
        # need the M4 widening to query per-position net properly.
        net_exposure = gross_exposure

        leverage = (gross_exposure / equity) if equity and equity > 0 else Decimal("0")

        return AccountSnapshot(
            equity=equity,
            cash_by_ccy=cash_by_ccy,
            buying_power=buying_power,
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            leverage=leverage,
            margin_used=margin_used,
            base_currency=base_currency,
            taken_at=taken_at,
        )

    def _infer_base_currency(self) -> str:
        """Identify the account's base currency from accumulated values.

        IB reports a "BASE" pseudo-currency for aggregate values; the
        actual currency code lives in per-currency rows. Heuristic:
        prefer the explicit ``AccountCurrency`` tag (rare); else pick
        the currency that appears in the most ``NetLiquidationByCurrency``
        rows that aren't "BASE" — this is the per-account base in
        practice.
        """
        # 1. Explicit AccountCurrency tag (set in some account configs).
        for (ccy, tag), value in self._account_values.items():
            if tag == "AccountCurrency" and value:
                return value

        # 2. The non-BASE currency with a NetLiquidation row. For a
        # single-currency account there's only one; for multi-currency the
        # account base is ambiguous and we pick the highest-equity row.
        best_ccy = ""
        best_equity = Decimal("-Infinity")
        for (ccy, tag), value in self._account_values.items():
            if tag != _TAG_NET_LIQUIDATION:
                continue
            if not ccy or ccy == "BASE":
                continue
            try:
                equity = Decimal(value)
            except (ValueError, ArithmeticError):
                continue
            if equity > best_equity:
                best_equity = equity
                best_ccy = ccy
        if best_ccy:
            return best_ccy

        # 3. Fallback: USD (most common IB account currency).
        return "USD"

    def _account_value_decimal(
        self,
        primary_key: tuple[str, str],
        *,
        fallback_keys: list[tuple[str, str]] | None = None,
    ) -> Decimal:
        """Read an account value as Decimal, with fallback keys.

        Used for the BASE-vs-base-currency duality. Returns ``Decimal("0")``
        if no key is present (an empty cache shouldn't reach here per
        :meth:`account_snapshot`'s upfront check, but defensively zero
        is safer than raising on a single missing tag).
        """
        candidates = [primary_key]
        if fallback_keys:
            candidates.extend(fallback_keys)
        for key in candidates:
            value = self._account_values.get(key)
            if value is None:
                continue
            try:
                return Decimal(value)
            except (ValueError, ArithmeticError):
                log.warning(
                    "IB account value %s = %r is not a Decimal; skipping",
                    key,
                    value,
                )
        return Decimal("0")


def _parse_order_side(action: str) -> OrderSide:
    if action == "BUY":
        return OrderSide.BUY
    if action == "SELL":
        return OrderSide.SELL
    raise IBShapeError(f"Unknown IB order action {action!r}")


# IB ``orderType`` is a string in TWS API. We map only the v1 subset; richer
# types are a future-strategy concern. Unknown types raise (load-bearing —
# we can't silently treat ``MIDPRICE`` as ``LMT``).
_IB_ORDER_TYPE_MAP: dict[str, OrderType] = {
    "MKT": OrderType.MKT,
    "LMT": OrderType.LMT,
    "MOC": OrderType.MOC,
    "LOC": OrderType.LOC,
    "STP": OrderType.STP,
    "STP LMT": OrderType.STP_LMT,
    "STP_LMT": OrderType.STP_LMT,
}


def _parse_order_type(order_type_str: str) -> OrderType:
    mapped = _IB_ORDER_TYPE_MAP.get(order_type_str)
    if mapped is None:
        raise IBShapeError(f"Unsupported IB orderType {order_type_str!r}")
    return mapped


_IB_TIF_MAP: dict[str, TimeInForce] = {
    "DAY": TimeInForce.DAY,
    "GTC": TimeInForce.GTC,
    "IOC": TimeInForce.IOC,
    "FOK": TimeInForce.FOK,
    "OPG": TimeInForce.OPG,
}


def _parse_time_in_force(tif_str: str) -> TimeInForce:
    mapped = _IB_TIF_MAP.get(tif_str)
    if mapped is None:
        raise IBShapeError(f"Unsupported IB tif {tif_str!r}")
    return mapped


# --- Internals: blive Order ↔ ib_async Order ---------------------------------


def _blive_to_ib_order(order: Order) -> ib_async.Order:
    """Map a broker-neutral :class:`Order` to ``ib_async.Order``.

    Supports ``MKT``, ``LMT``, ``STP``, ``STP_LMT`` (M2-IB.4a) and
    ``ADAPTIVE_MKT`` (M2-IB.6.2c — IBALGO Adaptive variant of MKT that
    bypasses IB's regulatory disruptive-orders price-cap on volatile /
    leveraged products; see warning 2161 in INV-14 v0.7). ``MOC`` /
    ``LOC`` / ``OPG`` are valid blive types per [DD-1 §1.1](../../../../docs/dd/domain_objects.md#11-enums)
    but raise here pending v1.1 — they require additional IB plumbing
    (``goodAfterTime``, ``tif="OPG"``, etc.).
    """
    action = order.side.value  # OrderSide.BUY → "BUY"; OrderSide.SELL → "SELL"
    qty = float(order.quantity)
    tif = order.time_in_force.value  # DAY, GTC, IOC, FOK, OPG

    ib_order: ib_async.Order
    if order.order_type == OrderType.MKT:
        ib_order = ib_async.MarketOrder(action=action, totalQuantity=qty)
    elif order.order_type == OrderType.ADAPTIVE_MKT:
        # IBALGO Adaptive: a smart agency order that IB does NOT apply the
        # disruptive-orders price-cap to (warning 2161 path), because the
        # algorithm itself manages execution price + timing within IB's
        # regulatory envelope. Validated at M2-IB.6.2c against QQL3 on
        # LSEETF where raw MKT was structurally cap-bound at the bid even
        # with a 60-second event-wait. ``adaptivePriority="Normal"`` is
        # IB's recommended default — alternative values are "Patient"
        # (slower but lower impact) and "Urgent" (faster but more market
        # impact). ``Normal`` is appropriate for the M2-IB.6 daily-rebalance
        # cadence; Phase-2 strategies with intra-day cadence can override
        # via a future Order.algo_priority field if needed.
        ib_order = ib_async.MarketOrder(action=action, totalQuantity=qty)
        ib_order.algoStrategy = "Adaptive"
        ib_order.algoParams = [ib_async.TagValue("adaptivePriority", "Normal")]
    elif order.order_type == OrderType.LMT:
        if order.limit_price is None:
            raise ValueError(f"LMT order {order.client_order_id} requires limit_price")
        ib_order = ib_async.LimitOrder(
            action=action,
            totalQuantity=qty,
            lmtPrice=float(order.limit_price),
        )
    elif order.order_type == OrderType.STP:
        if order.stop_price is None:
            raise ValueError(f"STP order {order.client_order_id} requires stop_price")
        ib_order = ib_async.StopOrder(
            action=action,
            totalQuantity=qty,
            stopPrice=float(order.stop_price),
        )
    elif order.order_type == OrderType.STP_LMT:
        if order.limit_price is None or order.stop_price is None:
            raise ValueError(
                f"STP_LMT order {order.client_order_id} requires both "
                f"limit_price and stop_price"
            )
        ib_order = ib_async.StopLimitOrder(
            action=action,
            totalQuantity=qty,
            lmtPrice=float(order.limit_price),
            stopPrice=float(order.stop_price),
        )
    else:
        raise NotImplementedError(
            f"IBBroker.submit does not support order_type={order.order_type.value} "
            f"at M2-IB.6.2c. Supported: MKT, ADAPTIVE_MKT, LMT, STP, STP_LMT. "
            f"MOC/LOC/OPG land at v1.1 if a strategy needs them."
        )

    ib_order.tif = tif
    return ib_order


def _cancel_reason_from_status(status: str, trade: ib_async.Trade) -> str:
    """Compute the [INV-13 §5](../../../../docs/inv/order_state_transitions.md#5-reason-taxonomy-for-cancel-and-reject)
    cancel reason from the IB status + trade context.

    "ApiCancelled" → ``"engine"`` (we initiated the cancel via cancelOrder).
    "Cancelled" → ``"venue_purge"`` if the trade has no prior cancel
    intent in its log; otherwise ``"engine"``. Defensive — IB sometimes
    fires "Cancelled" even when blive initiated.
    """
    if status == "ApiCancelled":
        return "engine"
    # IB "Cancelled" typically follows our cancelOrder request; treat as
    # engine-initiated unless we have evidence otherwise.
    return "engine"


def _last_error_log_entry(trade: ib_async.Trade) -> Any:
    """Return the most recent ``trade.log`` entry whose ``errorCode`` is
    non-zero, or ``None`` if the log is empty or contains only zero-code
    entries.

    Used by :meth:`IBBroker._on_order_status` to disambiguate CANCELED
    from REJECTED on IB ``status="Cancelled"``: a non-zero ``errorCode``
    in the trade log means the cancel was system-initiated due to a
    rejection (e.g., risk precautions, direct-routing block at error
    10311, dup orderId at 322). [INV-13 §5](../../../../docs/inv/order_state_transitions.md#5-reason-taxonomy-for-cancel-and-reject)
    distinguishes engine-initiated cancels from venue-side rejections;
    [INV-14](../../../../docs/inv/ib_error_codes.md) catalogues the codes.

    Defensive against IB's loose typing — ``getattr(..., 0) or 0`` handles
    missing attribute, ``None``, and 0 identically.
    """
    log_entries = getattr(trade, "log", None)
    if not log_entries:
        return None
    for entry in reversed(log_entries):
        error_code = getattr(entry, "errorCode", 0) or 0
        if error_code:
            return entry
    return None


def _rejected_reason_from_log_entry(entry: Any) -> str:
    """Build the [INV-13 §5](../../../../docs/inv/order_state_transitions.md#5-reason-taxonomy-for-cancel-and-reject)
    reason string from a ``TradeLogEntry`` with a non-zero ``errorCode``.

    Format: ``"ib:{errorCode} {message}"`` so consumers can grep by code
    for analytics ([INV-14](../../../../docs/inv/ib_error_codes.md))
    while keeping the human message visible. Empty message degrades to
    ``"ib:{errorCode}"``.
    """
    error_code = getattr(entry, "errorCode", 0) or 0
    message = getattr(entry, "message", "") or ""
    if message:
        return f"ib:{error_code} {message}"
    return f"ib:{error_code}"


def _rejected_reason_from_trade(trade: ib_async.Trade) -> str | None:
    """Extract the reject reason from an Inactive trade, or ``None`` if
    nothing useful is on the trade.

    IB *sometimes* pushes the reject reason via the ``log`` attribute
    (TradeLogEntry list) or ``orderStatus.whyHeld`` — but for some
    rejection paths (observed at M2-IB.6.2 with error 201 PRIIPs/KID)
    the reason text lives only on the global ``ib.errorEvent`` channel
    and never reaches ``trade.log`` / ``whyHeld``. Returning ``None``
    signals the caller to consult the broker's
    ``_error_by_order_id`` stash before falling back to a generic
    "rejected" placeholder. The [INV-13 §5](../../../../docs/inv/order_state_transitions.md#5-reason-taxonomy-for-cancel-and-reject)
    reason string is built by the caller after that lookup.
    """
    if trade.log:
        last = trade.log[-1]
        msg = getattr(last, "message", "")
        if msg:
            return msg
    why_held = getattr(trade.orderStatus, "whyHeld", "")
    if why_held:
        return why_held
    return None


def _decimal_or_none(value: Any) -> Decimal | None:
    """Parse an IB-side numeric to Decimal, treating 0 / 0.0 / None / ''
    as None (IB uses 0.0 as a "not set" sentinel for limit / stop fields
    on order types that don't carry that field).
    """
    if value is None or value == "":
        return None
    try:
        d = Decimal(str(value))
    except (ValueError, ArithmeticError):
        return None
    if d == 0:
        return None
    return d


__all__ = [
    "IBBroker",
    "IBShapeError",
]
