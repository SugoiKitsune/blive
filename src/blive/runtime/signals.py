"""Signal helpers that produce a ``position_series`` for the pipeline.

The M2-IB.5 paper test runs ``tkan_v4_momentum_timing`` 1× through
:func:`blive.runtime.ib_pipeline.run_ib_pipeline`, which takes a
pre-computed ``position_series: pd.Series[close_time_utc → 0|1]`` rather
than running the strategy's btest interpreter inline. This module
provides simple, deterministic stubs producing such series for end-to-end
paper testing without the real TKAN ``pred_cache.pkl`` artefact (per
operator's M2-IB.5 instruction: TKAN deferred until end-to-end paper
testing is done).

Stubs here are **not** strategies — they are signal generators useful
for exercising the full data → signal → portfolio → sizer → risk →
broker → fills → equity loop with realistic regime flips. When the real
TKAN artefact is wired (post-paper-test), the loader replaces the stub
with the production signal source; the pipeline contract stays the same.

Available stubs:

- :func:`sma_crossover_position`: long when ``close > SMA(window)``,
  flat otherwise. Warmup bars (insufficient history for SMA) → 0.

Phase-1 production signals (per [ADR-043](../../../docs/decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2)):

- :func:`triple_lev_sma_eligibility`: per-leg SMA-200 trend filter with
  hysteresis re-entry, producing a wide ``pd.DataFrame[date → ticker]``
  matching btest's ``ExternalFactor(per_instrument=True)`` contract for
  the ``triple_lev_sma_filter_dsl`` strategy. Bit-exact replica of the
  notebook's signal logic (``btest/research/Triple Leveraged ETF/triple_leveraged_etf_dsl.ipynb``).
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from blive.domain.types import Bar


def sma_crossover_position(
    bars: Sequence[Bar],
    *,
    sma_window: int = 50,
) -> pd.Series:
    """Return ``position_series`` indexed by each bar's ``close_time_utc``.

    Values are ``1`` when the bar's ``close`` is strictly above the
    trailing SMA of length ``sma_window`` (computed inclusive of the
    current bar — the pipeline reads ``position[t]`` after seeing
    ``bar[t]``, matching the typical "decide at close, place at next
    open" pattern for daily-frequency strategies). Values are ``0``
    during the warmup period (first ``sma_window - 1`` bars where the
    SMA is undefined) and whenever ``close <= SMA``.

    Empty ``bars`` returns an empty Series with a UTC datetime index.

    Output shape matches what
    :func:`blive.runtime.ib_pipeline.run_ib_pipeline` consumes: integer
    {0, 1} values, indexed by tz-aware UTC timestamps.
    """
    if sma_window < 2:
        raise ValueError(f"sma_window must be >= 2; got {sma_window}")

    if not bars:
        return pd.Series(
            data=pd.array([], dtype="int64"),
            index=pd.DatetimeIndex([], tz="UTC"),
            name="position",
        )

    closes = pd.Series(
        data=[float(b.close) for b in bars],
        index=pd.to_datetime([b.close_time_utc for b in bars], utc=True),
        name="close",
    )
    sma = closes.rolling(window=sma_window, min_periods=sma_window).mean()
    position = (closes > sma).astype("int64")
    # Warmup bars (sma is NaN) → already 0 due to NaN > x being False, but the
    # comparison sets them to False explicitly via the boolean cast. Ensure
    # the first sma_window-1 entries are exactly 0 for clarity.
    position.iloc[: sma_window - 1] = 0
    position.name = "position"
    return position


def triple_lev_sma_eligibility(
    *,
    qqq_closes: pd.Series,
    tlt_closes: pd.Series,
    sma_window: int = 200,
    exit_buffer: float = 0.0,
    enter_buffer: float = 0.05,
) -> pd.DataFrame:
    """Per-leg SMA-200 trend filter with hysteresis re-entry, returning a
    wide DataFrame matching btest's ``ExternalFactor(per_instrument=True)``
    contract for ``triple_lev_sma_filter_dsl``.

    Bit-exact replica of the signal block in
    ``btest/research/Triple Leveraged ETF/triple_leveraged_etf_dsl.ipynb``:

    - **TQQQ leg eligibility**: starts ``True``. Exits to ``False`` when
      ``qqq_close < qqq_sma * (1 + exit_buffer)``. Re-enters to ``True``
      when ``qqq_close > qqq_sma * (1 + enter_buffer)``. The
      asymmetric exit / enter thresholds prevent whipsaw — the leg has
      to clear the SMA by the enter buffer (default 5%) before
      re-engaging.
    - **TMF leg eligibility**: same logic against ``tlt_close`` and
      ``tlt_sma``.
    - **IEF eligibility**: ``NOT(tqqq_eligible AND tmf_eligible)`` —
      guarantees exactly 2 instruments are eligible at any point (per
      the notebook's "always 2 selected" invariant), so
      ``EqualWeight`` selectors give an exact 50/50 split when both
      risk-on legs are active, or 100% IEF only when both are filtered
      out. With one leg filtered, the active risk-on leg gets 50% and
      IEF gets 50%.

    Output columns are exactly ``["TQQQ", "TMF", "IEF"]`` in that
    order with float values ``0.0`` or ``1.0`` (the
    ``btest.ExternalFactor`` contract uses float, not bool, so
    downstream ``GreaterEqual(..., 0.5)`` produces the boolean mask).

    Inputs:

    - ``qqq_closes`` / ``tlt_closes``: pd.Series indexed by date
      (typically the bars' ``close_time_utc``); values are floats.
      The two series must share their index (caller aligns / forward-
      fills before calling).
    - ``sma_window``: SMA period (default 200, matches the notebook).
    - ``exit_buffer`` / ``enter_buffer``: hysteresis thresholds (default
      0.0 / 0.05, matches the notebook).

    Warmup behaviour: until ``sma_window`` bars are available for both
    series (SMA values exist), eligibility for all three columns is
    ``True`` (matches the notebook's "no signal yet → hold initial state"
    convention). Once SMA values come online, the state machine begins
    its hysteresis tracking from the warmup-end state of all-True.
    """
    if sma_window < 2:
        raise ValueError(f"sma_window must be >= 2; got {sma_window}")
    if not qqq_closes.index.equals(tlt_closes.index):
        raise ValueError(
            "qqq_closes and tlt_closes must share the same index; align/ffill before calling"
        )
    if len(qqq_closes) == 0:
        return pd.DataFrame(
            {
                "TQQQ": pd.Series(dtype=float),
                "TMF": pd.Series(dtype=float),
                "IEF": pd.Series(dtype=float),
            },
            index=qqq_closes.index,
        )

    qqq_sma = qqq_closes.rolling(window=sma_window, min_periods=sma_window).mean()
    tlt_sma = tlt_closes.rolling(window=sma_window, min_periods=sma_window).mean()

    tq_eligible: list[bool] = []
    tm_eligible: list[bool] = []
    tq_state = True
    tm_state = True

    for dt in qqq_closes.index:
        q = qqq_closes.loc[dt]
        t = tlt_closes.loc[dt]
        qs = qqq_sma.loc[dt]
        ts = tlt_sma.loc[dt]

        # Warmup: SMA undefined → hold initial all-True state.
        if pd.isna(qs) or pd.isna(q):
            tq_eligible.append(True)
            tm_eligible.append(True)
            continue

        # Hysteresis state machine for TQQQ leg (against QQQ closes).
        if tq_state and q < qs * (1.0 + exit_buffer):
            tq_state = False
        elif not tq_state and q > qs * (1.0 + enter_buffer):
            tq_state = True

        # Hysteresis state machine for TMF leg (against TLT closes).
        if tm_state and t < ts * (1.0 + exit_buffer):
            tm_state = False
        elif not tm_state and t > ts * (1.0 + enter_buffer):
            tm_state = True

        tq_eligible.append(tq_state)
        tm_eligible.append(tm_state)

    tq_arr = np.array(tq_eligible, dtype=bool)
    tm_arr = np.array(tm_eligible, dtype=bool)
    ief_arr = ~(tq_arr & tm_arr)  # NOT(both eligible) → IEF eligible

    return pd.DataFrame(
        {
            "TQQQ": tq_arr.astype(float),
            "TMF": tm_arr.astype(float),
            "IEF": ief_arr.astype(float),
        },
        index=qqq_closes.index,
    )


def eligibility_to_target_weights(eligibility: pd.DataFrame) -> pd.DataFrame:
    """Convert a wide eligibility DataFrame into target weights by row.

    Implements the ``LongShortPortfolio + MaskSelector + EqualWeight``
    semantics in pure DataFrame arithmetic for the specific A3 strategy
    shape (per [ADR-045](../../../docs/decisions/DECISIONS.md#adr-045--longshortportfolio-btest-dispatch-extends-adr-030)
    LongShortPortfolio dispatch + the strategy spec in
    ``btest/research/Triple Leveraged ETF/triple_leveraged_etf_dsl.ipynb``).
    For each row:

    - Count the number of eligible columns (values >= 0.5; matches the
      btest ``GreaterEqual(..., 0.5)`` boolean cast on the eligibility
      ``ExternalFactor``).
    - Each eligible column gets ``1 / count`` weight; non-eligible
      columns get ``0.0``.
    - Rows with zero eligible columns return all-zero (no position;
      caller decides what to do — the driver typically treats this as
      a flat-cash signal).

    Output columns match input columns in order; index unchanged.

    This is functionally equivalent to running btest's
    ``compute_target_weights_for_date()`` with this strategy's spec
    (LongShortPortfolio with empty short_book, target_gross_leverage=1.0,
    MaskSelector(sma_eligible) + EqualWeight()) for every row. A future
    blive iteration may swap to calling btest directly when strict
    parity becomes load-bearing or other LongShortPortfolio strategies
    introduce features beyond MaskSelector + EqualWeight (e.g., non-empty
    short books, factor-weighted books, sector-neutrality).

    Examples
    --------
    Eligibility row {TQQQ: 1.0, TMF: 1.0, IEF: 0.0} (both risk-on legs
    active, IEF parked):
        Target weights {TQQQ: 0.5, TMF: 0.5, IEF: 0.0}.

    Eligibility row {TQQQ: 1.0, TMF: 0.0, IEF: 1.0} (TMF filtered out,
    IEF engaged):
        Target weights {TQQQ: 0.5, TMF: 0.0, IEF: 0.5}.

    Eligibility row {TQQQ: 0.0, TMF: 0.0, IEF: 1.0} (both risk-on legs
    filtered, fully in IEF):
        Target weights {TQQQ: 0.0, TMF: 0.0, IEF: 1.0}.
    """
    if eligibility.empty:
        return eligibility.copy()
    bool_mask = eligibility >= 0.5
    counts = bool_mask.sum(axis=1)
    # Avoid divide-by-zero: rows with 0 eligible → all-zero target weights.
    safe_counts = counts.replace(0, 1)  # divisor of 1 produces 0.0 weights since mask is all False
    weights = bool_mask.astype(float).div(safe_counts, axis=0)
    return weights


def equity_leg_regime_flips(target_weights: pd.DataFrame, *, equity_leg: str) -> int:
    """Count regime flips of the equity leg across a target-weights frame.

    A *regime flip* is a transition in the sign-state of the equity leg's
    weight between consecutive rows — long (``> 0``) ↔ flat (``== 0``) ↔
    short (``< 0``). For the Phase 1 A3 strategy the equity leg (``QQL3``)
    is long / flat, so a flip counts each entry into or exit from the
    leveraged-equity position. This is the M3.2 "regime-flip count"
    metric (per [TASK_REGISTRY M3.2](../../../TASK_REGISTRY.md)) that
    contextualises the OQ-031 fill-rate evidence — a regime-flat window
    annotates the OQ-031 decision rather than waiting unbounded
    (TASK_REGISTRY G4 exit-criterion #3 / Q2 quality check).

    Returns ``0`` for an empty frame, a single-row frame, or an
    ``equity_leg`` column absent from ``target_weights`` (no observable
    equity-leg regime). Rows are taken in their existing order; the caller
    passes a time-ordered frame (the M3.2 driver passes the capped,
    bar-aligned ``target_weights``).
    """
    if equity_leg not in target_weights.columns:
        return 0
    col = target_weights[equity_leg].fillna(0.0)
    if len(col) < 2:
        return 0
    # Sign-state per row: +1 long / 0 flat / -1 short. Count transitions
    # between consecutive distinct states.
    states = np.sign(col.to_numpy(dtype=float)).astype(int)
    return int((states[1:] != states[:-1]).sum())


__all__ = [
    "sma_crossover_position",
    "triple_lev_sma_eligibility",
    "eligibility_to_target_weights",
    "equity_leg_regime_flips",
]
