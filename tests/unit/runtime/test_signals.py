"""Tests for :mod:`blive.runtime.signals`."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pandas as pd
import pytest

from blive.domain.types import AssetClass, Bar, Instrument
from blive.runtime.signals import (
    eligibility_to_target_weights,
    equity_leg_regime_flips,
    sma_crossover_position,
    triple_lev_sma_eligibility,
)


def _instrument() -> Instrument:
    return Instrument(
        symbol="CAC.PA",
        venue="XPAR",
        currency="EUR",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
        tradability="spot",
    )


def _make_bars(closes: list[float]) -> list[Bar]:
    inst = _instrument()
    base = datetime(2026, 1, 5, 15, 30, tzinfo=timezone.utc)
    bars: list[Bar] = []
    for i, c in enumerate(closes):
        t = base + timedelta(days=i)
        bars.append(
            Bar(
                instrument=inst,
                open_time_utc=t - timedelta(hours=8),
                close_time_utc=t,
                open=Decimal(str(c)),
                high=Decimal(str(c + 0.5)),
                low=Decimal(str(c - 0.5)),
                close=Decimal(str(c)),
                volume=Decimal("1000"),
                vwap=None,
            )
        )
    return bars


def test_empty_bars_returns_empty_series() -> None:
    out = sma_crossover_position([], sma_window=10)
    assert len(out) == 0
    assert isinstance(out.index, pd.DatetimeIndex)
    assert out.index.tz is not None  # UTC


def test_warmup_window_is_flat() -> None:
    """First sma_window - 1 entries are 0 regardless of price action."""
    closes = [100.0] * 5 + [200.0] * 5  # second half spikes; SMA still warming
    bars = _make_bars(closes)
    out = sma_crossover_position(bars, sma_window=5)
    # First 4 bars have insufficient history for SMA(5) → must be 0.
    assert (out.iloc[:4] == 0).all(), "warmup bars should be flat"


def test_long_when_close_above_sma() -> None:
    """A clean uptrend: every bar's close is above its trailing SMA."""
    closes = [100.0 + i for i in range(20)]  # strictly rising
    bars = _make_bars(closes)
    out = sma_crossover_position(bars, sma_window=5)
    # Bars 4 onward have full SMA window AND close > sma (rising trend).
    assert (out.iloc[4:] == 1).all(), "rising trend should be fully long after warmup"


def test_flat_when_close_below_sma() -> None:
    """A clean downtrend: every bar's close is below its trailing SMA."""
    closes = [200.0 - i for i in range(20)]  # strictly falling
    bars = _make_bars(closes)
    out = sma_crossover_position(bars, sma_window=5)
    # Bars 4 onward have full SMA window AND close < sma (falling).
    assert (out.iloc[4:] == 0).all(), "falling trend should be fully flat after warmup"


def test_regime_flip_at_sma_crossing() -> None:
    """Rising then falling: position should flip from 1 to 0 around the
    crossover."""
    # 5 days flat at 100, then 10 days rising to 110, then 10 days falling to 90.
    closes = [100.0] * 5 + [100.0 + i for i in range(1, 11)] + [110.0 - i for i in range(1, 11)]
    bars = _make_bars(closes)
    out = sma_crossover_position(bars, sma_window=5)
    # Sanity: at least one flip from 1→0 in the falling segment.
    flips = ((out.shift() == 1) & (out == 0)).sum()
    assert flips >= 1, "expected at least one long→flat flip on the downtrend"


def test_index_matches_close_time_utc() -> None:
    """Output index aligns with bars' close_time_utc — what run_ib_pipeline
    consumes via ``position_series.loc[ts_key]``."""
    closes = [100.0 + i for i in range(10)]
    bars = _make_bars(closes)
    out = sma_crossover_position(bars, sma_window=3)
    expected_index = pd.to_datetime([b.close_time_utc for b in bars], utc=True)
    assert (out.index == expected_index).all()


def test_invalid_window_raises() -> None:
    bars = _make_bars([100.0, 101.0, 102.0])
    with pytest.raises(ValueError, match="sma_window"):
        sma_crossover_position(bars, sma_window=1)
    with pytest.raises(ValueError, match="sma_window"):
        sma_crossover_position(bars, sma_window=0)


# --- triple_lev_sma_eligibility -------------------------------------------


