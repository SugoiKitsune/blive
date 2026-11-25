"""IB-mode pipeline tests.

Covers the M2-IB.5 prereq #2 deliverable (broker-agnostic pipeline at
``src/blive/runtime/ib_pipeline.py``). The wire-level validation of the
underlying IBBroker happy + REJECTED-disambiguation paths is in
``test_broker.py`` + the ``probe_ib_submit.py`` wire probe; this file
tests the pipeline orchestration above the broker.

Mocking strategy: a small ``_FakeIBBroker`` class implements the surface
``run_ib_pipeline`` consumes (``is_connected``, ``submit``, ``cancel``,
``_events`` queue). The fake's submit() enqueues a configurable event
sequence so we can drive happy / cancel / reject paths without touching
real IB.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable
from uuid import uuid4

import pandas as pd
import pytest

from blive.adapters.paper.market_data import PaperMarketData
from blive.domain.events import OrderEvent
from blive.domain.ports import BrokerEvent
from blive.domain.types import (
    AssetClass,
    ClientOrderId,
    Fill,
    Instrument,
    Order,
    OrderEventKind,
    OrderSide,
)
from blive.risk import KillSwitch
from blive.runtime.ib_pipeline import (
    IBMultiRunResult,
    IBRunResult,
    run_ib_multi_pipeline,
    run_ib_pipeline,
)
from blive.strategy.config import (
    ArtefactPaths,
    LiveOverrides,
    LiveStrategyConfig,
    RiskOverrides,
)
from blive.strategy.loader import LiveStrategy

# --- Fake IBBroker -----------------------------------------------------------


@dataclass
class _FakeIBBroker:
    """Minimal fake matching the IBBroker surface that run_ib_pipeline uses."""

    is_connected: bool = True
    submitted_orders: list[Order] = None  # type: ignore[assignment]
    canceled_ids: list[ClientOrderId] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self._events: asyncio.Queue[BrokerEvent] = asyncio.Queue()
        self.submitted_orders = []
        self.canceled_ids = []
        self._on_submit: Callable[[Order], list[OrderEvent]] = self._default_on_submit
        self._on_cancel: Callable[[ClientOrderId], list[OrderEvent]] = self._default_on_cancel
        # M3.2: mirrors IBBroker.observed_error_codes. Tests mutate this
        # (e.g. via a configure_submit closure) to simulate IB error/warning
        # pushes such as 2161 (PMA cap); the pipeline baselines + deltas it.
        self._error_codes: dict[int, int] = {}

    @property
    def observed_error_codes(self) -> dict[int, int]:
        return dict(self._error_codes)

    def configure_submit(self, fn: Callable[[Order], list[OrderEvent]]) -> None:
        self._on_submit = fn

    def configure_cancel(self, fn: Callable[[ClientOrderId], list[OrderEvent]]) -> None:
        self._on_cancel = fn

    @staticmethod
    def _default_on_submit(order: Order) -> list[OrderEvent]:
        # Default: SUBMITTED → ACCEPTED → FILLED at the order's reference price
        # for the full quantity, no commission.
        cid = ClientOrderId(order.client_order_id)
        ref_price = order.limit_price if order.limit_price is not None else Decimal("100")
        fill = Fill(
            client_order_id=cid,
            venue_order_id="42",
            venue_exec_id=str(uuid4()),
            instrument=order.instrument,
            side=order.side,
            quantity=order.quantity,
            price=ref_price,
            commission=Decimal("0"),
            currency=order.instrument.currency,
            time_utc=order.created_at,
        )
        now = order.created_at
        return [
            OrderEvent(
                client_order_id=cid,
                venue_order_id="42",
                kind=OrderEventKind.SUBMITTED,
                reason=None,
                time_utc=now,
            ),
            OrderEvent(
                client_order_id=cid,
                venue_order_id="42",
                kind=OrderEventKind.ACCEPTED,
                reason=None,
                time_utc=now,
            ),
            OrderEvent(
                client_order_id=cid,
                venue_order_id="42",
                kind=OrderEventKind.FILLED,
                reason=None,
                time_utc=now,
                fill=fill,
            ),
        ]

    @staticmethod
    def _default_on_cancel(cid: ClientOrderId) -> list[OrderEvent]:
        now = datetime.now(tz=timezone.utc)
        return [
            OrderEvent(
                client_order_id=cid,
                venue_order_id="42",
                kind=OrderEventKind.CANCELED,
                reason="engine",
                time_utc=now,
            )
        ]

    async def submit(self, order: Order) -> ClientOrderId:
        self.submitted_orders.append(order)
        for event in self._on_submit(order):
            await self._events.put(event)
        return ClientOrderId(order.client_order_id)

    async def cancel(self, client_order_id: ClientOrderId) -> None:
        self.canceled_ids.append(client_order_id)
        for event in self._on_cancel(client_order_id):
            await self._events.put(event)


# --- Fixtures ---------------------------------------------------------------


@pytest.fixture
def fixture_path(tmp_path: Path) -> Path:
    """20-day CAC.PA-like parquet."""
    base = datetime(2026, 1, 5, 15, 30, tzinfo=timezone.utc)
    rows = []
    for i in range(20):
        t = base + timedelta(days=i)
        rows.append(
            dict(
                open_time_utc=t - timedelta(hours=8),
                close_time_utc=t,
                open=78.0 + i * 0.1,
                high=79.0 + i * 0.1,
                low=77.0 + i * 0.1,
                close=78.5 + i * 0.1,
                volume=1000.0,
            )
        )
    df = pd.DataFrame(rows)
    p = tmp_path / "cac_pa_20d.parquet"
    df.to_parquet(p)
    return p


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(
        symbol="CAC.PA",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
        tradability="spot",
    )


def _make_live_strategy(
    nav_slice: Decimal = Decimal("0.05"),
    risk_overrides: RiskOverrides | None = None,
    artefact_paths: ArtefactPaths | None = None,
) -> LiveStrategy:
    cfg = LiveStrategyConfig(
        strategy_id="fake_strategy",
        strategy_module="dummy",
        nav_slice=nav_slice,
        live_overrides=LiveOverrides(),
        risk_overrides=risk_overrides or RiskOverrides(),
        artefact_paths=artefact_paths or ArtefactPaths(),
    )
    return LiveStrategy(
        strategy=object(),  # not used by run_ib_pipeline (signal injected)
        live_config=cfg,
        spec_id="0" * 64,
        artefact_sha256_by_factor={},
    )


def _always_long(bar_times: list[datetime]) -> pd.Series:
    return pd.Series(
        data=[1] * len(bar_times),
        index=pd.to_datetime(bar_times, utc=True),
    )


# --- Tests ------------------------------------------------------------------


def test_run_ib_pipeline_requires_connected_broker(
    fixture_path: Path, instrument: Instrument
) -> None:
    md = PaperMarketData(fixtures={instrument: fixture_path})
    broker = _FakeIBBroker(is_connected=False)
    live = _make_live_strategy()
    bar_times = [b.close_time_utc for b in md.bars(instrument)]
    position = _always_long(bar_times)
    with pytest.raises(RuntimeError, match="already-connected"):
        asyncio.run(
            run_ib_pipeline(
                live_strategy=live,
                broker=broker,  # type: ignore[arg-type]
                market_data=md,
                instrument=instrument,
                position_series=position,
            )
        )


def test_run_ib_pipeline_empty_bars_raises(tmp_path: Path, instrument: Instrument) -> None:
    """Empty fixture → ValueError; pipeline can't size against zero bars."""
    df = pd.DataFrame(
        {
            "open_time_utc": pd.to_datetime([], utc=True),
            "close_time_utc": pd.to_datetime([], utc=True),
            "open": pd.Series([], dtype=float),
            "high": pd.Series([], dtype=float),
            "low": pd.Series([], dtype=float),
            "close": pd.Series([], dtype=float),
            "volume": pd.Series([], dtype=float),
        }
    )
    p = tmp_path / "empty.parquet"
    df.to_parquet(p)
    md = PaperMarketData(fixtures={instrument: p})
    broker = _FakeIBBroker()
    live = _make_live_strategy()
    with pytest.raises(ValueError, match="no bars"):
        asyncio.run(
            run_ib_pipeline(
                live_strategy=live,
                broker=broker,  # type: ignore[arg-type]
                market_data=md,
                instrument=instrument,
                position_series=pd.Series(dtype=int),
            )
        )


