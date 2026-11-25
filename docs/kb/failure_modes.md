---
id: KB-7
title: Failure Modes
status: DRAFT
owner: Claude
last_reviewed: 2026-06-05
version: 0.1
sources:
  - REQUIREMENTS.md §13.2 (failure modes)
  - REQUIREMENTS.md §5.7 (reconciliation)
  - M3.5 disconnect/reconnect chaos drill (scripts/probe_ib_reconnect.py, 2026-06-05)
  - ADR-040 (Phase 1 deployment: Windows host, daily TWS restart, operator-managed relogin)
depends_on:
  - REQUIREMENTS
  - INV-14
  - KB-8
referenced_by:
  - TASK_REGISTRY.md M3.5
---

# KB-7 — Failure Modes

## Purpose

Catalogue each failure mode the engine must withstand, the **required engine
response**, the **observed blive behaviour**, and the **chaos-test fixture**
that exercises it. Expands [REQUIREMENTS §13.2](../../REQUIREMENTS.md).

## Scope

**M3.5 stub (this version).** Only the failure modes **empirically drilled at
M3.5** are catalogued — currently the IB Gateway drop / daily restart (FM-1).
The full catalogue (market-data gaps, partial-fill / cancel races, clock skew,
artefact staleness, kill-switch paths, persistence-layer failures, etc.) is
**M4/M5** work and extends this stub (per [TASK_REGISTRY Sketched M4+](../../TASK_REGISTRY.md#sketched-m4-post-phase-1) — M5 grows KB-7 from this stub).

**Out:** failure modes not yet drilled; their required-response design (lives in
REQUIREMENTS / DESIGN until drilled).

## Content

### FM-1 — Unexpected IB Gateway drop / daily restart

**Trigger.** The daily 23:45 ET TWS/Gateway restart ([ADR-040](../decisions/DECISIONS.md#adr-040--phase-1-deployment-target-windows-host-with-native-ib-gateway), operator-managed manual relogin), or any connectivity loss (network blip, Gateway crash, host sleep).

**Required engine response** ([REQUIREMENTS §5.7](../../REQUIREMENTS.md#57-reconciliation)). Detect the drop; **pause order submission**; reconnect (with backoff); on resume **reconcile** open orders + positions (`reqAllOpenOrders` + `reqPositions`) against local state; then resume.

**Observed blive behaviour (M3.5 drill, 2026-06-05 — `scripts/probe_ib_reconnect.py`).**

1. **The drop is NOT auto-detected by the broker.** After the operator stopped the Gateway, `IBBroker.is_connected` (a cached bool) stayed **stale-`True`**, while `IBClient.is_connected` (→ `ib.isConnected()`) correctly went `False`. `IBBroker` has **no `ib.disconnectedEvent` subscription**, so on an *unexpected* drop it neither flips its flag nor emits `ConnectionStatus(connected=False)` — those fire only on an explicit `disconnect()`. ib_async logged `Peer closed connection`, but nothing in blive reacted.
2. **Recovery requires `disconnect()` then `connect()`.** `connect()` is a no-op while the cached flag is stale-`True`, so the stale flag must be reset via `disconnect()` (best-effort; safe on a dead socket) first. The drill's external loop did this; the broker does not do it itself.
3. **The restart raised two real transients before the reconnect succeeded (~10 s later):**
   - **IB error 10141** — `Paper trading disclaimer must first be accepted for API connection` (reqId -1). The freshly-restarted **paper** Gateway refuses the API connection until the disclaimer is re-accepted. See [INV-14](../inv/ib_error_codes.md).
   - **`clientId 1 already in use`** — the prior session lingered briefly on the restarted Gateway, so the same `clientId` was momentarily taken.
   - (Plus benign asyncio proactor teardown noise during the failed connect: `ConnectionResetError [WinError 10054]`.)
4. **On reconnect, positions reconciled** exactly with the pre-drop baseline (`IBTM 0.0`). The recovery *path* (detect-via-socket → `disconnect()+connect()` → re-fetch positions) is correct.

**Current state vs required.** The recovery *path* and *reconciliation* work — but only via an **external** driver (the drill). The broker has **no native** disconnect detection, no auto-reconnect, and does not pause submission on a drop. A consumer that trusts `IBBroker.is_connected` would believe it is connected when it is not (the stale-flag hazard).

**M5 actions** (continuous reconciliation, [REQUIREMENTS §5.7](../../REQUIREMENTS.md#57-reconciliation)):
- **Minimal (detect-only):** subscribe to `ib.disconnectedEvent` in `IBBroker` so the cached flag is honest and a `ConnectionStatus(connected=False)` is emitted on an unexpected drop.
- **Full:** an auto-reconnect watchdog (retry with backoff; tolerate the **10141** disclaimer + **clientId-in-use** transients seen above), a continuous reconciliation loop on resume, and submission-pause-while-disconnected (interplays with the RiskEngine / kill-switch).

**Chaos-test fixture.** `scripts/probe_ib_reconnect.py` — connect → baseline positions → monitor while the operator stops/restarts the Gateway → external recovery + reconciliation; prints the cached-flag-vs-socket divergence and a drop/recovered/reconciled summary.

## Sources

See frontmatter. The M3.5 drill is the empirical basis for FM-1's "observed
behaviour"; REQUIREMENTS §5.7 is the SSOT for the required response.

## Open Questions

None blocking. FM-1's M5 actions are tracked in [TASK_REGISTRY Sketched M4+](../../TASK_REGISTRY.md#sketched-m4-post-phase-1) (M5 reconciliation), not as a separate OQ.

## Cross-References

- [REQUIREMENTS §5.7](../../REQUIREMENTS.md#57-reconciliation) — reconciliation contract (the required response).
- [REQUIREMENTS §13.2](../../REQUIREMENTS.md) — failure-mode requirements this KB expands.
- [ADR-040](../decisions/DECISIONS.md#adr-040--phase-1-deployment-target-windows-host-with-native-ib-gateway) — Phase 1 deployment / daily restart context.
- [INV-14](../inv/ib_error_codes.md) — IB error codes, incl. 10141 (paper-trading disclaimer) observed in this drill.
- [KB-8](./operational_events.md) — operational events (daily restart cadence).
- [INV-13](../inv/order_state_transitions.md) — order-state idempotency on reconcile.

## Changelog

- **v0.1 (2026-06-05 / M3.5)** — initial stub. FM-1 (unexpected IB Gateway drop / daily restart) catalogued from the M3.5 chaos drill: blive has no native `disconnectedEvent` handling (cached `is_connected` goes stale) and no auto-reconnect; the external recovery path (`disconnect()+connect()`+reconcile) works and positions reconcile; the restart surfaced IB error 10141 (paper-trading disclaimer) + a `clientId`-in-use transient. Native detect/auto-reconnect/continuous-reconciliation deferred to M5 per REQUIREMENTS §5.7. Chaos-test fixture: `scripts/probe_ib_reconnect.py`.