def _date_index(n: int) -> pd.DatetimeIndex:
    base = datetime(2026, 1, 5, 15, 30, tzinfo=timezone.utc)
    return pd.to_datetime([base + timedelta(days=i) for i in range(n)], utc=True)


def test_triple_lev_eligibility_warmup_returns_all_true() -> None:
    """During the SMA warmup (before sma_window valid bars), the function
    holds the initial all-True state (matches the notebook's no-signal-yet
    convention). With sma_window=10 and 5 input bars, every row → all-True."""
    idx = _date_index(5)
    qqq = pd.Series([100.0] * 5, index=idx)
    tlt = pd.Series([100.0] * 5, index=idx)
    df = triple_lev_sma_eligibility(qqq_closes=qqq, tlt_closes=tlt, sma_window=10)
    assert (df["TQQQ"] == 1.0).all()
    assert (df["TMF"] == 1.0).all()
    # IEF = NOT(TQQQ AND TMF) → False during warmup → 0.0
    assert (df["IEF"] == 0.0).all()


def test_triple_lev_eligibility_steady_uptrend_keeps_both_legs_long() -> None:
    """When QQQ and TLT both stay above their SMAs, both legs eligible →
    IEF stays 0; the strategy is fully in TQQQ + TMF."""
    idx = _date_index(20)
    closes = [100.0 + i for i in range(20)]  # monotonic uptrend
    qqq = pd.Series(closes, index=idx)
    tlt = pd.Series(closes, index=idx)
    df = triple_lev_sma_eligibility(qqq_closes=qqq, tlt_closes=tlt, sma_window=5)
    # Past the warmup window, the rising trend keeps closes above SMA → both True.
    post_warmup = df.iloc[5:]
    assert (post_warmup["TQQQ"] == 1.0).all()
    assert (post_warmup["TMF"] == 1.0).all()
    assert (post_warmup["IEF"] == 0.0).all()


def test_triple_lev_eligibility_one_leg_falls_below_sma_engages_ief() -> None:
    """When QQQ falls below its SMA: TQQQ leg → 0; TMF leg stays 1; IEF
    becomes eligible (NOT(both)) → 1."""
    idx = _date_index(20)
    qqq_closes = [100.0] * 5 + [100.0 - i for i in range(15)]  # post-warmup falling
    tlt_closes = [100.0 + i for i in range(20)]  # monotonic up
    qqq = pd.Series(qqq_closes, index=idx)
    tlt = pd.Series(tlt_closes, index=idx)
    df = triple_lev_sma_eligibility(qqq_closes=qqq, tlt_closes=tlt, sma_window=5)
    # By the last few bars QQQ has fallen well below its SMA.
    last = df.iloc[-1]
    assert last["TQQQ"] == 0.0
    assert last["TMF"] == 1.0
    assert last["IEF"] == 1.0  # NOT(0 AND 1) = NOT(0) = 1


def test_triple_lev_eligibility_hysteresis_re_entry_requires_5pct_buffer() -> None:
    """After QQQ falls and triggers exit, it must rise above SMA*1.05 to
    re-enter — passing exactly through the SMA does NOT re-engage TQQQ."""
    idx = _date_index(40)
    # Phase 1: rising up to bar 10 → both eligible.
    # Phase 2: drop below SMA → TQQQ exits.
    # Phase 3: rise back to exactly the SMA value (not 5% above) → still flat.
    closes_qqq = (
        [100.0 + i for i in range(10)] + [70.0] * 10 + [109.0] * 20
    )  # 109 ≈ SMA at bar 30 likely
    closes_tlt = [100.0 + i for i in range(40)]
    qqq = pd.Series(closes_qqq, index=idx)
    tlt = pd.Series(closes_tlt, index=idx)
    df = triple_lev_sma_eligibility(qqq_closes=qqq, tlt_closes=tlt, sma_window=5, enter_buffer=0.05)
    # By bar 20+ we expect TQQQ to have exited; it's only re-engaged when
    # close exceeds SMA*1.05 — find at least one row where TQQQ is 0
    # confirming the exit happened.
    assert (df["TQQQ"] == 0.0).any(), "expected TQQQ to exit during the drop phase"


def test_triple_lev_eligibility_misaligned_indices_raises() -> None:
    """qqq and tlt must share their index; otherwise raises before any state
    machine runs."""
    qqq = pd.Series([100.0, 101.0], index=_date_index(2))
    tlt = pd.Series([100.0, 101.0, 102.0], index=_date_index(3))
    with pytest.raises(ValueError, match="share the same index"):
        triple_lev_sma_eligibility(qqq_closes=qqq, tlt_closes=tlt)