def test_run_ib_pipeline_happy_path_records_fill(
    fixture_path: Path, instrument: Instrument
) -> None:
    """Position=1 every day, broker fills at LMT price → one entry fill;
    subsequent days are flat (target unchanged) so no further submits."""
    md = PaperMarketData(fixtures={instrument: fixture_path})
    bar_times = [b.close_time_utc for b in md.bars(instrument)]
    position = _always_long(bar_times)

    broker = _FakeIBBroker()
    live = _make_live_strategy(nav_slice=Decimal("0.05"))

    result: IBRunResult = asyncio.run(
        run_ib_pipeline(
            live_strategy=live,
            broker=broker,  # type: ignore[arg-type]
            market_data=md,
            instrument=instrument,
            position_series=position,
            starting_cash=Decimal("100000"),
        )
    )

    assert result.fills_count == 1, "always-long → only the entry submits"
    assert result.canceled_count == 0
    assert result.rejected_count == 0
    # First-bar entry: nav_slice=0.05 * 100k = 5k; price ~78.5 LMT crossed +50bps
    # → ~78.89; qty ≈ 63.
    final = result.equity_curve[-1]
    assert final.position_qty == Decimal("63")
    # Equity tracks: cash debited by qty * fill_price; final mark uses last bar close.
    assert final.equity > Decimal("99000")
    # Submitted exactly once.
    assert len(broker.submitted_orders) == 1
    submitted = broker.submitted_orders[0]
    assert submitted.side == OrderSide.BUY


