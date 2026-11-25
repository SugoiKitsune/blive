---
id: INV-8
title: Metrics
status: DRAFT
owner: Claude
last_reviewed: 2026-06-05
version: 0.1
sources:
  - TASK_REGISTRY.md M3.2
  - blive M3.2 empirical-window results sink
depends_on:
  - INV-14 ib_error_codes (warning 2161 → cap_binding_2161_count)
  - INV-4 risk_checks (RiskEngine breaches → breach_count)
  - INV-13 order_state_transitions (FSM states → fsm_trace ratios)
referenced_by:
  - src/blive/runtime/m3_2_record.py (RunRecord — the metric row)
  - src/blive/runtime/ib_pipeline.py (IBMultiRunResult — counters)
  - src/blive/runtime/signals.py (equity_leg_regime_flips)
  - src/blive/adapters/ib/broker.py (observed_error_codes)
  - TASK_REGISTRY.md M3.2
---

# INV-8 — Metrics

## Purpose

Catalogue the metrics blive emits, with name, type, source (the code that
produces it), and meaning. The metric inventory is the SSOT that a future
machine-check (`test_metric_inventory_match`, [CONTEXT_PROTOCOL §7.2](../../CONTEXT_PROTOCOL.md);
M4+) asserts against code — every metric in code is here, every entry here
is in code.

## Scope

**This is the M3.2 stub-DRAFT** (per [TASK_REGISTRY M3.2](../../TASK_REGISTRY.md)):
it catalogues **only the M3.2 empirical-window metrics** captured by the
per-run results sink ([`src/blive/runtime/m3_2_record.py`](../../src/blive/runtime/m3_2_record.py),
one JSON row per run under `~/.blive/data/m3_2_window/runs.jsonl`). These
are the metrics the **M3.3 OQ-031 deployment decision** rests on.