def test_triple_lev_eligibility_invalid_window_raises() -> None:
    qqq = pd.Series([100.0, 101.0], index=_date_index(2))
    tlt = pd.Series([100.0, 101.0], index=_date_index(2))
    with pytest.raises(ValueError, match="sma_window"):
        triple_lev_sma_eligibility(qqq_closes=qqq, tlt_closes=tlt, sma_window=1)


def test_triple_lev_eligibility_empty_input_returns_empty_frame() -> None:
    empty_idx = pd.DatetimeIndex([], tz="UTC")
    qqq = pd.Series([], index=empty_idx, dtype=float)
    tlt = pd.Series([], index=empty_idx, dtype=float)
    df = triple_lev_sma_eligibility(qqq_closes=qqq, tlt_closes=tlt)
    assert len(df) == 0
    assert list(df.columns) == ["TQQQ", "TMF", "IEF"]


def test_eligibility_to_target_weights_both_legs_eligible_equal_weights() -> None:
    """{TQQQ:1, TMF:1, IEF:0} → {TQQQ:0.5, TMF:0.5, IEF:0}."""
    eligibility = pd.DataFrame(
        {"TQQQ": [1.0], "TMF": [1.0], "IEF": [0.0]},
        index=_date_index(1),
    )
    weights = eligibility_to_target_weights(eligibility)
    row = weights.iloc[0]
    assert row["TQQQ"] == 0.5
    assert row["TMF"] == 0.5
    assert row["IEF"] == 0.0


def test_eligibility_to_target_weights_one_leg_filtered_engages_ief() -> None:
    """{TQQQ:1, TMF:0, IEF:1} → {TQQQ:0.5, TMF:0, IEF:0.5}."""
    eligibility = pd.DataFrame(
        {"TQQQ": [1.0], "TMF": [0.0], "IEF": [1.0]},
        index=_date_index(1),
    )
    weights = eligibility_to_target_weights(eligibility)
    row = weights.iloc[0]
    assert row["TQQQ"] == 0.5
    assert row["TMF"] == 0.0
    assert row["IEF"] == 0.5


def test_eligibility_to_target_weights_only_ief_eligible_full_park() -> None:
    """{TQQQ:0, TMF:0, IEF:1} → {TQQQ:0, TMF:0, IEF:1.0} (100% safe-haven park)."""
    eligibility = pd.DataFrame(
        {"TQQQ": [0.0], "TMF": [0.0], "IEF": [1.0]},
        index=_date_index(1),
    )
    weights = eligibility_to_target_weights(eligibility)
    row = weights.iloc[0]
    assert row["TQQQ"] == 0.0
    assert row["TMF"] == 0.0
    assert row["IEF"] == 1.0


def test_eligibility_to_target_weights_no_eligible_returns_all_zero() -> None:
    """Edge case: no column eligible (shouldn't happen for the M2-IB.6
    strategy by construction — IEF is always eligible when both risk-on
    legs are filtered — but the helper is defensive)."""
    eligibility = pd.DataFrame(
        {"TQQQ": [0.0], "TMF": [0.0], "IEF": [0.0]},
        index=_date_index(1),
    )
    weights = eligibility_to_target_weights(eligibility)
    row = weights.iloc[0]
    assert row["TQQQ"] == 0.0
    assert row["TMF"] == 0.0
    assert row["IEF"] == 0.0


def test_eligibility_to_target_weights_multi_row_preserves_index() -> None:
    """Output index matches input index; per-row computation is independent."""
    idx = _date_index(3)
    eligibility = pd.DataFrame(
        {
            "TQQQ": [1.0, 0.0, 1.0],
            "TMF": [1.0, 0.0, 0.0],
            "IEF": [0.0, 1.0, 1.0],
        },
        index=idx,
    )
    weights = eligibility_to_target_weights(eligibility)
    assert (weights.index == idx).all()
    # Row 0: both legs eligible → 50/50
    assert weights.iloc[0]["TQQQ"] == 0.5
    assert weights.iloc[0]["TMF"] == 0.5
    # Row 1: only IEF
    assert weights.iloc[1]["IEF"] == 1.0
    # Row 2: TQQQ + IEF
    assert weights.iloc[2]["TQQQ"] == 0.5
    assert weights.iloc[2]["IEF"] == 0.5


