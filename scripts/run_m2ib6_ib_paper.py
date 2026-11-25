"""M2-IB.6 multi-instrument paper-test driver — `triple_lev_sma_filter_dsl` on IB Paper.

Operationalises [ADR-043](../docs/decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2)
+ [ADR-044](../docs/decisions/DECISIONS.md#adr-044--multi-instrument-pipeline-support-companion-to-adr-043)
+ [ADR-045](../docs/decisions/DECISIONS.md#adr-045--longshortportfolio-btest-dispatch-extends-adr-030)
+ [ADR-046](../docs/decisions/DECISIONS.md#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032)
+ [ADR-047](../docs/decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043)
end-to-end. Wires:

1. **5 EODHD parquets** (QQL3 / IBTL / IBTM / QQQ / TLT) loaded via
   :class:`PaperMarketData`. Three of those are tradables (UK-listed
   PRIIPs-compliant analogues per ADR-047 — the original notebook's
   TQQQ / TMF / IEF are PRIIPs-blocked from UK retail accounts; see
   INV-14 v0.5 for the error 201 KID-variant). QQQ + TLT are the
   trend-signal tickers used by `refresh_eodhd_signals.py` (signal-only,
   never traded — PRIIPs does not apply).
2. **Eligibility signals parquet** loaded from
   ``~/.blive/data/signals/triple_lev_sma_eligible.parquet`` (produced
   by `scripts/refresh_eodhd_signals.py` with columns QQL3 / IBTL /
   IBTM in IB-symbol order).
3. **Target weights** via
   :func:`blive.runtime.signals.eligibility_to_target_weights` — the
   LongShortPortfolio + MaskSelector + EqualWeight semantics applied
   per row.
4. **`IBBroker`** with the production :class:`IBInstrumentResolver`
   (XLON venue → SMART or direct-routed, per the resolver's venue-MIC
   handling) connecting to IB Paper Gateway.
5. **`run_ib_multi_pipeline`** orchestrates the rebalance loop.

Pipeline-mechanics test, **not** a parity-meaningful run. Orders submitted
to IB Paper fill at the venue's *current* market, not at the historical
bar's close — the equity curve informs FSM correctness and integration
health, not strategy quality. Note also that IBTL is **1× leverage** (not
3× — no UK-listed 3× US-Treasury ETP exists per ADR-047) so the strategy's
risk-on regime profile shifts vs. the notebook's TMF leg; the parity
envelope re-derives at M7. The full real-time-clock multi-day
"≥ 5 trading days" run is the M5+ daemon shape.

Defaults:

- Order type **MKT** (guaranteed FSM termination during LSE RTH).
- ``--max-bars 60`` (~3 months of daily bars; eligibility computation
  needs ~SMA-200 of warmup so the parquet's earlier history is the
  warmup, the last N bars are replayed).
- NAV slice **0.05** (Phase 1 lower bound per ADR-020).
- Per-order timeout **10s**.

Operator prereqs (per `M2-IB.4a-happy-cacpa`):

- IB Gateway running on the configured port (default 4002 paper).
- "Read-Only API" unchecked.
- For LSE-listed UCITS / ETPs the
  "Bypass Order Precautions for API Orders" toggle is **recommended on**
  (matches the M2-IB.4a-happy-cacpa setup); LSE direct-routing does not
  trigger the SMART-vs-direct error 10311 cascade since LSE is the
  primary venue.
- ``~/.blive/secrets/ib.env`` populated.
- ``~/.blive/data/eodhd/{ib_symbol}_1d.parquet`` for all 5 IB symbols
  (QQL3 / IBTL / IBTM / QQQ / TLT), produced by
  `scripts/refresh_eodhd_signals.py`.
- ``~/.blive/data/signals/triple_lev_sma_eligible.parquet`` produced
  by the same script.

Usage::

    uv run python scripts/run_m2ib6_ib_paper.py
    uv run python scripts/run_m2ib6_ib_paper.py --order-type LMT --max-bars 30
    uv run python scripts/run_m2ib6_ib_paper.py --max-bars 0  # full replay

M3.2 bounded deterministic capture (per [TASK_REGISTRY M3.2](../TASK_REGISTRY.md)):
the milestone closes on a small, definite set of capture rows rather than 10
calendar days. Regime variety comes from the **replay window** (the signal is
historical), not the calendar, so it is deterministic. Workflow::

    # 1. offline: size --max-bars to span >= 1 equity-leg regime flip (no IB)
    ... run_m2ib6_ib_paper.py --max-bars 250 --dry-run
    # 2. during LSE RTH: capture the run (one row appended to runs.jsonl)
    ... run_m2ib6_ib_paper.py --order-type LMT --max-bars 250
    # ... annotate a regime-flat datapoint:
    ... run_m2ib6_ib_paper.py --max-bars 5 --note "regime-flat"

Exit codes:

    0  success — pipeline ran to completion (regardless of fill counts)
    2  credentials / args / file-not-found
    3  IB Paper connect / network failure
    5  internal pipeline error (raised + traceback printed)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import traceback
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pandas as pd

from blive.adapters.clock.wall import WallClock
from blive.adapters.ib import (
    IB_DEFAULT_RATE_LIMITS,
    IBClient,
    IBConnectionError,
    IBCredentials,
    IBInstrumentResolver,
)
from blive.adapters.ib.broker import IBBroker
from blive.adapters.paper.market_data import PaperMarketData
from blive.adapters.shared.credentials import CredentialsMissing
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter
from blive.domain.types import AssetClass, Instrument, OrderType
from blive.runtime.ib_pipeline import IBMultiRunResult, run_ib_multi_pipeline
from blive.runtime.m3_2_record import (
    append_run_record,
    build_run_record,
    default_window_path,
)
from blive.runtime.signals import eligibility_to_target_weights, equity_leg_regime_flips
from blive.strategy.config import (
    ArtefactPaths,
    LiveOverrides,
    LiveStrategyConfig,
    RiskOverrides,
)
from blive.strategy.loader import LiveStrategy

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("m2ib6")


# Phase 1 instruments per ADR-043 + ADR-047. The PRIIPs-compliant
# substitution is QQL3 (LSE; 3× Nasdaq-100 ETP) for TQQQ, IBTL (LSE; 1×
# 20+yr US Treasury UCITS — no UK-listed 3× US Treasury exists, so the
# leg's leverage drops 3×→1× and the strategy regime profile shifts
# accordingly per ADR-047) for TMF, and IBTM (LSE; 1× 7-10yr US Treasury
# UCITS) for IEF.
#
# Currency caveat (M2-IB.6.1 wire-probe finding, post-ADR-047): IB
# exposes IBTL / IBTM on LSE only as **GBP-hedged** share classes (the
# bare IBTL / IBTM symbols on LSEETF resolve to "ISHARES USD TRES 20+yr"
# / "ISHARES USD TREASURY 7-10Y" GBP-hedged accumulating tranches —
# conIds 181150859 / 68489974). QQL3 trades USD-denominated on LSEETF
# (conId 566361457). Phase 1 P&L is therefore mixed-currency (USD on
# the QQL3 leg, GBP on the IBTL/IBTM legs); the strategy parity envelope
# re-derives at M7. The IB resolver routes XLON+ETF via SMART with
# primaryExchange="LSEETF" (not the main-book "LSE") per DD-7 §3
# discriminator added at M2-IB.6.1.
_QQL3 = Instrument(
    symbol="QQL3",
    venue="XLON",
    currency="USD",
    asset_class=AssetClass.ETF,
    multiplier=Decimal("1"),
    tradability="spot",
)
_IBTL = Instrument(
    symbol="IBTL",
    venue="XLON",
    currency="GBP",
    asset_class=AssetClass.ETF,
    multiplier=Decimal("1"),
    tradability="spot",
)
_IBTM = Instrument(
    symbol="IBTM",
    venue="XLON",
    currency="GBP",
    asset_class=AssetClass.ETF,
    multiplier=Decimal("1"),
    tradability="spot",
)
_TRADABLES: list[Instrument] = [_QQL3, _IBTL, _IBTM]


def _default_eodhd_dir() -> Path:
    return Path.home() / ".blive" / "data" / "eodhd"


def _default_signals_path() -> Path:
    return Path.home() / ".blive" / "data" / "signals" / "triple_lev_sma_eligible.parquet"


def _build_live_strategy(*, strategy_id: str, nav_slice: Decimal) -> LiveStrategy:
    cfg = LiveStrategyConfig(
        strategy_id=strategy_id,
        strategy_module="scripts.run_m2ib6_ib_paper",
        nav_slice=nav_slice,
        live_overrides=LiveOverrides(),
        risk_overrides=RiskOverrides(),
        artefact_paths=ArtefactPaths(),
    )
    return LiveStrategy(
        strategy=object(),  # the eligibility helper produces target_weights; pipeline doesn't read .strategy
        live_config=cfg,
        spec_id="0" * 64,
        artefact_sha256_by_factor={},
    )


def _print_header(title: str) -> None:
    print()
    print(f"=== {title} ===")


def _print_step(label: str, detail: str = "") -> None:
    suffix = f" -- {detail}" if detail else ""
    print(f"  - {label}{suffix}")


def _print_summary(result: IBMultiRunResult, *, starting_cash: Decimal) -> None:
    _print_header("M2-IB.6 paper run summary")
    print(f"  submitted: {result.submitted_count}")
    print(f"  filled:    {result.fills_count}")
    print(f"  canceled:  {result.canceled_count}")
    print(f"  rejected:  {result.rejected_count}")
    print(f"  breaches:  {len(result.breaches)}")
    print(f"  per-symbol fills: {dict(sorted(result.fills_by_symbol.items()))}")
    print(f"  starting cash:  {starting_cash}")
    print(f"  final equity:   {result.final_equity}")
    if result.equity_curve:
        first = result.equity_curve[0]
        last = result.equity_curve[-1]
        print(f"  equity curve:   {len(result.equity_curve)} point(s)")
        print(
            f"    first: {first.time_utc.isoformat()}  positions={dict(first.positions)}  "
            f"equity={first.equity}"
        )
        print(
            f"    last:  {last.time_utc.isoformat()}  positions={dict(last.positions)}  "
            f"equity={last.equity}"
        )
    if result.breaches:
        print("  breaches detail (first 5):")
        for b in result.breaches[:5]:
            print(f"    - {b.check.value}: {b.detail}")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "End-to-end M2-IB.6 paper-test driver: triple_lev_sma_filter_dsl "
            "(QQL3/IBTL/IBTM, Phase 1 PRIIPs-compliant universe per ADR-047) x "
            "IB Paper, multi-instrument pipeline."
        ),
    )
    parser.add_argument(
        "--eodhd-dir",
        type=Path,
        default=None,
        help=(
            "Directory containing the per-ticker EODHD parquets (QQL3 / IBTL / IBTM / "
            "QQQ / TLT)_1d.parquet. Default: ~/.blive/data/eodhd/"
        ),
    )
    parser.add_argument(
        "--signals-path",
        type=Path,
        default=None,
        help=(
            "Path to the wide eligibility-signals parquet. Default: "
            "~/.blive/data/signals/triple_lev_sma_eligible.parquet"
        ),
    )
    parser.add_argument(
        "--starting-cash",
        type=Decimal,
        default=Decimal("100000"),
        help="Starting cash in USD. Default: 100000.",
    )
    parser.add_argument(
        "--nav-slice",
        type=Decimal,
        default=Decimal("0.05"),
        help="NAV slice for the strategy. Default: 0.05 (per ADR-020).",
    )
    parser.add_argument(
        "--order-type",
        choices=["MKT", "LMT"],
        default="MKT",
        help="Order type for submits. Default: MKT (guaranteed fills during RTH).",
    )
    parser.add_argument(
        "--limit-offset-bps",
        type=Decimal,
        default=Decimal("50"),
        help="LMT offset (bps) from bar.close when --order-type LMT. Default: 50.",
    )
    parser.add_argument(
        "--event-wait-seconds",
        type=float,
        default=10.0,
        help="Per-order timeout waiting for terminal event. Default: 10.",
    )
    parser.add_argument(
        "--max-bars",
        type=int,
        default=60,
        help=(
            "Cap the number of replayed rebalance bars (smoke-bound). 0 = no cap. "
            "Default: 60. The eligibility computation in refresh_eodhd_signals.py "
            "uses the full parquet for SMA-200 warmup; --max-bars only caps the "
            "replay window."
        ),
    )
    parser.add_argument(
        "--strategy-id",
        default="triple_lev_sma_filter_dsl",
        help="Strategy id for the run record. Default matches the canonical id.",
    )
    parser.add_argument(
        "--record-path",
        type=Path,
        default=None,
        help=(
            "Path to the M3.2 window results JSONL. One row is appended per run. "
            "Default: ~/.blive/data/m3_2_window/runs.jsonl"
        ),
    )
    parser.add_argument(
        "--no-record",
        action="store_true",
        help="Skip writing the M3.2 results row (e.g. for a throwaway smoke run).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Offline regime-coverage preview: load the signals, compute the "
            "equity-leg regime-flip count for the chosen --max-bars window, print "
            "it, and exit — no IB connection, no results row. Use it to pick a "
            "--max-bars window that spans >= 1 regime flip for the M3.2 bounded "
            "deterministic capture (regime variety comes from the replay window, "
            "not the calendar)."
        ),
    )
    parser.add_argument(
        "--note",
        default="",
        help=(
            "Free-text note stored on the M3.2 results row (e.g. "
            "'regime-flat window' to annotate the OQ-031 evidence per G4 Q2)."
        ),
    )
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> int:
    eodhd_dir = args.eodhd_dir if args.eodhd_dir is not None else _default_eodhd_dir()
    signals_path = args.signals_path if args.signals_path is not None else _default_signals_path()

    # Validate inputs.
    missing: list[str] = []
    for inst in _TRADABLES:
        p = eodhd_dir / f"{inst.symbol}_1d.parquet"
        if not p.is_file():
            missing.append(str(p))
    if not signals_path.is_file():
        missing.append(str(signals_path))
    if missing:
        print("\nFAILED: missing input file(s). Run scripts/refresh_eodhd_signals.py first.")
        for m in missing:
            print(f"  missing: {m}")
        return 2

    _print_header("M2-IB.6 paper-test driver")
    print(f"  eodhd dir:      {eodhd_dir}")
    print(f"  signals path:   {signals_path}")
    print(f"  instruments:    {[i.symbol for i in _TRADABLES]}")
    print(f"  nav slice:      {args.nav_slice}")
    print(f"  starting cash:  {args.starting_cash}")
    print(f"  order type:     {args.order_type}")
    print(f"  max bars:       {'no cap' if args.max_bars == 0 else args.max_bars}")

    # --- Load market data + compute target weights (no IB connection yet) ---
    # Done before connecting so --dry-run can preview regime coverage offline.

    # Build PaperMarketData with the 3 tradable parquets.
    fixtures = {inst: eodhd_dir / f"{inst.symbol}_1d.parquet" for inst in _TRADABLES}
    md = PaperMarketData(fixtures=fixtures)
    canonical_bars = md.bars(_TRADABLES[0])  # QQL3 canonical
    print(
        f"  bars (QQL3 canonical): {len(canonical_bars)} ({canonical_bars[0].close_time_utc.date()} -> {canonical_bars[-1].close_time_utc.date()})"
    )

    # Load eligibility signals + compute target weights.
    eligibility_df = pd.read_parquet(signals_path)
    if eligibility_df.empty:
        print(f"\nFAILED: signals parquet at {signals_path} is empty.")
        return 5
    # Defensive: older eligibility parquets may have a tz-naive index
    # (built from .values in earlier refresh script versions). Force
    # tz-aware UTC so the downstream intersection with canonical bar
    # timestamps doesn't silently come up empty.
    eligibility_index = pd.DatetimeIndex(eligibility_df.index)
    if eligibility_index.tz is None:
        eligibility_index = eligibility_index.tz_localize("UTC")
    eligibility_df.index = eligibility_index
    target_weights_full = eligibility_to_target_weights(eligibility_df)

    # Cap the replay window to --max-bars by trimming the canonical bars and
    # restricting target_weights to the corresponding timestamps.
    if args.max_bars > 0 and len(canonical_bars) > args.max_bars:
        capped_bars = canonical_bars[-args.max_bars :]
        print(
            f"  capping bars: using last {args.max_bars} of {len(canonical_bars)} "
            f"({capped_bars[0].close_time_utc.date()} -> {capped_bars[-1].close_time_utc.date()})"
        )
    else:
        capped_bars = canonical_bars

    capped_index = pd.to_datetime([b.close_time_utc for b in capped_bars], utc=True)
    common_index = target_weights_full.index.intersection(capped_index)
    target_weights_capped = target_weights_full.loc[common_index]
    print(f"  target_weights rows: {len(target_weights_capped)}")
    if len(target_weights_capped) == 0:
        print(
            "\nFAILED: no target_weight rows align with the bar window. "
            "Check that eligibility parquet covers the same date range as the "
            "EODHD ticker parquets."
        )
        return 5

    # Regime coverage of the replay window — deterministic, from the signal.
    # The M3.2 "bounded deterministic capture" close-criterion: pick a
    # --max-bars window that spans >= 1 equity-leg regime flip (regime variety
    # comes from the replay window, not from waiting for live calendar flips).
    regime_flips = equity_leg_regime_flips(target_weights_capped, equity_leg=_QQL3.symbol)
    print(f"  regime-flip count (QQL3 equity leg): {regime_flips}")

    # --dry-run: report regime coverage and exit — no IB, no results row — so
    # the operator can size --max-bars to span a flip before the RTH run.
    if args.dry_run:
        _print_header("Dry run — regime coverage preview (no IB, no record)")
        _print_step("rebalance rows", str(len(target_weights_capped)))
        _print_step("regime-flip count (QQL3)", str(regime_flips))
        if regime_flips == 0:
            _print_step(
                "NOTE",
                "window is regime-FLAT — widen --max-bars to span a QQQ/TLT "
                "SMA-200 flip for the M3.2 regime-variety criterion (or capture "
                "it as a flat datapoint with --note 'regime-flat').",
            )
        return 0

    # Load IB credentials.
    try:
        credentials = IBCredentials.load()
    except CredentialsMissing as exc:
        print(f"\nFAILED: {exc}")
        return 2
    except ValueError as exc:
        print(f"\nFAILED: invalid credentials -- {exc}")
        return 2
    print(
        f"  IB:             host={credentials.host} port={credentials.port} "
        f"client_id={credentials.client_id} account=[REDACTED]"
    )

    # Construct broker stack.
    clock = WallClock()
    rate_limiter = TokenBucketRateLimiter(config=IB_DEFAULT_RATE_LIMITS, clock=clock)
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock)
    resolver = IBInstrumentResolver(client)
    broker = IBBroker(client=client, resolver=resolver, clock=clock)

    _print_header("Connecting to IB Paper")
    try:
        await broker.connect()
    except IBConnectionError as exc:
        print(f"\nFAILED on connect: {exc}")
        return 3
    print(f"  is_connected={broker.is_connected}")

    # If --max-bars trimmed the canonical bar set, we need a market_data view
    # restricted to those bars too — write a small temp parquet per ticker with
    # only the capped bars.
    if capped_bars is not canonical_bars:
        import tempfile

        tmp_dir = Path(tempfile.mkdtemp(prefix="m2ib6-"))
        tmp_fixtures: dict[Instrument, Path] = {}
        for inst in _TRADABLES:
            full_bars = md.bars(inst)
            # Filter full bars to those whose close_time_utc is in capped_index
            capped_set = set(capped_index)
            inst_capped = [b for b in full_bars if pd.Timestamp(b.close_time_utc) in capped_set]
            df_rows = []
            for b in inst_capped:
                df_rows.append(
                    dict(
                        open_time_utc=b.open_time_utc,
                        close_time_utc=b.close_time_utc,
                        open=float(b.open),
                        high=float(b.high),
                        low=float(b.low),
                        close=float(b.close),
                        volume=float(b.volume),
                    )
                )
            tmp_p = tmp_dir / f"{inst.symbol}_capped.parquet"
            pd.DataFrame(df_rows).to_parquet(tmp_p)
            tmp_fixtures[inst] = tmp_p
        capped_md = PaperMarketData(fixtures=tmp_fixtures)
    else:
        capped_md = md

    # Build LiveStrategy + run.
    live = _build_live_strategy(strategy_id=args.strategy_id, nav_slice=args.nav_slice)
    order_type = OrderType.MKT if args.order_type == "MKT" else OrderType.LMT

    # QQL3 (3× Nasdaq leveraged ETP) hits IB's regulatory disruptive-orders
    # price-cap on raw MKT (warning 2161; INV-14 v0.7), so we route it via
    # IBALGO Adaptive (`OrderType.ADAPTIVE_MKT`). IBTM / IBTL are 1× UCITS
    # Treasury ETFs and don't trip the cap — they stay on the global
    # ``order_type`` (MKT default). Per-symbol override only applies when
    # the global order_type is MKT or ADAPTIVE_MKT; for LMT runs (operator
    # explicit) we don't override since the operator-set limit price
    # already constrains routing.
    if order_type == OrderType.MKT:
        order_type_by_symbol = {_QQL3.symbol: OrderType.ADAPTIVE_MKT}
    else:
        order_type_by_symbol = None

    _print_header("Running multi-instrument pipeline")
    try:
        result = await run_ib_multi_pipeline(
            live_strategy=live,
            broker=broker,
            market_data=capped_md,
            instruments=_TRADABLES,
            target_weights_series=target_weights_capped,
            starting_cash=args.starting_cash,
            base_currency="USD",
            order_type=order_type,
            order_type_by_symbol=order_type_by_symbol,
            limit_price_offset_bps=args.limit_offset_bps,
            event_wait_seconds=args.event_wait_seconds,
        )
    except Exception as exc:  # noqa: BLE001 — driver-level error wrapper
        print(f"\nFAILED in pipeline: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        try:
            await broker.disconnect()
        except Exception:  # noqa: BLE001 — best-effort cleanup
            pass
        return 5

    _print_summary(result, starting_cash=args.starting_cash)

    # M3.2: append one structured results row for the empirical window (per
    # TASK_REGISTRY M3.2). Source: IBMultiRunResult counters +
    # observed_error_codes (warning 2161 = cap-binding signal, OQ-031) + the
    # equity-leg regime-flip count from the capped target weights. Written
    # before disconnect so a disconnect hiccup never loses the row.
    if not args.no_record:
        record_path = args.record_path if args.record_path is not None else default_window_path()
        # regime_flips was computed pre-connect (same value drives --dry-run).
        record = build_run_record(
            result=result,
            regime_flip_count=regime_flips,
            rebalance_rows=len(target_weights_capped),
            strategy_id=args.strategy_id,
            instruments=[i.symbol for i in _TRADABLES],
            order_type=args.order_type,
            max_bars=args.max_bars,
            nav_slice=args.nav_slice,
            starting_cash=args.starting_cash,
            run_id=uuid4().hex,
            recorded_at_utc=datetime.now(timezone.utc).isoformat(),
            note=args.note,
        )
        written = append_run_record(record_path, record)
        _print_header("M3.2 results row")
        _print_step("regime-flip count", str(regime_flips))
        _print_step("cap-binding (2161)", str(record.cap_binding_2161_count))
        _print_step("fill-rate by symbol", str(record.fill_rate_by_symbol))
        _print_step("appended to", str(written))

    _print_header("Disconnecting")
    await broker.disconnect()
    print("OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        return asyncio.run(_run(args))
    except KeyboardInterrupt:
        print("\nINTERRUPTED.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