def test_run_ib_pipeline_position_flip_triggers_exit(
    fixture_path: Path, instrument: Instrument
) -> None:
    """Position 1 then 0 mid-series → entry fill, then exit fill on flip."""
    md = PaperMarketData(fixtures={instrument: fixture_path})
    bar_times = [b.close_time_utc for b in md.bars(instrument)]
    half = len(bar_times) // 2
    values = [1] * half + [0] * (len(bar_times) - half)
    position = pd.Series(data=values, index=pd.to_datetime(bar_times, utc=True))

    broker = _FakeIBBroker()
    live = _make_live_strategy(nav_slice=Decimal("0.05"))

    result = asyncio.run(
        run_ib_pipeline(
            live_strategy=live,
            broker=broker,  # type: ignore[arg-type]
            market_data=md,
            instrument=instrument,
            position_series=position,
            starting_cash=Decimal("100000"),
        )
    )

    assert result.fills_count == 2, "expected entry fill + exit fill on the position flip"
    sides = [o.side for o in broker.submitted_orders]
    assert sides == [OrderSide.BUY, OrderSide.SELL]


def test_run_ib_pipeline_kill_switch_armed_blocks_submits(
    fixture_path: Path, instrument: Instrument
) -> None:
    """RC-13 kill switch armed pre-run → zero submits, breaches recorded."""
    md = PaperMarketData(fixtures={instrument: fixture_path})
    bar_times = [b.close_time_utc for b in md.bars(instrument)]
    position = _always_long(bar_times)

    broker = _FakeIBBroker()
    live = _make_live_strategy()
    ks = KillSwitch()
    ks.arm("test pre-armed kill switch")

    result = asyncio.run(
        run_ib_pipeline(
            live_strategy=live,
            broker=broker,  # type: ignore[arg-type]
            market_data=md,
            instrument=instrument,
            position_series=position,
            starting_cash=Decimal("100000"),
            kill_switch=ks,
        )
    )

    assert result.fills_count == 0
    assert result.submitted_count == 0
    assert len(broker.submitted_orders) == 0
    assert len(result.breaches) >= 1, "expected at least one RC-13 breach logged"