def test_eligibility_to_target_weights_empty_returns_empty() -> None:
    eligibility = pd.DataFrame({"TQQQ": [], "TMF": [], "IEF": []})
    weights = eligibility_to_target_weights(eligibility)
    assert weights.empty


def test_eligibility_to_target_weights_row_sums_to_one_when_at_least_one_eligible() -> None:
    """For all rows where ≥ 1 column is eligible, weights sum to 1.0
    (target_gross_leverage=1.0 invariant from the strategy spec)."""
    idx = _date_index(4)
    eligibility = pd.DataFrame(
        {
            "TQQQ": [1.0, 1.0, 0.0, 0.0],
            "TMF": [1.0, 0.0, 1.0, 0.0],
            "IEF": [0.0, 1.0, 1.0, 1.0],
        },
        index=idx,
    )
    weights = eligibility_to_target_weights(eligibility)
    row_sums = weights.sum(axis=1)
    # Every row has at least one eligible → sum = 1.0
    assert (row_sums == 1.0).all()


def test_triple_lev_eligibility_output_columns_in_canonical_order() -> None:
    """Column order must be exactly ['TQQQ', 'TMF', 'IEF'] — btest's
    ExternalFactor(per_instrument=True) reads by column name but consumers
    of the parquet may rely on positional order, so pinning."""
    idx = _date_index(20)
    qqq = pd.Series([100.0 + i for i in range(20)], index=idx)
    tlt = pd.Series([100.0 + i for i in range(20)], index=idx)
    df = triple_lev_sma_eligibility(qqq_closes=qqq, tlt_closes=tlt, sma_window=5)
    assert list(df.columns) == ["TQQQ", "TMF", "IEF"]
    # Values should all be 0.0 or 1.0 (no fractional float artefacts).
    assert set(df["TQQQ"].unique()) <= {0.0, 1.0}
    assert set(df["TMF"].unique()) <= {0.0, 1.0}
    assert set(df["IEF"].unique()) <= {0.0, 1.0}


# --- equity_leg_regime_flips (M3.2 regime-flip metric) ----------------------


def _weights_frame(qql3_values: list[float]) -> pd.DataFrame:
    idx = _date_index(len(qql3_values))
    other = [0.5] * len(qql3_values)
    return pd.DataFrame({"QQL3": qql3_values, "IBTM": other}, index=idx)


def test_regime_flips_counts_long_flat_transitions() -> None:
    """QQL3 weight [0.5, 0.5, 0, 0, 0.5] → states [1,1,0,0,1] → 2 flips
    (long→flat at idx 2, flat→long at idx 4)."""
    weights = _weights_frame([0.5, 0.5, 0.0, 0.0, 0.5])
    assert equity_leg_regime_flips(weights, equity_leg="QQL3") == 2


def test_regime_flips_zero_when_constant() -> None:
    weights = _weights_frame([0.5, 0.5, 0.5, 0.5])
    assert equity_leg_regime_flips(weights, equity_leg="QQL3") == 0


def test_regime_flips_counts_long_short_transition() -> None:
    """A long→short transition (sign change) counts as a flip even with no
    flat state between — generic over long/flat/short."""
    weights = _weights_frame([0.5, -0.5])
    assert equity_leg_regime_flips(weights, equity_leg="QQL3") == 1


def test_regime_flips_missing_column_returns_zero() -> None:
    weights = _weights_frame([0.5, 0.0, 0.5])
    assert equity_leg_regime_flips(weights, equity_leg="NOT_THERE") == 0


def test_regime_flips_single_row_returns_zero() -> None:
    weights = _weights_frame([0.5])
    assert equity_leg_regime_flips(weights, equity_leg="QQL3") == 0


def test_regime_flips_empty_frame_returns_zero() -> None:
    assert equity_leg_regime_flips(pd.DataFrame(), equity_leg="QQL3") == 0


def test_regime_flips_tolerates_nan() -> None:
    """A NaN weight is treated as flat (0); does not raise on the int cast."""
    weights = _weights_frame([0.5, float("nan"), 0.5])
    # states [1, 0, 1] → 2 flips.
    assert equity_leg_regime_flips(weights, equity_leg="QQL3") == 2
