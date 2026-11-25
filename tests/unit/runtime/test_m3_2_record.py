"""Tests for the M3.2 empirical-window results sink.

Covers :mod:`blive.runtime.m3_2_record`: the pure ``build_run_record``
builder (per-instrument fill-rate, FSM-trace ratios, 2161 cap-binding
extraction, breach mapping), JSON serialisation, and the JSONL append
round-trip. The builder is pure (caller supplies ``run_id`` +
``recorded_at_utc``) so every assertion is deterministic.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from blive.domain.events import RiskBreach, RiskBreachSeverity, RiskCheckCode
from blive.runtime.ib_pipeline import IBMultiRunResult
from blive.runtime.m3_2_record import (
    SCHEMA_VERSION,
    RunRecord,
    append_run_record,
    build_run_record,
    record_to_json_dict,
)


def _make_result() -> IBMultiRunResult:
    """A representative multi-instrument outcome for a cap-bound QQL3 leg."""
    result = IBMultiRunResult()
    result.submitted_count = 10
    result.accepted_count = 8
    result.fills_count = 3
    result.canceled_count = 5
    result.rejected_count = 2
    result.fills_by_symbol = {"QQL3": 1, "IBTM": 2}
    result.submitted_by_symbol = {"QQL3": 5, "IBTM": 3, "IBTL": 2}
    result.observed_error_codes = {2161: 4, 110: 1}
    result.final_equity = Decimal("100123.45")
    return result


def _build(result: IBMultiRunResult, *, note: str = "") -> RunRecord:
    return build_run_record(
        result=result,
        regime_flip_count=2,
        rebalance_rows=5,
        strategy_id="triple_lev_sma_filter_dsl",
        instruments=["QQL3", "IBTL", "IBTM"],
        order_type="MKT",
        max_bars=5,
        nav_slice=Decimal("0.05"),
        starting_cash=Decimal("100000"),
        run_id="run-abc",
        recorded_at_utc="2026-06-05T10:00:00+00:00",
        note=note,
    )


def test_build_run_record_core_counts() -> None:
    record = _build(_make_result())

    assert record.schema_version == SCHEMA_VERSION
    assert record.run_id == "run-abc"
    assert record.recorded_at_utc == "2026-06-05T10:00:00+00:00"
    assert record.strategy_id == "triple_lev_sma_filter_dsl"
    assert record.instruments == ["QQL3", "IBTL", "IBTM"]
    assert record.order_type == "MKT"
    assert record.rebalance_rows == 5
    assert record.regime_flip_count == 2
    assert record.submitted_count == 10
    assert record.accepted_count == 8
    assert record.filled_count == 3
    assert record.canceled_count == 5
    assert record.rejected_count == 2
    assert record.breach_count == 0
    # Decimals serialised as strings for exactness.
    assert record.nav_slice == "0.05"
    assert record.starting_cash == "100000"
    assert record.final_equity == "100123.45"


def test_cap_binding_2161_extracted_from_observed_codes() -> None:
    record = _build(_make_result())
    assert record.cap_binding_2161_count == 4
    assert record.observed_error_codes == {2161: 4, 110: 1}


def test_cap_binding_zero_when_no_2161() -> None:
    result = _make_result()
    result.observed_error_codes = {110: 1}
    record = _build(result)
    assert record.cap_binding_2161_count == 0


def test_fill_rate_by_symbol() -> None:
    record = _build(_make_result())
    # QQL3: 1/5 = 0.2; IBTM: 2/3 = 0.6667; IBTL: 0/2 = 0.0 (placed, never filled).
    assert record.fill_rate_by_symbol == {"QQL3": 0.2, "IBTM": 0.6667, "IBTL": 0.0}


def test_fsm_trace_ratios() -> None:
    record = _build(_make_result())
    assert record.fsm_trace == {
        "accepted_rate": 0.8,
        "filled_rate": 0.3,
        "canceled_rate": 0.5,
        "rejected_rate": 0.2,
    }


def test_zero_submitted_yields_safe_ratios_and_empty_fill_rate() -> None:
    record = _build(IBMultiRunResult())  # all-zero default
    assert record.submitted_count == 0
    assert record.fill_rate_by_symbol == {}
    assert record.fsm_trace == {
        "accepted_rate": 0.0,
        "filled_rate": 0.0,
        "canceled_rate": 0.0,
        "rejected_rate": 0.0,
    }


def test_breaches_mapped_to_dicts() -> None:
    result = _make_result()
    result.breaches = [
        RiskBreach(
            strategy_id="triple_lev_sma_filter_dsl",
            check=RiskCheckCode.RC_13,
            severity=RiskBreachSeverity.BLOCK,
            detail="kill switch armed",
            time_utc=datetime(2026, 6, 5, 10, 0, tzinfo=timezone.utc),
        )
    ]
    record = _build(result)
    assert record.breach_count == 1
    assert record.breaches == [
        {"check": "RC-13", "severity": "block", "detail": "kill switch armed"}
    ]


def test_note_is_carried() -> None:
    record = _build(_make_result(), note="regime-flat window")
    assert record.note == "regime-flat window"


def test_record_to_json_dict_is_json_serialisable() -> None:
    record = _build(_make_result())
    payload = record_to_json_dict(record)
    text = json.dumps(payload, sort_keys=True)
    reloaded = json.loads(text)
    assert reloaded["final_equity"] == "100123.45"
    assert reloaded["nav_slice"] == "0.05"
    # int error-code keys become JSON string keys.
    assert reloaded["observed_error_codes"]["2161"] == 4


def test_append_run_record_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "runs.jsonl"
    r1 = _build(_make_result(), note="day-1")
    r2 = _build(_make_result(), note="day-2")

    written = append_run_record(path, r1)
    append_run_record(path, r2)

    assert written == path
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["note"] == "day-1"
    assert second["note"] == "day-2"
    assert first["cap_binding_2161_count"] == 4
    assert first["fill_rate_by_symbol"]["QQL3"] == 0.2


def test_append_run_record_creates_parent_dirs(tmp_path: Path) -> None:
    path = tmp_path / "m3_2_window" / "nested" / "runs.jsonl"
    append_run_record(path, _build(_make_result()))
    assert path.is_file()
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1