def test_run_ib_pipeline_canceled_when_no_terminal_within_timeout(
    fixture_path: Path, instrument: Instrument
) -> None:
    """If submit() emits only SUBMITTED + ACCEPTED (no fill, no terminal),
    the pipeline times out and engine-cancels the order; cancel emits
    CANCELED → counted in result.canceled_count."""
    md = PaperMarketData(fixtures={instrument: fixture_path})
    bar_times = [b.close_time_utc for b in md.bars(instrument)]
    position = _always_long(bar_times)

    broker = _FakeIBBroker()

    def _on_submit_no_terminal(order: Order) -> list[OrderEvent]:
        cid = ClientOrderId(order.client_order_id)
        now = order.created_at
        # No FILLED / CANCELED / REJECTED — pipeline must time out and cancel.
        return [
            OrderEvent(
                client_order_id=cid,
                venue_order_id="42",
                kind=OrderEventKind.SUBMITTED,
                reason=None,
                time_utc=now,
            ),
            OrderEvent(
                client_order_id=cid,
                venue_order_id="42",
                kind=OrderEventKind.ACCEPTED,
                reason=None,
                time_utc=now,
            ),
        ]

    broker.configure_submit(_on_submit_no_terminal)

    live = _make_live_strategy()

    result = asyncio.run(
        run_ib_pipeline(
            live_strategy=live,
            broker=broker,  # type: ignore[arg-type]
            market_data=md,
            instrument=instrument,
            position_series=position,
            starting_cash=Decimal("100000"),
            event_wait_seconds=0.05,  # short for fast test
        )
    )

    assert result.fills_count == 0
    # Always-long with no fills → every bar attempts entry, every one cancels.
    # The fake's cancel() emits CANCELED so count grows per attempt.
    assert result.canceled_count >= 1
    assert len(broker.canceled_ids) >= 1


# --- Multi-instrument pipeline tests (M2-IB.6 per ADR-044) ------------------


def _us_etf(symbol: str) -> Instrument:
    """Construct a US ETF Instrument for multi-instrument tests."""
    return Instrument(
        symbol=symbol,
        venue="XNAS",
        currency="USD",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
        tradability="spot",
    )


@pytest.fixture
def triple_lev_fixture_paths(tmp_path: Path) -> dict[str, Path]:
    """20-day fixtures for TQQQ, TMF, IEF — all sharing the same close
    timestamps to mirror US calendar uniformity."""
    base = datetime(2026, 1, 5, 15, 30, tzinfo=timezone.utc)
    paths: dict[str, Path] = {}
    starts = {"TQQQ": 50.0, "TMF": 30.0, "IEF": 100.0}
    for symbol, start_price in starts.items():
        rows = []
        for i in range(20):
            t = base + timedelta(days=i)
            close = start_price + i * 0.1
            rows.append(
                dict(
                    open_time_utc=t - timedelta(hours=8),
                    close_time_utc=t,
                    open=close - 0.05,
                    high=close + 0.5,
                    low=close - 0.5,
                    close=close,
                    volume=1000.0,
                )
            )
        df = pd.DataFrame(rows)
        p = tmp_path / f"{symbol}_20d.parquet"
        df.to_parquet(p)
        paths[symbol] = p
    return paths


@pytest.fixture
def triple_lev_market_data(triple_lev_fixture_paths: dict[str, Path]) -> PaperMarketData:
    fixtures = {_us_etf(symbol): path for symbol, path in triple_lev_fixture_paths.items()}
    return PaperMarketData(fixtures=fixtures)


@pytest.fixture
def triple_lev_instruments() -> list[Instrument]:
    """Canonical order — TQQQ first matches the order ADR-043 + the
    eligibility parquet column convention."""
    return [_us_etf("TQQQ"), _us_etf("TMF"), _us_etf("IEF")]


def _both_legs_eligible_weights(canonical_bars_close_times: list[datetime]) -> pd.DataFrame:
    """Always {TQQQ:0.5, TMF:0.5, IEF:0} — both risk-on legs active throughout."""
    n = len(canonical_bars_close_times)
    return pd.DataFrame(
        {"TQQQ": [0.5] * n, "TMF": [0.5] * n, "IEF": [0.0] * n},
        index=pd.to_datetime(canonical_bars_close_times, utc=True),
    )


def test_run_ib_multi_pipeline_requires_connected_broker(
    triple_lev_market_data: PaperMarketData,
    triple_lev_instruments: list[Instrument],
) -> None:
    broker = _FakeIBBroker(is_connected=False)
    live = _make_live_strategy()
    bars = triple_lev_market_data.bars(triple_lev_instruments[0])
    weights = _both_legs_eligible_weights([b.close_time_utc for b in bars])
    with pytest.raises(RuntimeError, match="already-connected"):
        asyncio.run(
            run_ib_multi_pipeline(
                live_strategy=live,
                broker=broker,  # type: ignore[arg-type]
                market_data=triple_lev_market_data,
                instruments=triple_lev_instruments,
                target_weights_series=weights,
            )
        )


