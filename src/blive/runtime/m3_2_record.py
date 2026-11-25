"""M3.2 empirical-window per-run results sink.

The M3.2 milestone (per [TASK_REGISTRY M3.2](../../../TASK_REGISTRY.md))
runs the ``triple_lev_sma_filter_dsl`` A3 strategy against IB Paper across
10 LSE-RTH trading days and captures, **per run/day**, the metrics the
M3.3 OQ-031 deployment decision rests on:

- per-instrument **fill-rate** (placed vs filled),
- **regime-flip count** (equity-leg long/flat transitions),
- **warning-2161 cap-binding** occurrences (the OQ-031 signal per
  [INV-14 v0.9](../../../docs/inv/ib_error_codes.md)),
- **RiskEngine breach** count,
- **FSM-trace coverage** (SUBMITTED → ACCEPTED → FILLED / CANCELED /
  REJECTED ratios).

This module turns one
:class:`blive.runtime.ib_pipeline.IBMultiRunResult` (plus the
driver-computed regime-flip count and run metadata) into one structured
:class:`RunRecord` and appends it as a single JSON line under
``~/.blive/data/m3_2_window/runs.jsonl`` — so the 10-day window
aggregates without log-scraping. The metric catalogue is
[INV-8](../../../docs/inv/metrics.md); the alert catalogue is
[INV-9](../../../docs/inv/alerts.md).

The builder is pure (no clock / filesystem / randomness): the caller
supplies ``run_id`` + ``recorded_at_utc`` so the row is reproducible and
unit-testable. Decimals are serialised as strings for exactness; the
``observed_error_codes`` int keys become JSON strings on write (json's
standard int-key coercion).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids runtime coupling
    from blive.runtime.ib_pipeline import IBMultiRunResult

#: Bump when the :class:`RunRecord` row shape changes incompatibly so the
#: 10-day aggregation can distinguish schema generations.
SCHEMA_VERSION = 1

#: IB warning code for the Price Management Algo disruptive-orders cap —
#: the OQ-031 fill-rate signal (INV-14 v0.9).
_WARNING_2161 = 2161


@dataclass(frozen=True, slots=True)
class RunRecord:
    """One M3.2 paper-run results row (one line of ``runs.jsonl``).

    Self-contained: every field needed by the M3.3 OQ-031 decision is
    present without re-reading logs. Counts come straight from
    :class:`blive.runtime.ib_pipeline.IBMultiRunResult`;
    ``fill_rate_by_symbol`` / ``fsm_trace`` are derived conveniences so
    the file is directly analysable.
    """

    schema_version: int
    run_id: str
    recorded_at_utc: str
    strategy_id: str
    instruments: list[str]
    order_type: str
    max_bars: int
    nav_slice: str
    starting_cash: str
    final_equity: str
    rebalance_rows: int
    regime_flip_count: int
    submitted_count: int
    accepted_count: int
    filled_count: int
    canceled_count: int
    rejected_count: int
    breach_count: int
    cap_binding_2161_count: int
    submitted_by_symbol: dict[str, int]
    fills_by_symbol: dict[str, int]
    fill_rate_by_symbol: dict[str, float]
    observed_error_codes: dict[int, int]
    fsm_trace: dict[str, float]
    breaches: list[dict[str, str]]
    note: str = ""


def _fill_rate_by_symbol(
    *, submitted_by_symbol: dict[str, int], fills_by_symbol: dict[str, int]
) -> dict[str, float]:
    """Per-instrument fill-rate = filled / placed, over symbols that were
    placed at least once. Rounded to 4 dp."""
    rates: dict[str, float] = {}
    for symbol, placed in submitted_by_symbol.items():
        if placed <= 0:
            continue
        rates[symbol] = round(fills_by_symbol.get(symbol, 0) / placed, 4)
    return rates


def _fsm_trace(
    *,
    submitted: int,
    accepted: int,
    filled: int,
    canceled: int,
    rejected: int,
) -> dict[str, float]:
    """FSM-trace coverage ratios relative to submitted. Empty (all-zero)
    when nothing was submitted, to avoid divide-by-zero."""
    if submitted <= 0:
        return {
            "accepted_rate": 0.0,
            "filled_rate": 0.0,
            "canceled_rate": 0.0,
            "rejected_rate": 0.0,
        }
    return {
        "accepted_rate": round(accepted / submitted, 4),
        "filled_rate": round(filled / submitted, 4),
        "canceled_rate": round(canceled / submitted, 4),
        "rejected_rate": round(rejected / submitted, 4),
    }


def build_run_record(
    *,
    result: IBMultiRunResult,
    regime_flip_count: int,
    rebalance_rows: int,
    strategy_id: str,
    instruments: list[str],
    order_type: str,
    max_bars: int,
    nav_slice: Decimal,
    starting_cash: Decimal,
    run_id: str,
    recorded_at_utc: str,
    note: str = "",
) -> RunRecord:
    """Build a :class:`RunRecord` from a multi-instrument run outcome.

    Pure — ``run_id`` and ``recorded_at_utc`` are caller-supplied (the
    driver stamps them; tests pass fixed values). ``regime_flip_count``
    is computed by the driver from the capped target-weights via
    :func:`blive.runtime.signals.equity_leg_regime_flips`; ``rebalance_rows``
    is the number of target-weight rows replayed.
    """
    submitted_by_symbol = dict(result.submitted_by_symbol)
    fills_by_symbol = dict(result.fills_by_symbol)
    breaches = [
        {"check": b.check.value, "severity": b.severity.value, "detail": b.detail}
        for b in result.breaches
    ]
    return RunRecord(
        schema_version=SCHEMA_VERSION,
        run_id=run_id,
        recorded_at_utc=recorded_at_utc,
        strategy_id=strategy_id,
        instruments=list(instruments),
        order_type=order_type,
        max_bars=max_bars,
        nav_slice=str(nav_slice),
        starting_cash=str(starting_cash),
        final_equity=str(result.final_equity),
        rebalance_rows=rebalance_rows,
        regime_flip_count=regime_flip_count,
        submitted_count=result.submitted_count,
        accepted_count=result.accepted_count,
        filled_count=result.fills_count,
        canceled_count=result.canceled_count,
        rejected_count=result.rejected_count,
        breach_count=len(result.breaches),
        cap_binding_2161_count=result.observed_error_codes.get(_WARNING_2161, 0),
        submitted_by_symbol=submitted_by_symbol,
        fills_by_symbol=fills_by_symbol,
        fill_rate_by_symbol=_fill_rate_by_symbol(
            submitted_by_symbol=submitted_by_symbol, fills_by_symbol=fills_by_symbol
        ),
        observed_error_codes=dict(result.observed_error_codes),
        fsm_trace=_fsm_trace(
            submitted=result.submitted_count,
            accepted=result.accepted_count,
            filled=result.fills_count,
            canceled=result.canceled_count,
            rejected=result.rejected_count,
        ),
        breaches=breaches,
        note=note,
    )


def record_to_json_dict(record: RunRecord) -> dict[str, Any]:
    """Serialise a :class:`RunRecord` to a JSON-ready dict.

    All values are already JSON-native (str / int / float / list / dict);
    ``observed_error_codes``' int keys are coerced to strings by
    :func:`json.dumps` on write.
    """
    return asdict(record)


def default_window_path() -> Path:
    """Default M3.2 window results file: ``~/.blive/data/m3_2_window/runs.jsonl``."""
    return Path.home() / ".blive" / "data" / "m3_2_window" / "runs.jsonl"


def append_run_record(path: Path, record: RunRecord) -> Path:
    """Append ``record`` as one JSON line to ``path`` (creating parents).

    Returns the path written to. JSONL (one object per line) is the
    aggregation contract for the 10-day window — each run/day appends one
    row; downstream M3.3 analysis reads the file line by line.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record_to_json_dict(record), sort_keys=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    return path


__all__ = [
    "SCHEMA_VERSION",
    "RunRecord",
    "append_run_record",
    "build_run_record",
    "default_window_path",
    "record_to_json_dict",
]
