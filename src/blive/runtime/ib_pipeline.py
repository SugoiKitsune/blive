"""IB-mode end-to-end pipeline.

Sibling of :mod:`blive.runtime.paper_pipeline` for the M2-IB.5 strategy
run: the rebalance-loop machinery is the same shape (factor → signal →
portfolio → sizer → risk → broker), but the broker is :class:`blive.adapters.ib.broker.IBBroker`
talking to IB Paper, and the data feed is :class:`blive.adapters.paper.market_data.PaperMarketData`
backed by an EODHD parquet (per [ADR-017](../../../docs/decisions/DECISIONS.md#adr-017--live-data-hybrid-eodhd--ib-streaming-per-instrument-routing)
hybrid routing — data from EODHD, execution on IB).

Decoupled from the signal source: the caller passes a pre-computed
``position_series`` (a pandas Series indexed by bar close timestamps,
values in ``{0, 1}`` for the M2-IB.5 single-leg long/flat case). The
TKAN stub for end-to-end paper testing (M2-IB.5 prereq #3) and any
future btest interpreter (per [OQ-030](../../../docs/decisions/OPEN_QUESTIONS.md#oq-030--which-btest-interpreter-does-blive-call-for-timingportfolio-and-other-non-longshort-archetypes)
/ [ADR-030](../../../docs/decisions/DECISIONS.md#adr-030--per-archetype-btest-interpreter-dispatch-amends-adr-010))
both produce a ``position_series`` matching this shape.

Compared to ``run_paper_pipeline``:

- **Broker is injected** (caller constructs and connects). The pipeline
  uses :class:`blive.adapters.ib.broker.IBBroker` directly only for the
  IB-specific event drain (``IBBroker._events`` queue access matches the
  pattern from ``scripts/probe_ib_submit.py``); switching to a different
  ``BrokerPort`` impl is a small refactor when the third-broker case
  arrives.
- **No price_lookup injection** — the broker fills at the venue's real
  market, so the pipeline doesn't simulate fills. The ``Fill.price`` and
  ``Fill.commission`` from the broker drive the local cash ledger.
- **No btest integration in this module.** The position_series is the
  signal contract.
- **Order type defaults to LMT** at the bar's close price ± a small
  aggressive offset — for paper testing, this exercises the full FSM
  (SUBMITTED → ACCEPTED → CANCELED if the order doesn't fill, or →
  FILLED if it crosses). MARKET orders are also supported; choose via
  ``order_type``.

Out of scope (M5+ work): real-time live mode (waiting for the next
session close); reconciliation drift; intraday tick handling;
multi-instrument rebalances.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Mapping, cast
from uuid import uuid4

import pandas as pd

from blive.adapters.alert.log import LogAlert
from blive.adapters.eodhd.conventions import eodhd_to_ib_price
from blive.adapters.ib.broker import IBBroker
from blive.adapters.paper.market_data import PaperMarketData
from blive.domain.events import OrderEvent
from blive.domain.positions import apply_fill
from blive.domain.types import (
    TERMINAL_ORDER_STATES,
    Bar,
    ClientOrderId,
    Instrument,
    Order,
    OrderEventKind,
    OrderSide,
    OrderState,
    OrderType,
    Position,
    TimeInForce,
)
from blive.risk import (
    BREACH_TOPIC,
    KillSwitch,
    RiskBreach,
    RiskEngine,
    RiskEngineConfig,
    RiskInputs,
)
from blive.sizing import SizerInput, size_orders
from blive.strategy.loader import LiveStrategy

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class IBEquityPoint:
    """One row of the equity curve at a rebalance close."""

    time_utc: datetime
    cash: Decimal
    position_qty: Decimal
    mark_price: Decimal
    equity: Decimal


@dataclass
class IBRunResult:
    """Outcome of an IB-paper run."""

    equity_curve: list[IBEquityPoint] = field(default_factory=list)
    breaches: list[RiskBreach] = field(default_factory=list)
    fills_count: int = 0
    submitted_count: int = 0
    canceled_count: int = 0
    rejected_count: int = 0
    final_equity: Decimal = Decimal("0")


@dataclass(frozen=True, slots=True)
class IBMultiEquityPoint:
    """One row of the multi-instrument equity curve at a rebalance close.

    Per [ADR-044](../../../docs/decisions/DECISIONS.md#adr-044--multi-instrument-pipeline-support-companion-to-adr-043):
    ``positions`` and ``mark_prices`` are per-instrument dicts keyed by
    the symbol (string) so equity attribution stays clear when the
    strategy holds positions in multiple instruments simultaneously.
    """

    time_utc: datetime
    cash: Decimal
    positions: dict[str, Decimal]  # symbol → quantity
    mark_prices: dict[str, Decimal]  # symbol → close at this rebalance
    equity: Decimal


@dataclass
class IBMultiRunResult:
    """Outcome of a multi-instrument IB-paper run.

    Companion to :class:`IBRunResult` for the single-instrument pipeline.
    Per ADR-044, the multi-instrument flow has one ``IBBroker.submit``
    call per per-instrument target-weight delta per rebalance; FSM
    counters are aggregate across all instruments.

    M3.2 (per [TASK_REGISTRY M3.2](../../../TASK_REGISTRY.md)) widened the
    result with the per-symbol + FSM-stage counters the empirical-window
    results sink needs:

    - ``submitted_by_symbol`` is the per-instrument *placed* denominator
      for the per-instrument fill-rate (``fills_by_symbol`` is the
      numerator).
    - ``accepted_count`` lets the sink report the FSM-trace coverage
      ratio (SUBMITTED → ACCEPTED → FILLED / CANCELED / REJECTED)
      exactly rather than inferring acceptance from terminal counts.
    - ``observed_error_codes`` is the broker's order-related error/warning
      histogram for this run (see
      :attr:`blive.adapters.ib.broker.IBBroker.observed_error_codes`);
      :attr:`cap_binding_2161_count` reads warning 2161 (PMA price-cap)
      out of it — the OQ-031 signal per INV-14 v0.9.

    All new fields are additive and default-empty; the wire-validated FSM
    counters (``fills_count`` / ``submitted_count`` / ``canceled_count`` /
    ``rejected_count``) keep their meaning unchanged.
    """

    equity_curve: list[IBMultiEquityPoint] = field(default_factory=list)
    breaches: list[RiskBreach] = field(default_factory=list)
    fills_count: int = 0
    submitted_count: int = 0
    accepted_count: int = 0
    canceled_count: int = 0
    rejected_count: int = 0
    fills_by_symbol: dict[str, int] = field(default_factory=dict)
    submitted_by_symbol: dict[str, int] = field(default_factory=dict)
    observed_error_codes: dict[int, int] = field(default_factory=dict)
    final_equity: Decimal = Decimal("0")

    @property
    def cap_binding_2161_count(self) -> int:
        """IB warning-2161 (PMA disruptive-orders price-cap) occurrences
        observed during the run — the OQ-031 fill-rate signal per
        [INV-14 v0.9](../../../docs/inv/ib_error_codes.md). Read out of
        :attr:`observed_error_codes`; ``0`` when none fired.
        """
        return self.observed_error_codes.get(2161, 0)


# --- Public entry point ------------------------------------------------------


async def run_ib_pipeline(
    *,
    live_strategy: LiveStrategy,
    broker: IBBroker,
    market_data: PaperMarketData,
    instrument: Instrument,
    position_series: pd.Series,
    starting_cash: Decimal = Decimal("1000000"),
    base_currency: str = "EUR",
    target_leverage: Decimal = Decimal("1"),
    order_type: OrderType = OrderType.LMT,
    limit_price_offset_bps: Decimal = Decimal("50"),
    event_wait_seconds: float = 10.0,
    kill_switch: KillSwitch | None = None,
) -> IBRunResult:
    """Run the M2-IB.5 IB-paper pipeline end-to-end against IB Paper.

    The caller must:

    1. Construct an :class:`IBBroker` and call :meth:`IBBroker.connect`.
    2. Provide a :class:`PaperMarketData` whose fixture covers
       ``position_series.index``.
    3. Provide ``position_series`` aligned with the market_data bars'
       close timestamps; values in ``{0, 1}``.

    The pipeline:

    1. Walks the historical bars in ``market_data.bars(instrument)``.
    2. For each bar whose timestamp is in ``position_series.index``,
       computes ``target_weight = position * target_leverage``.
    3. Sizes via :func:`blive.sizing.size_orders`, runs each candidate
       through the M1 :class:`blive.risk.RiskEngine` subset (RC-08 /
       RC-09 / RC-12 / RC-13), submits approved orders to IB.
    4. Drains the broker's event queue until the order reaches a
       terminal state (FILLED / CANCELED / REJECTED / EXPIRED), then
       cancels any non-terminal orders before moving to the next bar.
    5. Updates a local cash + position view from observed fills (the
       broker remains authoritative on its own ``account_snapshot``;
       this local view is the per-strategy attribution view).

    Returns an :class:`IBRunResult` summarising the run; the broker
    stays connected on return (caller manages disconnect).
    """
    if not broker.is_connected:
        raise RuntimeError("run_ib_pipeline expects an already-connected IBBroker")

    bars = market_data.bars(instrument)
    if not bars:
        raise ValueError(f"no bars in fixture for {instrument}")

    risk_engine = RiskEngine(
        config=_risk_config_from_live(live_strategy),
        kill_switch=kill_switch if kill_switch is not None else KillSwitch(),
        strategy_id=live_strategy.live_config.strategy_id,
    )
    alert = LogAlert()

    # Drain any startup events (ConnectionStatus, initial AccountUpdate)
    # off the broker's queue before the loop begins.
    await _drain_startup_events(broker)

    instrument_key = instrument.symbol
    cash = starting_cash
    positions: dict[str, Position] = {}
    result = IBRunResult()

    for bar in bars:
        t = bar.close_time_utc
        ts_key = pd.Timestamp(t)
        if ts_key not in position_series.index:
            continue

        position_int = int(position_series.loc[ts_key])
        target_weight = Decimal(position_int) * target_leverage

        def _resolve_instrument(_key: str, _i: Instrument = instrument) -> Instrument:
            return _i

        def _price_lookup(_inst: Instrument, _p: Decimal = bar.close) -> Decimal:
            return _p

        sizer_in = SizerInput(
            target_weights={instrument_key: target_weight},
            equity=_compute_equity(cash, positions, bar.close),
            nav_slice=live_strategy.live_config.nav_slice,
            current_positions=positions,
            instrument_resolver=_resolve_instrument,
            price_lookup=_price_lookup,
            strategy_id=live_strategy.live_config.strategy_id,
            now=t,
        )
        candidate_orders = size_orders(sizer_in)

        for desired in candidate_orders:
            risk_inputs = RiskInputs(
                last_bar=bar,
                is_market_open=True,  # paper-test runs against historical bars
                artefact_paths=dict(live_strategy.live_config.artefact_paths.paths),
            )
            approved, breaches = risk_engine.approve(desired, inputs=risk_inputs, now=t)
            if breaches:
                result.breaches.extend(breaches)
                for b in breaches:
                    await alert.send(
                        b.alert_severity(),
                        f"{BREACH_TOPIC}/{b.check.value}",
                        b.detail,
                    )
            if approved is None:
                continue

            # Promote to LMT at the bar's close (± offset) so IB Paper has
            # a price to work with; MARKET orders for a daily-frequency
            # paper test would fill at unrelated current-market prices.
            order_for_ib = _ib_order_from_desired(
                desired=approved,
                bar=bar,
                order_type=order_type,
                limit_price_offset_bps=limit_price_offset_bps,
            )

            await broker.submit(order_for_ib)
            result.submitted_count += 1
            # Single-instrument IBRunResult does not track per-stage FSM
            # coverage; discard reached_accepted (the multi pipeline uses it).
            terminal_state, fill_event, _ = await _drain_order_lifecycle(
                broker=broker,
                target_id=ClientOrderId(order_for_ib.client_order_id),
                timeout_s=event_wait_seconds,
            )

            if (
                terminal_state == OrderState.FILLED
                and fill_event is not None
                and fill_event.fill is not None
            ):
                fill = fill_event.fill
                prior = positions.get(instrument_key)
                positions[instrument_key] = apply_fill(
                    prior,
                    fill,
                    strategy_id=live_strategy.live_config.strategy_id,
                    now=t,
                )
                signed = fill.quantity if fill.side == OrderSide.BUY else -fill.quantity
                cash -= signed * fill.price + fill.commission
                result.fills_count += 1
            elif terminal_state == OrderState.CANCELED:
                result.canceled_count += 1
            elif terminal_state == OrderState.REJECTED:
                result.rejected_count += 1
            else:
                # Non-terminal after timeout — engine-cancel before moving on.
                try:
                    await broker.cancel(ClientOrderId(order_for_ib.client_order_id))
                except KeyError:
                    pass
                # Drain any final event after the cancel; ignore outcome.
                await _drain_order_lifecycle(
                    broker=broker,
                    target_id=ClientOrderId(order_for_ib.client_order_id),
                    timeout_s=event_wait_seconds,
                )
                result.canceled_count += 1

        equity = _compute_equity(cash, positions, bar.close)
        qty = positions[instrument_key].quantity if instrument_key in positions else Decimal("0")
        result.equity_curve.append(
            IBEquityPoint(
                time_utc=t,
                cash=cash,
                position_qty=qty,
                mark_price=bar.close,
                equity=equity,
            )
        )

    result.final_equity = result.equity_curve[-1].equity if result.equity_curve else starting_cash
    return result


# --- Public entry point: multi-instrument (M2-IB.6 per ADR-044) -------------


async def run_ib_multi_pipeline(
    *,
    live_strategy: LiveStrategy,
    broker: IBBroker,
    market_data: PaperMarketData,
    instruments: list[Instrument],
    target_weights_series: pd.DataFrame,
    starting_cash: Decimal = Decimal("1000000"),
    base_currency: str = "USD",
    order_type: OrderType = OrderType.MKT,
    order_type_by_symbol: Mapping[str, OrderType] | None = None,
    limit_price_offset_bps: Decimal = Decimal("50"),
    event_wait_seconds: float = 10.0,
    kill_switch: KillSwitch | None = None,
) -> IBMultiRunResult:
    """Multi-instrument IB-paper pipeline per [ADR-044](../../../docs/decisions/DECISIONS.md#adr-044--multi-instrument-pipeline-support-companion-to-adr-043).

    Sibling of :func:`run_ib_pipeline`; same FSM-drain shape, but extends
    from one instrument to N. The Sizer (:func:`blive.sizing.size_orders`)
    is multi-instrument-capable already; this function is the per-bar
    orchestration wrapper.

    Caller contract:

    1. Construct an :class:`IBBroker` and call :meth:`IBBroker.connect`.
    2. Provide a :class:`PaperMarketData` whose fixtures cover all
       ``instruments``; the first instrument's bar timeline is the
       canonical rebalance schedule (other instruments get their bars
       looked up at the same close timestamps via
       :meth:`PaperMarketData.latest`).
    3. Provide ``target_weights_series`` indexed by bar
       ``close_time_utc``, columns by instrument symbol (e.g. ``TQQQ`` /
       ``TMF`` / ``IEF``), values ``float`` weights summing to ≤ 1.0
       per row.

    Per-rebalance flow:

    1. Read the canonical bar from ``instruments[0]``.
    2. Look up the weights row at this bar's ``close_time_utc``; skip if
       absent.
    3. Build per-instrument current-position dict + per-instrument
       price-lookup, call :func:`size_orders` once with the full
       ``target_weights: dict[str, float]``.
    4. Each Order returned goes through the RiskEngine, then IBBroker;
       per-order FSM drain awaits terminal state.
    5. Accumulate fills in per-instrument positions / cash; mark
       multi-instrument equity at the rebalance close.

    Returns the broker still connected (caller manages disconnect).
    """
    if not broker.is_connected:
        raise RuntimeError("run_ib_multi_pipeline expects an already-connected IBBroker")
    if not instruments:
        raise ValueError("instruments list must be non-empty")
    if target_weights_series.empty:
        raise ValueError("target_weights_series must not be empty")

    # Per-symbol Instrument lookup; the canonical timeline is instruments[0].
    inst_by_symbol: dict[str, Instrument] = {i.symbol: i for i in instruments}
    canonical_inst = instruments[0]
    canonical_bars = market_data.bars(canonical_inst)
    if not canonical_bars:
        raise ValueError(f"no bars in fixture for canonical instrument {canonical_inst}")

    risk_engine = RiskEngine(
        config=_risk_config_from_live(live_strategy),
        kill_switch=kill_switch if kill_switch is not None else KillSwitch(),
        strategy_id=live_strategy.live_config.strategy_id,
    )
    alert = LogAlert()
    await _drain_startup_events(broker)

    cash = starting_cash
    positions: dict[str, Position] = {}  # keyed by symbol
    result = IBMultiRunResult()
    # M3.2: baseline the broker's order-error histogram so end-of-run we
    # record only the codes *this* run produced. Defensive against broker
    # reuse — the M3.2 driver constructs a fresh broker per run, so the
    # baseline is normally empty.
    error_codes_baseline = broker.observed_error_codes

    for canonical_bar in canonical_bars:
        t = canonical_bar.close_time_utc
        ts_key = pd.Timestamp(t)
        if ts_key not in target_weights_series.index:
            continue

        # Per-instrument bar lookup: use the canonical bar timestamp; for
        # other instruments, look up the latest bar at-or-before this
        # timestamp via PaperMarketData's helper. US calendars are
        # uniform so this typically matches exactly; defensive against
        # split-day fixtures.
        bars_by_symbol: dict[str, Bar] = {canonical_inst.symbol: canonical_bar}
        for inst in instruments[1:]:
            other_bar = market_data.latest(inst, on_or_before=t)
            if other_bar is None:
                # Skip this rebalance entirely — incomplete cross-instrument data.
                continue
            bars_by_symbol[inst.symbol] = other_bar
        if len(bars_by_symbol) != len(instruments):
            continue

        # Read the per-symbol target weights for this rebalance. Sizer
        # expects Decimal values; cast via str → Decimal to avoid float-
        # repr artefacts (Decimal(0.5) != Decimal("0.5") strictly).
        weights_row = target_weights_series.loc[ts_key]
        target_weights: dict[str, Decimal] = {}
        for inst in instruments:
            if inst.symbol in weights_row.index:
                # cast: pandas-stubs types Series element access as Any | Series,
                # but a scalar-label lookup is a scalar at runtime (mypy 2.x, ADR-053).
                target_weights[inst.symbol] = Decimal(
                    str(float(cast(float, weights_row[inst.symbol])))
                )
            else:
                target_weights[inst.symbol] = Decimal("0")

        # Sizer inputs: per-instrument resolver + price lookup.
        def _resolve_instrument(
            symbol: str, _by: dict[str, Instrument] = inst_by_symbol
        ) -> Instrument:
            return _by[symbol]

        # Per ADR-050 (M3.1 narrow-scope sizing fix), EODHD prices are
        # converted to their IB-equivalent via the per-instrument
        # convention catalogue at sizing time. The PaperMarketData
        # parquet stays vendor-pristine; conversion is at the pipeline
        # boundary so the Sizer continues to receive a single Decimal
        # price per Instrument (preserves ADR-027 Sizer purity).
        # Symbols absent from the catalogue use IDENTITY (no conversion).
        def _price_lookup(
            inst: Instrument,
            _bars: dict[str, Bar] = bars_by_symbol,
        ) -> Decimal:
            return eodhd_to_ib_price(
                ib_symbol=inst.symbol,
                eodhd_price=_bars[inst.symbol].close,
            )

        # Compute mark-to-market equity for the Sizer's NAV-slice math.
        # Same per-symbol conversion applies — equity must be in
        # IB-equivalent terms so the NAV slice represents real exposure.
        mark_prices: dict[str, Decimal] = {
            sym: eodhd_to_ib_price(ib_symbol=sym, eodhd_price=bar.close)
            for sym, bar in bars_by_symbol.items()
        }
        equity = _compute_equity_multi(cash, positions, mark_prices)

        sizer_in = SizerInput(
            target_weights=target_weights,
            equity=equity,
            nav_slice=live_strategy.live_config.nav_slice,
            current_positions=positions,
            instrument_resolver=_resolve_instrument,
            price_lookup=_price_lookup,
            strategy_id=live_strategy.live_config.strategy_id,
            now=t,
        )
        candidate_orders = size_orders(sizer_in)

        for desired in candidate_orders:
            # IB-equivalent reference for RC-10 (price sanity, ADR-050) —
            # mark_prices was already converted via the EODHD convention
            # catalogue; reuse rather than re-convert.
            ref_price = mark_prices.get(desired.instrument.symbol)
            risk_inputs = RiskInputs(
                last_bar=bars_by_symbol[desired.instrument.symbol],
                is_market_open=True,  # paper-test runs against historical bars
                artefact_paths=dict(live_strategy.live_config.artefact_paths.paths),
                reference_price=ref_price,
            )
            approved, breaches = risk_engine.approve(desired, inputs=risk_inputs, now=t)
            if breaches:
                result.breaches.extend(breaches)
                for b in breaches:
                    await alert.send(
                        b.alert_severity(),
                        f"{BREACH_TOPIC}/{b.check.value}",
                        b.detail,
                    )
            if approved is None:
                continue

            # Per-symbol order_type override per [INV-14 v0.7](../../../docs/inv/ib_error_codes.md)
            # warning 2161: leveraged-leg orders (e.g. QQL3 on LSEETF) hit
            # IB's regulatory disruptive-orders price-cap on raw MKT, so
            # the operator can opt them in to ADAPTIVE_MKT (IBALGO Adaptive)
            # via ``order_type_by_symbol``. Symbols absent from the map
            # fall through to the global ``order_type`` argument.
            effective_order_type = (
                order_type_by_symbol.get(approved.instrument.symbol, order_type)
                if order_type_by_symbol is not None
                else order_type
            )
            order_for_ib = _ib_order_from_desired(
                desired=approved,
                bar=bars_by_symbol[approved.instrument.symbol],
                order_type=effective_order_type,
                limit_price_offset_bps=limit_price_offset_bps,
            )

            await broker.submit(order_for_ib)
            result.submitted_count += 1
            # M3.2: per-instrument *placed* count (fill-rate denominator).
            submit_sym = approved.instrument.symbol
            result.submitted_by_symbol[submit_sym] = (
                result.submitted_by_symbol.get(submit_sym, 0) + 1
            )
            terminal_state, fill_event, reached_accepted = await _drain_order_lifecycle(
                broker=broker,
                target_id=ClientOrderId(order_for_ib.client_order_id),
                timeout_s=event_wait_seconds,
            )
            # M3.2 FSM-trace coverage: count acceptance once per submitted
            # order from the primary drain (engine-cancel re-drains below
            # but must not double-count).
            if reached_accepted:
                result.accepted_count += 1

            if (
                terminal_state == OrderState.FILLED
                and fill_event is not None
                and fill_event.fill is not None
            ):
                fill = fill_event.fill
                sym = fill.instrument.symbol
                prior = positions.get(sym)
                positions[sym] = apply_fill(
                    prior,
                    fill,
                    strategy_id=live_strategy.live_config.strategy_id,
                    now=t,
                )
                signed = fill.quantity if fill.side == OrderSide.BUY else -fill.quantity
                cash -= signed * fill.price + fill.commission
                result.fills_count += 1
                result.fills_by_symbol[sym] = result.fills_by_symbol.get(sym, 0) + 1
            elif terminal_state == OrderState.CANCELED:
                result.canceled_count += 1
            elif terminal_state == OrderState.REJECTED:
                result.rejected_count += 1
            else:
                # Non-terminal after timeout — engine-cancel before next order.
                try:
                    await broker.cancel(ClientOrderId(order_for_ib.client_order_id))
                except KeyError:
                    pass
                await _drain_order_lifecycle(
                    broker=broker,
                    target_id=ClientOrderId(order_for_ib.client_order_id),
                    timeout_s=event_wait_seconds,
                )
                result.canceled_count += 1

        # Mark multi-instrument equity at rebalance close.
        post_equity = _compute_equity_multi(cash, positions, mark_prices)
        snapshot_positions: dict[str, Decimal] = {
            sym: pos.quantity for sym, pos in positions.items()
        }
        result.equity_curve.append(
            IBMultiEquityPoint(
                time_utc=t,
                cash=cash,
                positions=snapshot_positions,
                mark_prices=dict(mark_prices),
                equity=post_equity,
            )
        )

    # M3.2: record this run's order-related IB error/warning histogram
    # (delta vs the entry baseline). ``cap_binding_2161_count`` reads
    # warning 2161 out of it — the OQ-031 cap-binding signal (INV-14 v0.9).
    end_codes = broker.observed_error_codes
    result.observed_error_codes = {
        code: count - error_codes_baseline.get(code, 0)
        for code, count in end_codes.items()
        if count - error_codes_baseline.get(code, 0) > 0
    }
    result.final_equity = result.equity_curve[-1].equity if result.equity_curve else starting_cash
    return result


# --- Helpers -----------------------------------------------------------------


def _compute_equity_multi(
    cash: Decimal,
    positions: dict[str, Position],
    mark_prices: dict[str, Decimal],
) -> Decimal:
    """Multi-instrument mark-to-market: cash + Σ (qty × mark_price) per
    held position. Uses the symbol-keyed positions dict from the
    multi-instrument pipeline; missing mark_prices for a held symbol
    contributes zero (defensive — the canonical-timeline contract
    guarantees a price for every instrument the pipeline tracks).
    """
    notional = Decimal("0")
    for sym, pos in positions.items():
        price = mark_prices.get(sym)
        if price is not None:
            notional += pos.quantity * price
    return cash + notional


def _ib_order_from_desired(
    *,
    desired: Order,
    bar: Bar,
    order_type: OrderType,
    limit_price_offset_bps: Decimal,
) -> Order:
    """Build the order to send to IB.

    For MARKET, return ``desired`` with ``order_type=MKT`` and no price.
    For LIMIT, set the limit at the IB-equivalent bar close ± an
    aggressive offset (BUY: ref * (1 + bps/10000); SELL: ref * (1 -
    bps/10000)) so crossing orders are likely to fill in normal venue
    conditions while away-of-market ones exercise the SUBMITTED →
    ACCEPTED → CANCELED path on the engine's bar-end cancel.

    The reference is the EODHD bar close converted via
    :func:`blive.adapters.eodhd.conventions.eodhd_to_ib_price` per
    [ADR-050](../../../../docs/decisions/DECISIONS.md#adr-050--eodhd-vs-ib-unit-of-quote-conversion-at-sizing-time-hybrid-b-now--a-later-free-md-only) —
    without the conversion the QQL3 LMT lands at ~10× IB's allowed
    range and trips IB error 110 ("price not in allowed range") before
    warning 2161 (PMA cap) fires.
    """
    base = desired
    if order_type in (OrderType.MKT, OrderType.ADAPTIVE_MKT):
        return Order(
            client_order_id=ClientOrderId(uuid4()),
            strategy_id=base.strategy_id,
            instrument=base.instrument,
            side=base.side,
            quantity=base.quantity,
            order_type=order_type,
            time_in_force=base.time_in_force,
            limit_price=None,
            stop_price=None,
            parent_id=None,
            tags={**base.tags, "pipeline": "m2-ib.5"},
            created_at=base.created_at,
        )
    if order_type == OrderType.LMT:
        scale = limit_price_offset_bps / Decimal("10000")
        ib_reference = eodhd_to_ib_price(
            ib_symbol=base.instrument.symbol,
            eodhd_price=bar.close,
        )
        if base.side == OrderSide.BUY:
            limit_price = ib_reference * (Decimal("1") + scale)
        else:
            limit_price = ib_reference * (Decimal("1") - scale)
        # No tick-grid rounding here (ADR-051): the pipeline emits the
        # economically-intended limit; IBBroker.submit snaps it to the
        # contract's legal price grid at the wire boundary. (Pre-ADR-051
        # this quantized to 0.01, which tripped IB error 110 on QQL3's
        # 0.10 tick.)
        return Order(
            client_order_id=ClientOrderId(uuid4()),
            strategy_id=base.strategy_id,
            instrument=base.instrument,
            side=base.side,
            quantity=base.quantity,
            order_type=OrderType.LMT,
            time_in_force=TimeInForce.DAY,
            limit_price=limit_price,
            stop_price=None,
            parent_id=None,
            tags={**base.tags, "pipeline": "m2-ib.5"},
            created_at=base.created_at,
        )
    raise ValueError(
        f"run_ib_pipeline supports MKT / ADAPTIVE_MKT / LMT order_type only; got {order_type!r}"
    )


async def _drain_startup_events(broker: IBBroker) -> None:
    """Pull any ConnectionStatus / AccountUpdate sitting in the queue at
    pipeline entry. We don't want them to confuse per-order drain loops."""
    queue = broker._events  # noqa: SLF001 — pipeline-internal access
    drained = 0
    while not queue.empty():
        await queue.get()
        drained += 1
    if drained:
        log.debug("drained %d startup event(s) from broker queue", drained)


async def _drain_order_lifecycle(
    *,
    broker: IBBroker,
    target_id: ClientOrderId,
    timeout_s: float,
    settle_on_accepted: bool = False,
    accepted_grace_s: float = 1.0,
) -> tuple[OrderState, OrderEvent | None, bool]:
    """Pull events from the broker until ``target_id`` reaches a terminal state.

    Returns ``(final_state, fill_event, reached_accepted)``:

    - ``final_state`` — the terminal state, or the latest non-terminal
      state seen on timeout (the caller decides whether to cancel).
    - ``fill_event`` — the (optional) fill-bearing event that decided it.
    - ``reached_accepted`` — whether the order was ever observed at
      ACCEPTED or beyond (PARTIALLY_FILLED / FILLED). Lets the caller
      report FSM-trace coverage (M3.2): an order that times out in
      SUBMITTED never reached ACCEPTED, whereas one that reached ACCEPTED
      and then engine-cancelled did. REJECTED orders that skip ACCEPTED
      keep this ``False``.

    ``settle_on_accepted``: a LOO/DAY order queued for the open is acknowledged
    (SUBMITTED/ACCEPTED) and then simply works until the auction — a terminal
    state will NOT arrive within the submit window, so waiting the full
    ``timeout_s`` per order is pure idle time. When set, once the order is
    confirmed working we wait only ``accepted_grace_s`` more (to catch a
    trailing reject) and return the working state instead of idling out.

    Reads :attr:`IBBroker._events` directly to avoid the async-generator
    cancellation hazard documented in ``scripts/probe_ib_submit.py``.
    """
    queue = broker._events  # noqa: SLF001 — pipeline-internal access
    fill_event: OrderEvent | None = None
    state = OrderState.SUBMIT_PENDING
    reached_accepted = False
    deadline = asyncio.get_event_loop().time() + timeout_s

    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            return state, fill_event, reached_accepted
        try:
            event = await asyncio.wait_for(queue.get(), timeout=remaining)
        except asyncio.TimeoutError:
            return state, fill_event, reached_accepted
        if not isinstance(event, OrderEvent):
            continue
        if event.client_order_id != target_id:
            continue
        if event.kind == OrderEventKind.SUBMITTED:
            state = OrderState.SUBMITTED
        elif event.kind == OrderEventKind.ACCEPTED:
            state = OrderState.ACCEPTED
            reached_accepted = True
        elif event.kind == OrderEventKind.PARTIAL_FILL:
            state = OrderState.PARTIALLY_FILLED
            reached_accepted = True
            fill_event = event
        elif event.kind == OrderEventKind.FILLED:
            state = OrderState.FILLED
            reached_accepted = True
            fill_event = event
            break
        elif event.kind == OrderEventKind.CANCELED:
            state = OrderState.CANCELED
            break
        elif event.kind == OrderEventKind.REJECTED:
            state = OrderState.REJECTED
            break
        elif event.kind == OrderEventKind.EXPIRED:
            state = OrderState.EXPIRED
            break
        if settle_on_accepted and state in (OrderState.SUBMITTED, OrderState.ACCEPTED):
            # Order confirmed working (won't reach terminal until the auction/session) — wait only a
            # short grace for a trailing reject, then return the working state instead of idling out.
            deadline = min(deadline, asyncio.get_event_loop().time() + accepted_grace_s)

    assert state in TERMINAL_ORDER_STATES
    return state, fill_event, reached_accepted


def _risk_config_from_live(live: LiveStrategy) -> RiskEngineConfig:
    """Translate ``LiveStrategyConfig.risk_overrides`` into ``RiskEngineConfig``.

    Daily-frequency Phase 1 → ``is_intraday=False``. M5+ widening adds
    intraday awareness when the engine grows real-time clock support.
    """
    overrides = live.live_config.risk_overrides
    return RiskEngineConfig(
        max_data_staleness_intraday_sec=overrides.max_data_staleness_intraday_sec,
        max_data_staleness_daily_sec=overrides.max_data_staleness_daily_sec,
        outside_rth_allowed=overrides.outside_rth_allowed,
        max_model_artefact_age_days=overrides.max_model_artefact_age_days,
        model_artefact_warning_age_days=overrides.model_artefact_warning_age_days,
        is_intraday=False,
    )


def _compute_equity(
    cash: Decimal,
    positions: dict[str, Position],
    mark_price: Decimal,
) -> Decimal:
    notional = sum(
        (p.quantity * mark_price for p in positions.values()),
        start=Decimal("0"),
    )
    return cash + notional


__all__ = [
    "IBEquityPoint",
    "IBMultiEquityPoint",
    "IBMultiRunResult",
    "IBRunResult",
    "run_ib_multi_pipeline",
    "run_ib_pipeline",
]