def test_run_ib_multi_pipeline_empty_instruments_raises(
    triple_lev_market_data: PaperMarketData,
) -> None:
    broker = _FakeIBBroker()
    live = _make_live_strategy()
    weights = pd.DataFrame({"TQQQ": [0.5]})
    with pytest.raises(ValueError, match="non-empty"):
        asyncio.run(
            run_ib_multi_pipeline(
                live_strategy=live,
                broker=broker,  # type: ignore[arg-type]
                market_data=triple_lev_market_data,
                instruments=[],
                target_weights_series=weights,
            )
        )


def test_run_ib_multi_pipeline_empty_weights_raises(
    triple_lev_market_data: PaperMarketData,
    triple_lev_instruments: list[Instrument],
) -> None:
    broker = _FakeIBBroker()
    live = _make_live_strategy()
    with pytest.raises(ValueError, match="must not be empty"):
        asyncio.run(
            run_ib_multi_pipeline(
                live_strategy=live,
                broker=broker,  # type: ignore[arg-type]
                market_data=triple_lev_market_data,
                instruments=triple_lev_instruments,
                target_weights_series=pd.DataFrame(),
            )
        )


def test_run_ib_multi_pipeline_happy_path_3_instruments_both_legs(
    triple_lev_market_data: PaperMarketData,
    triple_lev_instruments: list[Instrument],
) -> None:
    """Always {TQQQ:0.5, TMF:0.5, IEF:0} → both risk-on legs hold positions
    throughout; daily rebalances may produce small adjustment fills as
    equity drifts (this is correct: ADR-027 integer-share rounding +
    daily rebalance against drifting equity → micro-rebalance fills).

    Core invariants tested:
    - Multi-instrument FSM round trips work (fills happen).
    - Per-symbol fill tracking populates fills_by_symbol.
    - Final positions are held in TQQQ and TMF (the two eligible legs).
    - Equity curve has one row per bar (20 bars → 20 points)."""
    broker = _FakeIBBroker()
    live = _make_live_strategy(nav_slice=Decimal("0.05"))
    bars = triple_lev_market_data.bars(triple_lev_instruments[0])
    weights = _both_legs_eligible_weights([b.close_time_utc for b in bars])

    result: IBMultiRunResult = asyncio.run(
        run_ib_multi_pipeline(
            live_strategy=live,
            broker=broker,  # type: ignore[arg-type]
            market_data=triple_lev_market_data,
            instruments=triple_lev_instruments,
            target_weights_series=weights,
            starting_cash=Decimal("100000"),
        )
    )

    # Multi-instrument fills happen across the 20-bar replay.
    assert result.fills_count >= 2, "expected at least one entry fill per active leg"
    assert result.submitted_count >= 2
    assert result.rejected_count == 0
    # Per-symbol tracking: both eligible legs accumulate fills.
    assert result.fills_by_symbol.get("TQQQ", 0) >= 1
    assert result.fills_by_symbol.get("TMF", 0) >= 1
    # Equity curve: one row per canonical bar.
    assert len(result.equity_curve) == 20
    # Final-row positions: both eligible legs are held with positive qty.
    final = result.equity_curve[-1]
    assert final.positions.get("TQQQ", Decimal("0")) > Decimal("0")
    assert final.positions.get("TMF", Decimal("0")) > Decimal("0")


