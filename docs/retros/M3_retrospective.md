---
id: RETRO-M3
title: M3 Retrospective
status: STABLE
owner: Oleg
last_reviewed: 2026-06-05
version: 1.0
sources:
  - TASK_REGISTRY.md M3
depends_on:
  - TASK_REGISTRY
referenced_by: []
---

# RETRO-M3 — M3 Retrospective

> **Frozen record.** This file is `STABLE` on first complete write and not edited thereafter. If a future session needs to add context, append a separate `RETRO-M3-addendum.md` rather than modifying this file.

## Date and session(s)

- **Date:** 2026-06-05 (M3 close)
- **Sessions involved:** ~5 across 2026-05-06 → 2026-06-05 — M3.1 (unit-of-quote, ADR-050) + M3.1b (tick-grid, ADR-051) on 2026-05-06; M3.2 results-capture code + the plan-call #6 re-scope on 2026-06-05; the M3.2 live captures (operator) on 2026-06-05; and one long close session 2026-06-05 carrying M3.3 → M3.4 → M3.5 → M3.6 → close.
- **Closing milestone:** M3 (Phase 1 deployment-decision).

## Gate status

**G4 status: PASSED** (all 10 exit criteria met).

| Exit criterion (TASK_REGISTRY M3) | Status | Notes |
|---|---|---|
| 1. OQ-031 RESOLVED (new ADR, data→option→why) | ✓ | ADR-052, Option 1, on the M3.2 capture (QQL3 0/69 vs IBTM 6/6). |
| 2. EODHD-vs-IB sizing reconciled + RC-10 | ✓ | ADR-050 + ADR-051 (magnitude + tick-grid); RC-10 implemented (INV-4 v0.2). |
| 3. Bounded M3.2 capture (≥1 flip-spanning run) | ✓ | Two runs (`max-bars 40`+`60`) in `runs.jsonl`. |
| 4. Mixed-currency P&L reconciled | ✓ | M3.4 — surfaced + fixed the `equity`-reads-base-sleeve bug; live equity £1,003,855. |
| 5. Chaos drills survived | ✓ | M3.5 controlled Gateway stop/start drill; recovery + reconcile validated; native auto-reconnect = M5. |
| 6. Phase-2 substrate stubs (KB-7/KB-15/INV-8/INV-9) | ✓ | All DRAFT v0.1 (KB-15 M3.1, INV-8/INV-9 M3.2, KB-7 M3.5). |
| 7. KB-2 / KB-3 STABLE | ✓ | M3.6 — both DRAFT v0.1.1 → v1.0, scoped to the Phase-1 surface. |
| 8. No M2-IB regressions | ✓ | G3-IB-A3 intact; 591 tests green; SMART/LSEETF routing + FSM unchanged. |
| 9. RETRO-M3 written + frozen | ✓ | This document. |
| 10. Test suite green | ✓ | pytest 591, mypy --strict, black, isort, lint-imports all green. |

## Delivered vs plan

| Plan deliverable | Status | Notes |
|---|---|---|
| 1. EODHD-vs-IB sizing reconciliation + RC-10 | ✓ | ADR-050 (magnitude) + ADR-051 (tick-grid) — was *two* entangled bugs. |
| 2. M3.2 capture data file | ✓ | Bounded deterministic capture (re-scoped from "10 calendar days"). |
| 3. OQ-031 resolution ADR | ✓ | ADR-052 (Option 1); OQ-032 raised for the Phase-2 redesign. |
| 4. Live mixed-currency P&L observation | ✓ | + fixed a real `AccountSnapshot.equity` bug found in the act. |
| 5. INV-14 catalogue extension | ✓ | error 110 (M3.1, two sub-causes) + 10141 (M3.5); 110x stay forward-listed. |
| 6. KB-7 stub-DRAFT | ✓ | FM-1 (Gateway drop / daily restart) from the M3.5 drill. |
| 7. INV-8 stub-DRAFT | ✓ | M3.2 metrics. |
| 8. INV-9 stub-DRAFT | ✓ | M3.2 alerts. |
| 9. KB-15 stub-DRAFT | ✓ | M3.1 unit-of-quote / reverse-split section. |
| 10. KB-2 / KB-3 STABLE flip | ✓ | M3.6. |
| 11. RETRO-M3 | ✓ | this. |
| 12. Successor NEXT_PROMPT | ✓ | → Phase-2 readiness session (per §8.3.2). |

## Surprises