**Out (deferred to M7):** the full Prometheus / Grafana observability
surface (metric *names in Prometheus exposition format*, labels, scrape
config, recording rules). M7 extends this stub to the full catalogue per
[Sketched M4+ M7](../../TASK_REGISTRY.md#sketched-m4-post-phase-1). The
M3.2 metrics here are **file-sink fields**, not yet Prometheus gauges /
counters — the "type" column names the *conceptual* metric kind so the M7
mapping is mechanical.

## M3.2 metric catalogue

The five milestone metrics (the [NEXT_PROMPT M3.2](../../NEXT_PROMPT.md)
"What M3.2 produces" list). Each is a field (or derived field) of
`RunRecord`:

| Metric | Kind | RunRecord field | Source | Meaning |
|--------|------|-----------------|--------|---------|
| **per-instrument fill-rate** | gauge (ratio) | `fill_rate_by_symbol` | `m3_2_record.build_run_record` from `submitted_by_symbol` (placed) ÷ `fills_by_symbol` (filled) | filled ÷ placed per IB symbol; the core OQ-031 signal for the QQL3 leg under the 2161 cap |
| **regime-flip count** | counter | `regime_flip_count` | `signals.equity_leg_regime_flips(target_weights, equity_leg="QQL3")` | equity-leg long ↔ flat ↔ short transitions over the replay window; contextualises fill-rate evidence (a regime-flat window annotates rather than blocks the OQ-031 decision — G4 Q2) |
| **warning-2161 cap-binding** | counter | `cap_binding_2161_count` | `IBBroker.observed_error_codes[2161]` → `IBMultiRunResult.observed_error_codes` (delta over the run) | occurrences of IB warning 2161 (PMA disruptive-orders price-cap) per [INV-14 v0.9](ib_error_codes.md); the structural-cap signal OQ-031 measures |
| **RiskEngine breach count** | counter | `breach_count` | `len(IBMultiRunResult.breaches)` (RiskEngine `approve`) | RC-08/09/10/12/13 breaches observed during the run per [INV-4](risk_checks.md) |
| **FSM-trace coverage** | gauge (ratios) | `fsm_trace` | `m3_2_record.build_run_record` from the FSM counters | `accepted_rate` / `filled_rate` / `canceled_rate` / `rejected_rate`, each ÷ `submitted_count` — SUBMITTED → ACCEPTED → FILLED / CANCELED / REJECTED coverage per [INV-13](order_state_transitions.md) |

### Supporting raw counters (the analysable denominators / numerators)

These back the derived metrics above and are stored on each row for direct
analysis:

| Field | Kind | Source | Meaning |
|-------|------|--------|---------|
| `submitted_count` | counter | `IBMultiRunResult.submitted_count` | orders placed on the wire this run |
| `accepted_count` | counter | `IBMultiRunResult.accepted_count` | orders that reached ACCEPTED (or beyond) — exact, from the drain loop's `reached_accepted` |
| `filled_count` | counter | `IBMultiRunResult.fills_count` | orders that reached FILLED |
| `canceled_count` | counter | `IBMultiRunResult.canceled_count` | orders that reached CANCELED (engine-cancel on timeout + IB 202) |
| `rejected_count` | counter | `IBMultiRunResult.rejected_count` | orders that reached REJECTED |
| `submitted_by_symbol` | counter map | `IBMultiRunResult.submitted_by_symbol` | per-IB-symbol placed count (fill-rate denominator) |
| `fills_by_symbol` | counter map | `IBMultiRunResult.fills_by_symbol` | per-IB-symbol filled count (fill-rate numerator) |
| `observed_error_codes` | counter map | `IBBroker.observed_error_codes` | full order-related IB error/warning histogram this run; `cap_binding_2161_count` reads 2161 out of it; also feeds M3.5's INV-14 catalogue-extension |
| `rebalance_rows` | gauge | driver (`len(target_weights_capped)`) | number of target-weight rows replayed (window length context) |
| `final_equity` | gauge | `IBMultiRunResult.final_equity` | mark-to-market equity at the last rebalance (string-encoded Decimal) |

### Row metadata (provenance, not metrics)

`schema_version`, `run_id`, `recorded_at_utc`, `strategy_id`, `instruments`,
`order_type`, `max_bars`, `nav_slice`, `starting_cash`, `note` — carried on
each row so the 10-day window is self-describing and the M3.3 decision is
auditable (data → option chosen → why). `note` annotates regime-flat
windows per the G4 Q2 quality check.

## Sink contract

One `RunRecord` is serialised as one JSON line (`json.dumps(..., sort_keys=True)`)
and appended to `~/.blive/data/m3_2_window/runs.jsonl` (override via
`--record-path`; suppress via `--no-record`). JSONL — one object per line —
is the 10-day aggregation contract: each operator-driven run/day appends
one row; M3.3 reads the file line by line. `schema_version` (currently
`1`, [`m3_2_record.SCHEMA_VERSION`](../../src/blive/runtime/m3_2_record.py))
distinguishes row generations if the shape changes.

## Cross-References

- [INV-14](ib_error_codes.md) — warning 2161 (the `cap_binding_2161_count` source).
- [INV-4](risk_checks.md) — RiskEngine checks (the `breach_count` source).
- [INV-13](order_state_transitions.md) — FSM states (the `fsm_trace` semantics).
- [INV-9](alerts.md) — alerts (companion stub; the breach metric has an alert twin).
- [`src/blive/runtime/m3_2_record.py`](../../src/blive/runtime/m3_2_record.py) — the `RunRecord` schema + builder.
- [TASK_REGISTRY M3.2](../../TASK_REGISTRY.md) — the milestone this stub serves.

## Open Questions

None blocking. The Prometheus exposition mapping (metric names, labels,
HELP text, scrape config) is deferred to M7 with the full observability
stack; this stub stays file-sink-only through Phase 1.

## Changelog

- **v0.1 (2026-06-05 / M3.2)** — MISSING → DRAFT. Stub catalogue of the
  five M3.2 empirical-window metrics (per-instrument fill-rate, regime-flip
  count, warning-2161 cap-binding, RiskEngine breach count, FSM-trace
  coverage) + their supporting raw counters + row metadata, all sourced
  from the per-run results sink (`RunRecord` in
  `src/blive/runtime/m3_2_record.py`). Full Prometheus / Grafana surface
  deferred to M7.