def test_run_ib_multi_pipeline_regime_flip_TMF_to_IEF(
    triple_lev_market_data: PaperMarketData,
    triple_lev_instruments: list[Instrument],
) -> None:
    """Day-1: {TQQQ:0.5, TMF:0.5, IEF:0} (both legs in). Day-10 onwards:
    {TQQQ:0.5, TMF:0, IEF:0.5} (TMF leg parks in IEF). Pipeline must
    SELL TMF + BUY IEF on day-10."""
    broker = _FakeIBBroker()
    live = _make_live_strategy(nav_slice=Decimal("0.05"))
    bars = triple_lev_market_data.bars(triple_lev_instruments[0])
    times = [b.close_time_utc for b in bars]
    n = len(times)
    flip_idx = 10
    weights = pd.DataFrame(
        {
            "TQQQ": [0.5] * n,
            "TMF": [0.5] * flip_idx + [0.0] * (n - flip_idx),
            "IEF": [0.0] * flip_idx + [0.5] * (n - flip_idx),
        },
        index=pd.to_datetime(times, utc=True),
    )

    result = asyncio.run(
        run_ib_multi_pipeline(
            live_strategy=live,
            broker=broker,  # type: ignore[arg-type]
            market_data=triple_lev_market_data,
            instruments=triple_lev_instruments,
            target_weights_series=weights,
            starting_cash=Decimal("100000"),
        )
    )

    # Core invariants for the regime flip:
    # - Some fills happen for all three instruments across the run.
    # - The flip produces a SELL TMF + BUY IEF transition (sides observable
    #   in submitted_orders).
    # (Daily rebalance with drifting equity also produces small adjustment
    # fills; we don't assert exact counts to keep the test robust.)
    assert result.fills_count >= 3, "regime flip should yield at least entry + exit + new-entry"
    sides = [(o.instrument.symbol, o.side) for o in broker.submitted_orders]
    # The TMF leg must SELL at some point during the post-flip phase.
    assert ("TMF", OrderSide.SELL) in sides
    # IEF must BUY (the new safe-haven park leg).
    assert ("IEF", OrderSide.BUY) in sides
    # All three instruments see at least one fill.
    assert result.fills_by_symbol.get("TQQQ", 0) >= 1
    assert result.fills_by_symbol.get("TMF", 0) >= 1
    assert result.fills_by_symbol.get("IEF", 0) >= 1


def test_run_ib_multi_pipeline_kill_switch_armed_blocks_submits(
    triple_lev_market_data: PaperMarketData,
    triple_lev_instruments: list[Instrument],
) -> None:
    """Kill-switch armed pre-run → zero submits across all instruments."""
    broker = _FakeIBBroker()
    live = _make_live_strategy()
    ks = KillSwitch()
    ks.arm("multi-instrument kill-switch test")
    bars = triple_lev_market_data.bars(triple_lev_instruments[0])
    weights = _both_legs_eligible_weights([b.close_time_utc for b in bars])

    result = asyncio.run(
        run_ib_multi_pipeline(
            live_strategy=live,
            broker=broker,  # type: ignore[arg-type]
            market_data=triple_lev_market_data,
            instruments=triple_lev_instruments,
            target_weights_series=weights,
            starting_cash=Decimal("100000"),
            kill_switch=ks,
        )
    )

    assert result.fills_count == 0
    assert result.submitted_count == 0
    assert len(broker.submitted_orders) == 0
    # Kill-switch fires once per Sizer-produced order per rebalance, across
    # multiple bars + instruments → many breaches.
    assert len(result.breaches) >= 1


def test_run_ib_multi_pipeline_equity_curve_includes_all_instruments(
    triple_lev_market_data: PaperMarketData,
    triple_lev_instruments: list[Instrument],
) -> None:
    """IBMultiEquityPoint.mark_prices captures every instrument's close
    at each rebalance, even those without held positions."""
    broker = _FakeIBBroker()
    live = _make_live_strategy(nav_slice=Decimal("0.05"))
    bars = triple_lev_market_data.bars(triple_lev_instruments[0])
    weights = _both_legs_eligible_weights([b.close_time_utc for b in bars])

    result = asyncio.run(
        run_ib_multi_pipeline(
            live_strategy=live,
            broker=broker,  # type: ignore[arg-type]
            market_data=triple_lev_market_data,
            instruments=triple_lev_instruments,
            target_weights_series=weights,
            starting_cash=Decimal("100000"),
        )
    )
    final = result.equity_curve[-1]
    # All 3 instruments have mark prices (even IEF which has no held position).
    assert set(final.mark_prices.keys()) == {"TQQQ", "TMF", "IEF"}
    assert all(p > Decimal("0") for p in final.mark_prices.values())


# --- M3.1 / ADR-050 — EODHD-vs-IB conversion at the pipeline boundary -------


def _qql3_instrument() -> Instrument:
    """QQL3 on LSEETF per ADR-047 / ADR-048. The catalogue entry per
    ADR-050 is the load-bearing test fixture: divisor 10 against IB
    live reference."""
    return Instrument(
        symbol="QQL3",
        venue="XLON",
        currency="USD",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
        tradability="spot",
    )