- **The unit-of-quote bug was actually two bugs.** ADR-050 fixed the price *magnitude* (EODHD reverse-split lag, ~10×); the wire run then surfaced a *second, independent* error-110 cause — tick-grid non-conformance (QQL3's 0.10 LSEETF tick vs blive's `quantize(0.01)`). Fixing magnitude *exposed* the grid bug underneath (ADR-051). A $381 price was both wrong-magnitude and off-grid.
- **ADAPTIVE_MKT does not trip the *visible* 2161 cap, yet QQL3 still doesn't fill.** In M3.2 the leveraged leg went out as ADAPTIVE_MKT, `cap_binding_2161_count` was 0 (`mktCapPrice` 0.0), and QQL3 was still 0/69 — the non-fill is robust to the order-type *mechanism*, not merely the visible cap (contrast the raw-MKT M2-IB.6.2c runs where 2161 fired). The load-bearing fact is the non-fill, regardless of mechanism.
- **The OQ-031 option set was incomplete as first drafted.** It listed accept / Pro-Client / de-lever / mean-revert — all of which drop the leverage or the strategy. The operator caught the omission of the *leverage-preserving* path (3× via margin on a 1× Nasdaq UCITS, which likely dodges the volatility-triggered PMA cap). The honest scope is a **trilemma**: a UK-retail **Cash** account has *no* open path to leveraged equity exposure (PRIIPs blocks US leveraged ETPs, PMA blocks UK ones, Cash blocks margin). Captured in OQ-032.
- **M3.4 found a real read-side equity bug — exactly what the milestone was for.** `AccountSnapshot.equity` read `NetLiquidationByCurrency[base_currency]` (the GBP *sleeve*) instead of the consolidated `BASE` total, understating a mixed-currency account by ~10% (~£101k USD dropped). Invisible at M2-IB (single-currency GBP → sleeve == total); the GBP→USD FX split is what exposed it. The synthetic M2-IB tests couldn't catch it — only the *live mixed-currency* account did. `_infer_base_currency` was also fragile (compared unconverted cross-currency magnitudes; right only by luck).
- **The M3.5 drill confirmed no native disconnect handling + surfaced a new operational code.** `IBBroker.is_connected` (cached) stayed stale-`True` on an unexpected drop; recovery needs `disconnect()+connect()`; the Gateway restart raised **IB 10141** ("paper trading disclaimer must first be accepted") + a `clientId`-in-use transient before the retry connected. Positions reconciled on resume.
- **A pre-existing full-tree formatting drift surfaced during gate-running.** ~15 M2-IG-era files were black-noncompliant — not a regression but an *unpinned* black drifting to a newer calendar version (26.3.1) whose blank-line rule changed. Fixed + pinned the formatters; no local pre-commit hook had ever caught it (gates were run scoped to changed files).
- **M3.2 was re-scoped mid-milestone** (plan-call #6) from "10 LSE-RTH calendar trading days" to bounded deterministic capture, once it was clear the driver is a historical-replay tool (regime variety comes from `--max-bars`), not the M5 live daemon.

## ADRs raised this milestone

- **ADR-050** — EODHD-vs-IB unit-of-quote conversion at sizing time (Hybrid: B-now convention catalogue / A-later free-MD-only). ACCEPTED.
- **ADR-051** — Normalize IB order prices to the contract tick grid at submit time (pure `snap_price` + IB market-rule source/cache). ACCEPTED (jointly with ADR-050 on the clean wire run).
- **ADR-052** — Phase 1 accepts the PMA-bound leveraged-leg non-fill (OQ-031 Option 1); leveraged-leg redesign deferred to Phase 2. ACCEPTED. Introduced the `refined-by:` frontmatter backref convention.

## OQs raised this milestone

- **OQ-032** — Phase 2 A3 leveraged-leg redesign: how (or whether) to restore leveraged equity exposure. OPEN, target Phase 2 entry. Carries the full design space including the **leverage-preserving margin-on-a-1×-UCITS** path and the trilemma framing.
- (**OQ-031** — Phase 1 deployment under PMA-bound retail account — was *resolved* this milestone: RESOLVED-BY-ADR-052.)

## Substrate transitions

| Artefact | Before | After |
|---|---|---|
| ADR-050 / ADR-051 / ADR-052 | (new) | ACCEPTED |
| OQ-031 | OPEN | RESOLVED-BY-ADR-052 |
| OQ-032 | (new) | OPEN |
| KB-7 `failure_modes` | MISSING | DRAFT v0.1 |
| KB-15 `parity_methodology` | MISSING | DRAFT v0.1 (M3.1) |
| INV-8 `metrics` / INV-9 `alerts` | MISSING | DRAFT v0.1 (M3.2) |
| KB-2 `ib_capability_matrix` / KB-3 `ib_pacing_spec` | DRAFT v0.1.1 | STABLE v1.0 |
| INV-4 `risk_checks` | v0.1 | v0.2 (RC-10) |
| INV-14 `ib_error_codes` | v0.7 | v0.10 (110, 10141; 110x forward-listed) |
| DD-1 `domain_objects` | v0.2 | v0.3 (AccountSnapshot mixed-currency note) |
| DD-7 `instrument_dictionary` | v1.3 | v1.5 (tick / market-rule metadata) |
| KB-10 DECISIONS / KB-11 OPEN_QUESTIONS | v0.19 / v0.3 | v0.23 / v0.5 |

## Effort vs estimate

- **Estimated:** ~5–7 sessions (revised down from ~6–8 by the plan-call #6 re-scope).
- **Actual:** ~5 sessions.
- **Variance reason:** none significant — on target. The M3.4 equity bug + the M3.5 drill added unplanned (but in-scope) work that the streamlined-clean close absorbed without slipping.

## Recommendations for NEXT_PROMPT M4 (Phase 2 entry)

- **§8.3.2 phase boundary.** M3 → M4 is the Phase 1 → Phase 2 boundary and needs the three-session ceremony: (1) this implementation close [done]; (2) a **Phase-2 readiness-audit** session that *refreshes* `PHASE_2_READINESS.md` against M3's *real* outcomes (the trilemma, the equity fix, the reconnect gap, the structural QQL3 non-fill); (3) a **Phase-2 plan-drafting** session that resolves OQ-032 with the VIX/TQQQ/VXX deep-analysis notebook as input. **Do not draft the Phase-2 strategy at close** — NEXT_PROMPT targets session (2).
- **OQ-032 is the central Phase-2 decision.** The leverage trilemma means restoring 3× equity exposure requires a deliberate lever: a Margin account (margin-on-1×-UCITS, the leverage-preserving path — needs its own no-PMA validation), Pro-Client classification, de-levering to 1×/1×, or a different archetype. The operator leans toward redesign; this is where the notebook lands.
- **The incoming strategy is more demanding than the current A3.** The notebook is a VIX-term-structure (contango/backwardation) strategy on TQQQ/VXX/IEF — it needs **VIX-futures data (UX1/UX6)** blive doesn't source yet, adds a volatility ETP (VXX), and is *more* leverage/vol-dependent — so it reinforces, not dodges, the trilemma. Phase 2 = new data + universe + signal + execution-access work.
- **The M5 reconnect gap is now documented (KB-7 FM-1).** Any multi-day live run needs at least the *minimal* fix (subscribe to `ib.disconnectedEvent` so `is_connected` is honest + emits `ConnectionStatus(False)`); the full auto-reconnect watchdog + continuous reconciliation is M5, and must tolerate the **10141** disclaimer + **clientId-in-use** transients.
- **Sizing now *can* trust live equity.** The M3.4 fix means `AccountSnapshot.equity` is the consolidated base-currency total, so NAV-slice sizing / RiskEngine can use it — but Phase-1's driver still sizes off a synthetic $100k view; wiring sizing to the live (now-correct) equity is M4/M5.

## Recommendations for the discipline itself

- **Decision option-sets must include the intent-preserving option.** The OQ-031 omission (caught by the operator) shows an agent-drafted option list can steer by omission. Before surfacing options, explicitly ask "what keeps the original goal, just achieved differently?" Captured in agent memory; not ADR-worthy on its own.
- **The CONTEXT_INVENTORY banner is growing unbounded** (a long per-commit running log). Consider the §6.4 freeze-snapshot (snapshot to `docs/_freezes/M{N}-CONTEXT_INVENTORY.md` at gate close) *and* trimming the live banner to the last 2–3 increments, so the index stays skimmable. Worth an ADR if adopted.

## Cross-References

- [TASK_REGISTRY.md](../../TASK_REGISTRY.md) — M3 plan and exit criteria.
- [CONTEXT_PROTOCOL.md §8.3.1 / §8.3.2](../../CONTEXT_PROTOCOL.md) — milestone-close + phase-boundary protocol.
- [ADR-024](../decisions/DECISIONS.md#adr-024--add-session-retrospective-artefact-type) — retro artefact type.
- [ADR-050](../decisions/DECISIONS.md#adr-050--eodhd-vs-ib-unit-of-quote-conversion-at-sizing-time-hybrid-b-now--a-later-free-md-only) / [ADR-051](../decisions/DECISIONS.md#adr-051--normalize-ib-order-prices-to-the-contract-tick-grid-at-submit-time) / [ADR-052](../decisions/DECISIONS.md#adr-052--phase-1-accepts-the-pma-bound-leveraged-leg-non-fill-oq-031-option-1) — the M3 ADRs.
- [OQ-031](../decisions/OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account) (resolved) / [OQ-032](../decisions/OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure) (raised).
- [previous retro: RETRO-M2-IB](M2-IB_retrospective.md).

## Changelog

- **v1.0 (2026-06-05)** — initial (and only) write at M3 close.
