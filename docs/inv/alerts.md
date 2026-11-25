---
id: INV-9
title: Alerts
status: DRAFT
owner: Claude
last_reviewed: 2026-06-05
version: 0.1
sources:
  - TASK_REGISTRY.md M3.2
  - blive M3.2 paper-mode alert surface
depends_on:
  - INV-4 risk_checks (breach severities + on-breach actions)
  - INV-8 metrics (the breach-count metric twin)
  - INV-5 domain_events (risk.breach event topic)
referenced_by:
  - src/blive/risk/checks.py (BREACH_TOPIC, RiskEngine breaches, KillSwitch)
  - src/blive/runtime/ib_pipeline.py (alert.send per breach)
  - src/blive/adapters/alert/log.py (LogAlert — M3.2 channel)
  - TASK_REGISTRY.md M3.2
---

# INV-9 — Alerts

## Purpose

Catalogue the alerts blive raises, with name, trigger condition, severity,
channel, and runbook link. An alert is an *operator-facing* signal that
something needs attention — distinct from a [metric](metrics.md) (a measured
value) and a [domain event](domain_events.md) (an internal state change),
though an alert is usually *driven by* an event crossing a threshold.

## Scope

**This is the M3.2 stub-DRAFT** (per [TASK_REGISTRY M3.2](../../TASK_REGISTRY.md)):
it catalogues **only the M3.2 paper-mode alerts** — the kill-switch /
RiskEngine-breach surface exercised by the empirical-window runs. During
M3.2 the only alert channel is [`LogAlert`](../../src/blive/adapters/alert/log.py)
(structured log line via the `AlertPort`); the RiskEngine calls
`alert.send(severity, topic, detail)` once per breach inside the pipeline
loop ([`run_ib_multi_pipeline`](../../src/blive/runtime/ib_pipeline.py)).

**Out (deferred to M7):** the full alerting stack — Prometheus Alertmanager
routing, severity-to-channel mapping (email / SMS / push), de-duplication /
grouping, runbook automation. M7 extends this stub per
[Sketched M4+ M7](../../TASK_REGISTRY.md#sketched-m4-post-phase-1).

## M3.2 alert catalogue

| Alert | Trigger condition | Severity | M3.2 channel | Runbook |
|-------|-------------------|----------|--------------|---------|
| **RiskEngine breach** (`risk.breach/{RC}`) | RiskEngine `approve()` returns one or more breaches for a sized order — any of RC-08 (stale data) / RC-09 (market hours) / RC-10 (price sanity) / RC-12 (artefact freshness) / RC-13 (kill-switch) per [INV-4](risk_checks.md) | per breach: BLOCK → HIGH, SCALE → MEDIUM, WARN → LOW (`RiskBreach.alert_severity()`) | `LogAlert` (one line per breach; topic `risk.breach/{check}`) | (M7 — runbook entry per RC) |
| **Kill-switch armed** (`risk.breach/RC-13`) | the RC-13 check fires because `KillSwitch.armed` is true; **every** sized order is blocked while armed, so the alert repeats per candidate order per rebalance | HIGH (RC-13 is BLOCK) | `LogAlert` (detail `kill-switch armed: {reason}`) | (M7 — kill-switch recovery runbook) |

Notes:

- The **breach metric twin** is `breach_count` in [INV-8](metrics.md):
  the metric counts breaches per run; the alert fires per breach in real
  time. Same underlying `RiskBreach`; metric is the aggregate, alert is the
  signal.
- The kill-switch alert is a **special case** of the RiskEngine-breach
  alert (RC-13), called out separately because it is the milestone's named
  "kill-switch alert" and because its BLOCK severity halts all submission —
  the highest-consequence M3.2 alert.
- M3.2 does **not** alert on warning 2161 (cap-binding) — it is captured as
  a [metric](metrics.md) (`cap_binding_2161_count`), not an operator alert,
  because the cap is a *structural, expected* characteristic of the QQL3
  leg under OQ-031, not an exceptional condition. Whether sustained cap
  binding *becomes* an alert is an OQ-031 / M7 question, not an M3.2 one.

## Cross-References

- [INV-4](risk_checks.md) — the risk checks + severities + on-breach actions that drive these alerts.
- [INV-8](metrics.md) — the metric counterpart (`breach_count`).
- [INV-5](domain_events.md) — the `risk.breach` domain-event topic.
- [`src/blive/risk/checks.py`](../../src/blive/risk/checks.py) — `BREACH_TOPIC`, `RiskEngine`, `KillSwitch`.
- [`src/blive/adapters/alert/log.py`](../../src/blive/adapters/alert/log.py) — `LogAlert`, the M3.2 channel.
- [TASK_REGISTRY M3.2](../../TASK_REGISTRY.md) — the milestone this stub serves.

## Open Questions

None blocking. Channel routing (which severities go to which operator
channel) and whether sustained 2161 cap-binding warrants an alert are M7 /
OQ-031 questions, deferred with the full alerting stack.

## Changelog

- **v0.1 (2026-06-05 / M3.2)** — MISSING → DRAFT. Stub catalogue of the two
  M3.2 paper-mode alerts (RiskEngine breach `risk.breach/{RC}`; kill-switch
  armed `risk.breach/RC-13`), both on the `LogAlert` channel. Full
  alerting stack (Alertmanager, channel routing, runbooks) deferred to M7.