@pytest.fixture
def qql3_only_market_data(tmp_path: Path) -> tuple[PaperMarketData, list[Instrument]]:
    """20-day QQL3-only fixture; close price ~$400 (raw EODHD scale,
    reflecting the M3.1 split-lag scenario). The convention catalogue
    converts to ~$40 IB-equivalent."""
    base = datetime(2026, 1, 5, 15, 30, tzinfo=timezone.utc)
    rows = []
    for i in range(20):
        t = base + timedelta(days=i)
        close = 400.0 + i * 1.0
        rows.append(
            dict(
                open_time_utc=t - timedelta(hours=8),
                close_time_utc=t,
                open=close - 0.5,
                high=close + 1.0,
                low=close - 1.0,
                close=close,
                volume=1000.0,
            )
        )
    p = tmp_path / "QQL3_20d.parquet"
    pd.DataFrame(rows).to_parquet(p)
    inst = _qql3_instrument()
    md = PaperMarketData(fixtures={inst: p})
    return md, [inst]


def test_run_ib_multi_pipeline_qql3_uses_converted_price_for_sizing_and_marks(
    qql3_only_market_data: tuple[PaperMarketData, list[Instrument]],
) -> None:
    """The M3.1 happy path — QQL3 in the catalogue (divisor 10):

    - Sizer sees the converted price ~$40 not raw $400, so position
      sizes are 10× larger than the no-conversion case (correct
      IB-USD-equivalent exposure).
    - Equity-curve mark_prices reflect the converted scale.
    - No RC-10 BLOCK fires on the strategy's MKT orders (MKT is a
      no-op for RC-10 by design)."""
    market_data, instruments = qql3_only_market_data
    broker = _FakeIBBroker()
    live = _make_live_strategy(nav_slice=Decimal("0.05"))
    bars = market_data.bars(instruments[0])
    weights = pd.DataFrame(
        {"QQL3": [1.0] * len(bars)},
        index=pd.to_datetime([b.close_time_utc for b in bars], utc=True),
    )

    result = asyncio.run(
        run_ib_multi_pipeline(
            live_strategy=live,
            broker=broker,  # type: ignore[arg-type]
            market_data=market_data,
            instruments=instruments,
            target_weights_series=weights,
            starting_cash=Decimal("100000"),
        )
    )

    # Mark price is the IB-equivalent (raw EODHD / 10), not raw EODHD.
    final = result.equity_curve[-1]
    final_mark = final.mark_prices["QQL3"]
    # Last bar raw close = 400 + 19 = 419; converted = 41.9
    assert Decimal("40") <= final_mark <= Decimal("45")

    # Sizer at NAV slice 0.05 with $100k starting cash and target_weight=1.0
    # against a ~$40 converted price gives ~125 shares (5000 / 40),
    # versus only ~12 if using the raw $400 price. The first rebalance
    # is the diagnostic.
    first = result.equity_curve[0]
    first_qty = first.positions.get("QQL3", Decimal("0"))
    # Expect a non-trivial position size that's plausible at the
    # converted scale (>50 shares; raw EODHD would give <15).
    assert first_qty > Decimal("50"), (
        f"expected >50 QQL3 shares from converted-price sizing, got {first_qty} "
        f"(would be ~12 if conversion were missing)"
    )

    # No RC-10 BLOCK on MKT orders; conversion handled at sizing time.
    assert all(b.check.value != "RC-10" for b in result.breaches)


# --- M3.2 capture — per-symbol counts, FSM coverage, 2161 cap-binding -------


def test_multi_pipeline_tracks_submitted_by_symbol_and_accepted_count(
    triple_lev_market_data: PaperMarketData,
    triple_lev_instruments: list[Instrument],
) -> None:
    """M3.2: submitted_by_symbol is the per-instrument placed denominator;
    accepted_count counts orders that reached ACCEPTED. On the happy path
    every submit reaches FILLED (through ACCEPTED), so accepted_count ==
    submitted_count and the per-symbol placed counts sum to submitted_count."""
    broker = _FakeIBBroker()
    live = _make_live_strategy(nav_slice=Decimal("0.05"))
    bars = triple_lev_market_data.bars(triple_lev_instruments[0])
    weights = _both_legs_eligible_weights([b.close_time_utc for b in bars])

    result = asyncio.run(
        run_ib_multi_pipeline(
            live_strategy=live,
            broker=broker,  # type: ignore[arg-type]
            market_data=triple_lev_market_data,
            instruments=triple_lev_instruments,
            target_weights_series=weights,
            starting_cash=Decimal("100000"),
        )
    )

    assert result.submitted_count > 0
    assert sum(result.submitted_by_symbol.values()) == result.submitted_count
    assert set(result.submitted_by_symbol).issubset({"TQQQ", "TMF", "IEF"})
    # Happy path: every submit reaches ACCEPTED then FILLED.
    assert result.accepted_count == result.submitted_count
    # cap_binding is zero — no 2161 simulated on the default fake.
    assert result.cap_binding_2161_count == 0
    assert result.observed_error_codes == {}


def test_multi_pipeline_records_2161_cap_binding_from_broker(
    triple_lev_market_data: PaperMarketData,
    triple_lev_instruments: list[Instrument],
) -> None:
    """M3.2 / OQ-031: a submit that emits SUBMITTED→ACCEPTED but never fills
    (the cap binds) and pushes warning 2161 on the broker's error channel
    is captured in observed_error_codes / cap_binding_2161_count via the
    pipeline's baseline→delta snapshot."""
    broker = _FakeIBBroker()

    def _on_submit_cap_bound(order: Order) -> list[OrderEvent]:
        # Simulate IB's errorEvent push for warning 2161 on this order.
        broker._error_codes[2161] = broker._error_codes.get(2161, 0) + 1
        cid = ClientOrderId(order.client_order_id)
        now = order.created_at
        return [
            OrderEvent(
                client_order_id=cid,
                venue_order_id="42",
                kind=OrderEventKind.SUBMITTED,
                reason=None,
                time_utc=now,
            ),
            OrderEvent(
                client_order_id=cid,
                venue_order_id="42",
                kind=OrderEventKind.ACCEPTED,
                reason=None,
                time_utc=now,
            ),
            # No FILLED — the cap binds and the market moves away.
        ]

    broker.configure_submit(_on_submit_cap_bound)
    live = _make_live_strategy(nav_slice=Decimal("0.05"))
    bars = triple_lev_market_data.bars(triple_lev_instruments[0])
    times = [b.close_time_utc for b in bars]
    # Only the first 3 rebalances to keep the timeout loop fast.
    weights = _both_legs_eligible_weights(times[:3])

    result = asyncio.run(
        run_ib_multi_pipeline(
            live_strategy=live,
            broker=broker,  # type: ignore[arg-type]
            market_data=triple_lev_market_data,
            instruments=triple_lev_instruments,
            target_weights_series=weights,
            starting_cash=Decimal("100000"),
            event_wait_seconds=0.05,
        )
    )

    # Every submit pushed a 2161; the pipeline captured the delta.
    assert result.cap_binding_2161_count >= 1
    assert result.observed_error_codes.get(2161) == result.cap_binding_2161_count
    assert result.cap_binding_2161_count == result.submitted_count
    # Reached ACCEPTED but never FILLED → engine-cancelled, zero fills.
    assert result.accepted_count == result.submitted_count
    assert result.fills_count == 0
    assert result.canceled_count >= 1


def test_multi_pipeline_no_accept_does_not_count_accepted(
    triple_lev_market_data: PaperMarketData,
    triple_lev_instruments: list[Instrument],
) -> None:
    """An order that times out in SUBMITTED (never ACCEPTED) must not
    increment accepted_count — the FSM-trace coverage metric stays honest."""
    broker = _FakeIBBroker()

    def _on_submit_no_accept(order: Order) -> list[OrderEvent]:
        cid = ClientOrderId(order.client_order_id)
        return [
            OrderEvent(
                client_order_id=cid,
                venue_order_id="42",
                kind=OrderEventKind.SUBMITTED,
                reason=None,
                time_utc=order.created_at,
            ),
        ]

    broker.configure_submit(_on_submit_no_accept)
    live = _make_live_strategy(nav_slice=Decimal("0.05"))
    bars = triple_lev_market_data.bars(triple_lev_instruments[0])
    times = [b.close_time_utc for b in bars]
    weights = _both_legs_eligible_weights(times[:3])

    result = asyncio.run(
        run_ib_multi_pipeline(
            live_strategy=live,
            broker=broker,  # type: ignore[arg-type]
            market_data=triple_lev_market_data,
            instruments=triple_lev_instruments,
            target_weights_series=weights,
            starting_cash=Decimal("100000"),
            event_wait_seconds=0.05,
        )
    )

    assert result.submitted_count >= 1
    assert result.accepted_count == 0
    assert result.fills_count == 0
    assert result.canceled_count >= 1
