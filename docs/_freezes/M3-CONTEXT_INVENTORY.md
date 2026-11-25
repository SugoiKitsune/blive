# blive — Context Inventory

> **Purpose:** the canonical map of every knowledge artifact this project depends on. Any agent (Claude, contributor, future-self) reading this file should understand *what we know, where it lives, and what's missing* in under 10 minutes.
>
> **Status:** v0.23 DRAFT — **M3 CLOSED 2026-06-05 — G4 PASSED (all 10 exit criteria); Phase 1 complete.** M3.6 flipped **KB-2 / KB-3 → STABLE v1.0** (scoped to the Phase-1 surface; Phase-2 futures/vol per OQ-032 re-opens). [RETRO-M3](./docs/retros/M3_retrospective.md) written + frozen (STABLE v1.0). [NEXT_PROMPT](./NEXT_PROMPT.md) v1.4 → **v1.5 targeting the Phase-2 readiness-audit session** (session 2 of the [§8.3.2](./CONTEXT_PROTOCOL.md) M3→M4 boundary; the VIX/TQQQ/VXX notebook + OQ-032 feed session 3's plan-drafting, not the close). M3 arc: ADR-050/051 (unit-of-quote + tick-grid) → bounded M3.2 capture → ADR-052 (OQ-031 Option 1) + OQ-032 (the leverage trilemma) → M3.4 equity-sleeve fix → M3.5 chaos drill + KB-7 → M3.6 KB-2/KB-3 STABLE. Tests 591; all gates green (formatters pinned `black==26.3.1`/`isort==8.0.1`). **Next: Phase-2 readiness audit (substrate-only).** Prior banner (M3.5) preserved inline below. **M3.5 chaos drill done 2026-06-05 — KB-7 `failure_modes` DRAFT v0.1 + IB 10141.** A controlled IB Gateway stop/start drill (`scripts/probe_ib_reconnect.py`; operator stopped + restarted the live paper Gateway) substituted for the 23:45 ET restart. Observed: **no native disconnect detection** (`IBBroker.is_connected` stays stale-`True` vs the dropped socket — no `disconnectedEvent` handler) and no auto-reconnect; recovery via `disconnect()+connect()` works; the restart surfaced **IB error 10141** (paper-trading disclaimer) + a transient `clientId 1 already in use`; positions reconciled on reconnect. Native detect / auto-reconnect / continuous reconciliation = **M5** (REQUIREMENTS §5.7). KB-7 MISSING → DRAFT v0.1 (FM-1); INV-14 v0.9 → v0.10 (10141 promoted; 110x stay forward-listed). G4 #5 (chaos) + #6 (Phase 2 stubs all DRAFT) ✓ MET. Tests unchanged 591 (manual fixture). **Remaining for M3 close: M3.6 (KB-2/KB-3 STABLE flip) → M3-close (RETRO-M3 + G4).** Prior banner (M3.4) preserved inline below. **M3.4 mixed-currency P&L done 2026-06-05 — found + fixed a real equity bug.** Live reconciliation on IB Paper `DUP886336` (GBP base + USD cash from the FX) surfaced that `AccountSnapshot.equity` read the GBP NetLiquidation *sleeve* (£902,839) not the consolidated `BASE` total (£1,003,886) — silently dropping the ~£101k USD sleeve (invisible until the FX split the account; single-currency at M2-IB → sleeve == total). Fixed (`IBBroker._build_account_snapshot` reads the `BASE` aggregate primary; `_infer_base_currency` hardened to the unit-`ExchangeRate` signal) + a mixed-currency regression test + new `scripts/probe_ib_account_ccy.py` raw-row diagnostic; DD-1 §2.8 v0.2 → v0.3 footnote; re-confirmed live (equity £1,003,855). Bug-fix, **no ADR** (DD-1 already specified equity = total NAV). Tests 590 → 591; mypy/black/isort/lint-imports green. (Separate hygiene commit `5166e20` pinned black==26.3.1 / isort==8.0.1 + cleared pre-existing M2-IG-era full-tree formatting drift.) G4 exit-criterion #4 ✓ MET. **Next: M3.5 — controlled Gateway stop/start drill + KB-7 stub.** Prior banner (M3.3) preserved inline below. **M3.3 OQ-031 RESOLVED 2026-06-05 — Option 1 ([ADR-052](./docs/decisions/DECISIONS.md#adr-052--phase-1-accepts-the-pma-bound-leveraged-leg-non-fill-oq-031-option-1)).** The operator resolved [OQ-031](./docs/decisions/OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account) on the M3.2 capture: Phase 1 **accepts** the PMA-bound leveraged-leg non-fill (QQL3 0/69 fills = 0% vs IBTM 6/6 = 100%) as a deployment characteristic — **no code change**, live behaviour Treasury-leg-dominated. The leveraged-leg redesign is deferred to Phase 2 as **OQ-032** (full design space incl. the leverage-preserving margin-on-a-1×-UCITS path the four OQ-031 options omitted; the *trilemma* — PRIIPs blocks US leveraged ETPs, PMA blocks UK ones, Cash blocks margin-leverage). `refined-by: ADR-052` backref added to ADR-043 + ADR-047 (QQL3 leg provisional). G4 exit-criterion #1 ✓ MET. Substrate: DECISIONS v0.22 → v0.23; OPEN_QUESTIONS v0.4 → v0.5; TASK_REGISTRY v0.11 → v0.12; [NEXT_PROMPT](./NEXT_PROMPT.md) v1.3 → v1.4. No code change; tests unchanged at 590. **Next: M3.4 — mixed-currency P&L reconciliation.** Prior banner (M3.2 capture-complete) preserved inline below. **M3.2 CAPTURE-COMPLETE 2026-06-05.** Its bounded-capture criterion is MET on the live IB-Paper + EODHD wire (LSE RTH): two flip-spanning captures in `~/.blive/data/m3_2_window/runs.jsonl` (`max-bars 40` + `60`, 2 flips each) give **QQL3 0/69 fills (0%) vs IBTM 6/6 (100%), 2161 cap-binding 0, zero rejects/breaches/error-110** — the empirical OQ-031 signal (the leveraged equity leg doesn't fill on now-correctly-sized on-grid orders; the Treasury leg fills cleanly; ADAPTIVE_MKT didn't trip the *visible* 2161 cap yet QQL3 still didn't fill). `scripts/flatten_ib_paper.py` added + used to reset the accumulated paper IBTM (230 → 0). M3.2 data deliverable done; **next: M3.3 — OQ-031 resolution** (NEXT_PROMPT v1.3). This v0.19 increment also carries the earlier-this-session M3.2 results-capture code + INV-8/INV-9 stubs + the plan-call #6 re-scope (below). The empirical-window per-run results sink ([`src/blive/runtime/m3_2_record.py`](./src/blive/runtime/m3_2_record.py) → one JSON row per run under `~/.blive/data/m3_2_window/runs.jsonl`) is wired into [`scripts/run_m2ib6_ib_paper.py`](./scripts/run_m2ib6_ib_paper.py) (`--record-path` / `--no-record` / `--note`). Capture surface (all additive, no FSM-behaviour change): `IBMultiRunResult` gained `accepted_count` / `submitted_by_symbol` / `observed_error_codes` + the `cap_binding_2161_count` property; `_drain_order_lifecycle` now reports `reached_accepted`; `IBBroker` tallies order-related error/warning codes in `observed_error_codes` (the warning-2161 PMA-cap signal, OQ-031); `blive.runtime.signals.equity_leg_regime_flips` computes the regime-flip metric. INV-8 `metrics` + INV-9 `alerts` MISSING → DRAFT v0.1 (M3.2-only stubs; full Prometheus / alerting stays M7). Tests 568 → 590 (+11 results-sink, +7 regime-flip, +3 pipeline-capture, +1 broker-tally); mypy `src` / black / isort / lint-imports all green. **M3.2 also re-scoped 2026-06-05 (operator call, TASK_REGISTRY plan-call #6): exit changed from "10 LSE-RTH calendar trading days" → bounded deterministic capture** — the driver is a historical-replay tool, so regime variety comes from the replay window (`--max-bars`) deterministically (offline-verifiable via the new `--dry-run`; empirically `--max-bars 60` spans 2 equity-leg flips), and QQL3's structural ≈0 fill-rate under the 2161 cap is already established. **Close criterion: ≥1 RTH capture run over a flip-spanning window (QQL3 ≈0 fills + IBTL/IBTM fills >0); operator-driven; M3.2 stays open until that row exists.** No new ADRs/OQs (the sink shape + re-scope are refinements per [NEXT_PROMPT](./NEXT_PROMPT.md)). Prior banner (M3.1 + M3.1b CLOSED) preserved inline below. **M3.1 + M3.1b CLOSED 2026-06-05 — ADR-050 + ADR-051 flipped ACCEPTED on the clean LSE-RTH wire run (zero IB error 110); M3.1b (ADR-051: IB order prices snapped to the contract tick grid) implemented + all gates green.** The 2026-06-05 LSE-RTH wire run (`--order-type LMT --max-bars 5`) validated ADR-050's unit-of-quote fix (QQL3 sized 65 sh @ ~$39, not the pre-fix 6 @ ~$381) but surfaced a *second, independent* cause of IB error 110 — **tick-size non-conformance** (QQL3's 0.10 LSEETF tick vs blive's `quantize(0.01)` penny rounding; 38.52 / 42.83 / 44.15 rejected, 39.60 / 41.50 passed). ADR-051 fixes it at the `IBBroker.submit` boundary: a pure `blive.adapters.shared.price_grid.snap_price` + an IB market-rule source/cache (`blive.adapters.ib.price_rules`, `minTick` fallback, per-`Instrument` cache + `clear_cache`); the pipeline's `quantize(0.01)` is removed. Magnitude (ADR-050, sizing-time) and grid (ADR-051, submit-time) are distinct layers by design. **ADR-050 + ADR-051 flipped PROPOSED → ACCEPTED jointly on the 2026-06-05 11:38 BST clean LMT wire run** — QQL3 limits snapped to its 0.10 grid on the live wire (`38.52→38.5`, `44.15→44.2`, …) and placed with zero IB error 110 (6 submitted, 0 rejected; IBTM filled). The residual QQL3 no-fill is the structural 2161 PMA-cap ([OQ-031](./docs/decisions/OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account), M3.2/M3.3), not a tick issue. **M3.1 + M3.1b closed; next active path: M3.2 — 10 LSE-RTH-day empirical window.** Substrate this batch: DECISIONS v0.20 → v0.21 (ADR-051 PROPOSED); INV-14 v0.8 → v0.9 (error 110 two sub-causes); DD-7 v1.3/v1.4 → v1.5 (tick-grid metadata footnote + frontmatter-version correction); 2 incidental pre-existing mypy fixes in `ig/instrument_resolver.py` (env-drift). Tests 541 → 568 (13 `price_grid` + 7 `price_rules` + 5 `broker_tick_grid`; mypy `src` / black / isort / lint-imports all green). Operationally: SAC-blocked `uv run` worked around by invoking the venv Python directly; IB paper account funded with USD (FX-converted from GBP) to clear the prior insufficient-funds blocker. **M3.1 (EODHD-vs-IB unit-of-quote reconciliation) implementation landed 2026-05-06.** Held PROPOSED for the wire-validation flip per the M2-IB pattern: ADR-050 (Hybrid B-now / A-later free-MD-only) drafted PROPOSED in this commit; flips to ACCEPTED on first `scripts/run_m2ib6_ib_paper.py --max-bars 5` LSE-RTH wire run that produces a QQL3 sized within ±1% of the IB-USD-equivalent target exposure with no IB error 110. **Substrate transitions shipped this commit**: ADR-050 PROPOSED added (DECISIONS v0.19 → v0.20); INV-4 v0.1 → v0.2 (RC-10 promoted from DRAFT-only to implemented; threshold ±20% → ±50%); INV-14 v0.7 → v0.8 (error 110 promoted from v0.7 side-finding to catalogue row); KB-15 `parity_methodology` MISSING → DRAFT v0.1 (stub-DRAFT, unit-of-quote / reverse-split section only — full M7 envelope deferred); DD-7 STABLE preserved + v1.4 footnote on the EODHD-vs-IB convention layer. **Code-side**: new module `src/blive/adapters/eodhd/conventions.py` with per-IB-symbol catalogue (QQL3 → MANUAL_SCALE divisor=10 against IB live reference); `RiskCheckCode.RC_10` added to `blive.domain.events`; `RiskEngineConfig.max_price_deviation_pct` (default ±50%) + `RiskInputs.reference_price` added to `blive.risk.checks` with order-of-evaluation slot after RC-12; `run_ib_multi_pipeline._price_lookup` + `_ib_order_from_desired` route through the conventions catalogue. Tests: 519 → 541 (8 conventions + 8 RC-10 + 1 pipeline integration; mypy/black/isort/lint-imports green on all touched files). Investigation surface: `scripts/probe_qql3_unit_of_quote.py` (parameterised hypothesis-refutation matrix; 2026-05-06 EODHD-side run refuted H1 split-adjusted + H2 currency-unit; operative cause is EODHD-side recent reverse-split lag). Operator decisions captured: Hybrid B-now / A-later **with A bounded to free IB MD tiers only** (paid LSEETF subscription out of scope indefinitely; consequence accepted); RC-10 threshold ±50% (calibrated for leveraged-ETP daily ranges per INV-14 v0.7); central-config sub-milestone deferred (current dict-literal scales gracefully; YAML-driven catalogue forward-listed in TASK_REGISTRY Sketched M4+). Next active path: **wire-validation smoke** during LSE RTH (operator-driven), then **M3.2 — 10 LSE-RTH-day empirical window**. Prior banner (M3 plan-drafted) preserved in §10 history below; the v0.13 banner pointed at M3.1 entry; this v0.14 banner points at M3.1 implementation landing + wire-validation pending. M2 → Phase 2 transition still complete per [CONTEXT_PROTOCOL §8.3.2](./CONTEXT_PROTOCOL.md); M3 plan stays at TASK_REGISTRY v0.6 → v0.7 with M3.1 sub-milestone deliverables ticked.
>
> **Maintainer:** Oleg + Claude.
>
> **Companion files in this repo:**
> - [`CONTEXT_PROTOCOL.md`](./CONTEXT_PROTOCOL.md) — the rules that keep the artifacts catalogued here coherent over time. Edits to anything in this inventory must follow that protocol.
> - [`REQUIREMENTS.md`](./REQUIREMENTS.md) — the project requirements (one of the artifacts catalogued below).
>
> **Conventions used here:**
> - **KB-N** — durable knowledge base (slow-changing world facts).
> - **INV-N** — inventory (a list of items in some category).
> - **DD-N** — data dictionary (schema-level documentation).
> - **ADR-N** — architectural decision record.
> - **OQ-N** — open question.
> - **RETRO-M{N}** — milestone retrospective (per [ADR-024](./docs/decisions/DECISIONS.md#adr-024--add-session-retrospective-artefact-type)); frozen historical record.
>
> Status tags: `MISSING` (not yet started) · `DRAFT` (started, incomplete) · `STABLE` (current, accurate) · `STALE` (needs review) · `DEPRECATED` (kept for history).
>
> RETRO artefacts use a simplified lifecycle: `DRAFT → STABLE` only (no `STALE` / `DEPRECATED`).

---

## 0. Why this file exists

Complex software projects fail when context is implicit. As soon as the same project spans more than one session, more than one agent, or more than one person, undocumented context becomes the bottleneck — not skill, not tooling.

The fix is to keep multiple **representation hierarchies** of the same project alongside the code:

- **Vision** — why this exists (1 paragraph).
- **Requirements** — what we will build (`REQUIREMENTS.md`).
- **Design** — how it's shaped (`DESIGN.md`, future).
- **Plan** — what to do next (`TASK_REGISTRY.md`, future).
- **Code** — the system itself.
- **Tests** — proof.
- **Ops** — how to run it (`RUNBOOK.md`, future).

Around those hierarchies, four supporting context layers:

1. **Knowledge bases (KBs)** — durable facts about the world we're building in (btest DSL, IB API, regulations, frameworks).
2. **Inventories (INVs)** — exhaustive lists of items in well-defined categories (strategies, order types, risk checks, events, ports, metrics, alerts).
3. **Data dictionaries (DDs)** — schema-level definitions of every domain object, every persisted row, every API payload.
4. **Decision & question logs** — append-only history of choices made and choices deferred (ADRs, OQs).

This file is the index of all of those. It does not contain the knowledge itself — only pointers to it, lifecycle status, and ownership.

---

## 1. Representation Hierarchy

| Layer | Artifact | Status | Lifecycle | Purpose |
|-------|----------|--------|-----------|---------|
| 0. Process | [`CONTEXT_PROTOCOL.md`](./CONTEXT_PROTOCOL.md) | DRAFT v0.4 (2026-05-02) | rare amendments, iterative until v1 | the discipline that keeps every other artifact coherent. v0.2 amended §8.3 with milestone-close (8.3.1) and phase-boundary (8.3.2) rules per [ADR-025](./docs/decisions/DECISIONS.md#adr-025--amend-context_protocol-83-with-milestone-close-and-phase-boundary-rules). v0.3 added §11 (Human-governance / agent-execution division of labour with five-layer adoption stack) per [ADR-026](./docs/decisions/DECISIONS.md#adr-026--adopt-agentic-execution-layer-reduce-human-action-surface); existing §11 Self-Critique renumbered to §12. v0.4 extended §11.2 with the session-bootstrap-file paragraph (manual L0 baseline) per [ADR-042](./docs/decisions/DECISIONS.md#adr-042--session-bootstrap-files-agent-agnostic-pattern-for-l0-warm-up-entry-point) |
| 0. Index | **this file** (`CONTEXT_INVENTORY.md`) | DRAFT v0.23 (2026-06-05) | continuous | the registry of all artifacts |
| 0. Bootstrap | [`CLAUDE.md`](./CLAUDE.md) | STABLE v1.0 (2026-05-02) | rare amendments, mirrors CONTEXT_PROTOCOL §8.1 / §11.2 | session-bootstrap pointer for AI agent harnesses (Claude Code instance of the agent-agnostic pattern in [ADR-042](./docs/decisions/DECISIONS.md#adr-042--session-bootstrap-files-agent-agnostic-pattern-for-l0-warm-up-entry-point)); the manual L0 baseline of the agentic-execution stack per [CONTEXT_PROTOCOL §11.2](./CONTEXT_PROTOCOL.md). Pointer file only — never restates the discipline; SSOT remains CONTEXT_PROTOCOL |
| 1. Vision | (top of `README.md`, future) | MISSING | rare | one paragraph: why blive exists |
| 2. Requirements | [`REQUIREMENTS.md`](./REQUIREMENTS.md) | DRAFT v0.1 | iterative until M0 frozen | what we will build |
| 3. Design | `DESIGN.md` | MISSING | iterative through M2 | how it is shaped (component, sequence, state diagrams) |
| 4. Plan | [`TASK_REGISTRY.md`](./TASK_REGISTRY.md) | DRAFT v0.6 (2026-05-06) | per milestone | Phase 1 plan: M0–M1 closed (G1, G2 PARTIAL); M2-IG bridge **closed at architectural surface 2026-04-28** (sub-milestones .1–.4 shipped; .5 strategy run deferred — see [RETRO-M2-IG](./docs/retros/M2-IG_retrospective.md)); **M2-IB closed 2026-05-06** at `M2-IB.6-close` (G3-IB-A3 PASSED at architectural surface; first IB-paper FILL on IBTM 19 × £128.5; OQ-031 deferred to M3 — see [RETRO-M2-IB](./docs/retros/M2-IB_retrospective.md)); **M3 plan-drafted 2026-05-06** at the [§8.3.2](./CONTEXT_PROTOCOL.md) third session (deployment-decision framing; sub-milestones M3.1 → M3.6 → M3-close); **M3.1 active path** (kickoff at [NEXT_PROMPT v1.0](./NEXT_PROMPT.md)). |
| 5. Code | `src/blive/` | DRAFT v1.9 (2026-06-05) | continuous | M0+M1: domain + adapters/{paper, memory, clock, alert} + strategy + sizing + risk + runtime/paper_pipeline. **M2-IG:** adapters/shared/{rate_limiter, credentials} + runtime/broker_registry + adapters/ig/*. **M2-IB.2–.4a:** adapters/ib/{credentials, client, instrument_resolver, broker, market_data, rate_limiter}; IB read/write side wire-validated. **M2-IB.5:** `runtime/ib_pipeline.py`, `runtime/signals.py`, `scripts/refresh_eodhd_parquet.py`, `scripts/run_m2ib5_paper.py`. **M2-IB.6.1 / .6.2-pre:** multi-instrument IB pipeline + LongShortPortfolio dispatch + `scripts/refresh_eodhd_signals.py` + `scripts/run_m2ib6_ib_paper.py` + `scripts/probe_tqqq_us_rth.py`; resolver now handles UK-listed ETFs via `SMART` + `primaryExchange="LSEETF"`; broker now subscribes to `ib.errorEvent` and stashes order-linked errors so PRIIPs / `Inactive` rejections surface the real formatted reason text instead of the fallback literal. **M2-IB.6.2c:** `OrderType.ADAPTIVE_MKT` + per-symbol `order_type_by_symbol` override on `run_ib_multi_pipeline`. **M3.1:** new `adapters/eodhd/{__init__,conventions}.py` (per-IB-symbol unit-of-quote catalogue per ADR-050); `runtime/ib_pipeline.run_ib_multi_pipeline` `_price_lookup` + `_ib_order_from_desired` route through `eodhd_to_ib_price`; `risk/checks.py` adds RC-10 (price sanity) with `RiskInputs.reference_price` + `RiskEngineConfig.max_price_deviation_pct=0.5`; `domain/events.RiskCheckCode.RC_10` enum value; `scripts/probe_qql3_unit_of_quote.py` parameterised investigation probe. **M3.1b:** `adapters/shared/price_grid.py` (`snap_price`) + `adapters/ib/price_rules.py` (`IBPriceRuleService` market-rule source/cache) per ADR-051; `IBBroker.submit` snaps priced fields to the contract tick grid. **M3.2:** new `runtime/m3_2_record.py` (per-run `RunRecord` results sink → `~/.blive/data/m3_2_window/runs.jsonl`); `runtime/ib_pipeline.IBMultiRunResult` gains `accepted_count` / `submitted_by_symbol` / `observed_error_codes` + `cap_binding_2161_count`; `_drain_order_lifecycle` reports `reached_accepted`; `adapters/ib/broker.IBBroker.observed_error_codes` 2161 tally; `runtime/signals.equity_leg_regime_flips`; `scripts/run_m2ib6_ib_paper.py` writes the row + gained `--dry-run` (offline regime-coverage preview; data-load now precedes the IB connect) / `--record-path` / `--no-record` / `--note`. New `scripts/flatten_ib_paper.py` (raw-`ib_async` paper-account reset, scoped to QQL3/IBTL/IBTM, distinct clientId, `--dry-run`). **M3.4:** `IBBroker._build_account_snapshot` reads the `BASE` NetLiquidation aggregate primary (was the base-currency sleeve — the M3.4 mixed-currency equity bug); `_infer_base_currency` uses the unit-`ExchangeRate` signal; new `scripts/probe_ib_account_ccy.py` raw per-currency account-value diagnostic. **M3.5:** new `scripts/probe_ib_reconnect.py` (disconnect/reconnect chaos drill — external recovery loop + reconciliation; the KB-7 FM-1 fixture). |
| 6. Tests | `tests/` | DRAFT v1.9 (2026-06-05) | continuous | 591 unit tests green (519 → 541 at M3.1; 568 at M3.1b; 590 at M3.2; 591 at M3.4 — +1 `test_account_snapshot_mixed_currency_reads_base_total` regression guard for the equity-sleeve bug). Earlier M0/M1/M2-IG/M2-IB.* coverage retained. **M3.1 additions:** `tests/unit/adapters/eodhd/test_conventions.py` (8 tests — identity / manual_scale / Decimal precision / value rejection / catalogue documentation); `tests/unit/risk/test_checks.py` grows 8 RC-10 tests (within band / far above / far below / missing reference / MKT skip / configurable threshold / default ±50% / RC-12 short-circuit); `tests/unit/runtime/test_ib_pipeline.py` adds 1 pipeline-integration test (QQL3 in-catalogue conversion produces ~10× larger position size than no-conversion baseline). **M3.2 additions (+22):** `tests/unit/runtime/test_m3_2_record.py` (11 — counts / cap-binding extraction / fill-rate / FSM-trace / zero-submitted / breach mapping / note / JSON round-trip / JSONL append); `test_ib_pipeline.py` +3 (submitted_by_symbol + accepted_count; 2161 capture via broker; no-accept ≠ accepted); `test_signals.py` +7 (`equity_leg_regime_flips` long/flat/short / missing-column / single-row / empty / NaN); `tests/unit/adapters/ib/test_broker.py` +1 (`observed_error_codes` tally, reqId ≤ 0 excluded, copy semantics). |
| 7. Ops | `RUNBOOK.md` | MISSING | post-M5 | running it |

Rule: each layer down narrows scope and is internally consistent with the layer above. If layer N changes, layer N-1 either approved the change (forward propagation) or is now stale (must be flagged).

---

## 2. Knowledge Bases (KBs)

Durable, slow-changing context. Each KB is one file under `docs/kb/` with a header listing **owner, status, last-reviewed, sources**.

| Id | File | Status | Why it matters | Owner | Needed by |
|----|------|--------|---------------|-------|-----------|
| **KB-1** | [`docs/kb/btest_dsl_inventory.md`](./docs/kb/btest_dsl_inventory.md) | DRAFT v0.1 (2026-04-26) | Every `btest` dataclass with broker-neutrality verdict (broker-neutral / backtest-only / mixed). Strategy → DataConfig → Universe → factors → signals → portfolio → execution → costs → backtest config → DataSource registry. blive's three sidecar extensions documented (live_overrides, live_*_provider, live_kill_switch). | Claude | REQUIREMENTS |
| **KB-2** | [`docs/kb/ib_capability_matrix.md`](./docs/kb/ib_capability_matrix.md) | STABLE v1.0 (2026-06-05) | Connectivity (TWS / Gateway / CPAPI), asset classes, order types, TIFs, routing (SMART / direct), IB algos (Adaptive, TWAP, VWAP, etc.), market hours, multi-currency, account types (IBKR Pro Margin), 2FA / IBC / daily restart. **STABLE flip at M3.6 (2026-06-05)** — the Phase-1 IB surface is wire-exercised across M2-IB.6 + M3 (incl. the 2161/Adaptive non-bypass finding + M3.4 multi-currency + ADR-040 native-Gateway note; DD-7 ref fixed); scoped to the Phase-1 equity/ETF surface (Phase-2 futures/vol per OQ-032 re-opens it → STALE). | Claude | REQUIREMENTS, DESIGN |
| **KB-3** | [`docs/kb/ib_pacing_spec.md`](./docs/kb/ib_pacing_spec.md) | STABLE v1.0 (2026-06-05) | 50 msg/sec throttle; historical-data pacing (≤60/10min, BID_ASK ×2); market-data tiers; reqMktData vs reqTickByTickData budgets; orderId monotonic + multi-client; daily/weekly ops; CPAPI limits (rejected); error-code mapping at pacing boundary; concrete adapter budget defaults table. **STABLE flip at M3.6 (2026-06-05)** — the ADR-031 rate limiter is behaviour-verified against IB Paper across M2-IB/M3; §5 daily-restart cross-linked to the M3.5 reconnect drill (KB-7 FM-1) + ADR-040; INV-14 refs fixed; scoped to the Phase-1 pacing surface. | Claude | REQUIREMENTS, DESIGN |
| **KB-4** | [`docs/kb/frameworks_survey.md`](./docs/kb/frameworks_survey.md) | DRAFT v0.1 (2026-04-26) | Adopt: ib_async. Study: NautilusTrader, Hummingbot, Lumibot, vnpy. Reject: native ibapi, CPAPI, Lean, Backtrader live, Zipline+pylivetrader, QSTrader, Lumibot polling lifecycle, QuantRocket, PyAlgoTrade, Catalyst. 10 architectural patterns to copy. | Claude | REQUIREMENTS |
| **KB-5** | [`docs/kb/strategy_taxonomy.md`](./docs/kb/strategy_taxonomy.md) | DRAFT v0.1 (2026-04-26) | The actual strategies blive must support: A1 cross-sectional L/S, A1a cross-index lagging, A2 single-instrument timing, A3 multi-ETF rotation; future A4–A8 slots. Phased priority proposal §7 pending OQ-013. Raised OQ-013..OQ-021. | shared (Oleg primary, Claude assist) | REQUIREMENTS |
| **KB-6** | [`docs/kb/cost_margin_dictionary.md`](./docs/kb/cost_margin_dictionary.md) | DRAFT v0.1 (2026-04-26) | Each component: backtest semantic, live equivalent, parity envelope. Commission (pure formula, IB ground truth), BorrowCost (live override needed, ±25 bps gen-coll), FinancingCost (live override, ±15 bps within tier), StaticFees (pure formula), MarginConfig (live per-instrument), RiskChecks + DrawdownPolicy (pure formulas). Aggregation pipeline + parity-residual decomposition for ADR-012. | Claude | REQUIREMENTS |
| **KB-7** | [`docs/kb/failure_modes.md`](./docs/kb/failure_modes.md) | DRAFT v0.1 (2026-06-05) | Every failure mode + required engine response + observed blive behaviour + chaos-test fixture. Expansion of REQUIREMENTS §13.2. **M3.5 stub**: FM-1 (unexpected IB Gateway drop / daily restart) catalogued from the M3.5 drill (`scripts/probe_ib_reconnect.py`) — no native disconnect detection / auto-reconnect (stale `is_connected`; the M5 gap per REQUIREMENTS §5.7); the external recovery path + reconciliation validated; surfaced IB 10141. Full catalogue (market-data gaps, fill races, clock skew, …) extends at M4/M5. | Claude | REQUIREMENTS, DESIGN |
| **KB-8** | [`docs/kb/operational_events.md`](./docs/kb/operational_events.md) | DRAFT v0.2 (2026-04-27) | Daily TWS restart (23:45 ET), weekly token rotation, TWS auto-update window, exchange holidays, corp actions, IB maintenance windows, blive-side scheduled events (`AccountUpdate` 30s, reconciliation 60s, daily backup, parity diagnostic). **v0.2 (M2-IG.2)**: §8 IG-specific operational events — session token TTL (6h demo / 24h live; auto-refresh 30s pre-emptive), idle-session timeout (~6 min; 5-min heartbeat on `general` bucket), weekend market closure, IG maintenance windows, IG-vs-IB comparison table. | Claude | DESIGN, OPS |
| **KB-9** | [`docs/kb/uk_regulatory.md`](./docs/kb/uk_regulatory.md) | DRAFT v0.2 (2026-05-03) | Personal trading not FCA-regulated; HMRC trade-by-trade records 5+ years; existing event-log + hash-chained audit already satisfies MiFID-II shape; market abuse always applies; data privacy n/a personal. **v0.2 adds PRIIPs / KID restrictions for UK retail clients** — load-bearing for ADR-047's Phase 1 universe substitution. Items needing accountant/lawyer flagged. **(Oleg / professional)** confirmation expected on trading-vs-investment classification. | Oleg primary | REQUIREMENTS (NFRs) |
| **KB-10** | [`docs/decisions/DECISIONS.md`](./docs/decisions/DECISIONS.md) | DRAFT v0.23 (2026-06-05) | **ADR-001..052 ACCEPTED**, except **ADR-021 SUPERSEDED-BY-ADR-043**. v0.23 (M3.3) added ADR-052 (OQ-031 resolution — Phase 1 Option 1, accept the PMA-bound leveraged-leg non-fill; no code change) + a `refined-by: ADR-052` backref on ADR-043 / ADR-047 (QQL3 leg provisional). v0.21 (M3.1b) added ADR-051 (normalize IB order prices to the contract tick grid at submit time); v0.22 flipped ADR-050 + ADR-051 PROPOSED → ACCEPTED jointly on the 2026-06-05 clean LSE-RTH wire run (zero IB error 110). v0.19 closed M2-IB.6 (ADR-048 + ADR-049 flipped ACCEPTED). v0.20 (M3.1 entry) added ADR-050 (EODHD-vs-IB unit-of-quote conversion at sizing time — Hybrid B-now / A-later free-MD-only). | Claude record, Oleg approve | continuous |
| **KB-11** | [`docs/decisions/OPEN_QUESTIONS.md`](./docs/decisions/OPEN_QUESTIONS.md) | DRAFT v0.5 (2026-06-05) | OQ-001..032 catalogued. **14 RESOLVED-BY-ADR** (013–016, 018, 019, 021, 022, 024–027, 030, **031→ADR-052**); 1 RESOLVED-by-finding (017); 5 OPEN (012, 023, 028, 029, **032**); 11 IN_DISCUSSION (001–011, 020). v0.4 raised OQ-031 (PMA-bound deployment); v0.5 (M3.3) flipped OQ-031 → RESOLVED-BY-ADR-052 (Option 1) + raised OQ-032 (Phase 2 leveraged-leg redesign — full design space incl. the leverage-preserving margin path). | shared | continuous |
| **KB-15** | [`docs/kb/parity_methodology.md`](./docs/kb/parity_methodology.md) | DRAFT v0.1 (2026-05-06) | M3.1 stub-DRAFT — unit-of-quote / reverse-split section only (full M7 parity envelope deferred). §1 problem framing + 4-hypothesis catalogue (split-adjusted / currency / share-class / vendor-symbol divergence); §2 per-instrument convention catalogue spec at `src/blive/adapters/eodhd/conventions.py`; §3 RC-10 role + non-role; §4 catalogue-curation workflow; §5 QQL3 worked example with M3.1 fix's pre/post-fix matrix; §6 M7 forward-list. | DESIGN |

---

## 3. Inventories (INVs)

Exhaustive lists in well-defined categories. Each lives at `docs/inv/<name>.md` and is expected to be machine-checkable (an automated test asserts the inventory matches code).

| Id | File | Status | Items | Needed by |
|----|------|--------|-------|-----------|
| **INV-1** | [`docs/inv/strategies.md`](./docs/inv/strategies.md) | DRAFT v0.1 (2026-04-26) | 9 strategies catalogued; v1 phase per ADR-013; NAV slice TBD per OQ-013. | REQUIREMENTS, DESIGN |
| **INV-2** | `docs/inv/order_types.md` | MISSING | MKT, LMT, MOC, LOC, STP, STP_LMT, OPG, IOC, FOK + IB support matrix per asset class | REQUIREMENTS, DESIGN |
| **INV-3** | `docs/inv/tif_values.md` | MISSING | DAY, GTC, IOC, FOK, OPG, GTD + venue compatibility | DESIGN |
| **INV-4** | [`docs/inv/risk_checks.md`](./docs/inv/risk_checks.md) | DRAFT v0.2 (2026-05-06) | RC-01..RC-13: leverage, exposure, weight, daily loss, rate limits (per-strategy + global), concentration, stale data, market hours, price sanity, drawdown scaling, model-artefact freshness, kill-switch armed. Order-of-evaluation specified. **v0.2 (M3.1)**: RC-10 promoted from DRAFT-only to implemented per ADR-050; threshold widened ±20% → ±50% for leveraged-ETP volatility per INV-14 v0.7; reference is the EODHD bar close converted via `blive.adapters.eodhd.eodhd_to_ib_price`. | REQUIREMENTS |
| **INV-5** | [`docs/inv/domain_events.md`](./docs/inv/domain_events.md) | STABLE v0.3.1 (2026-05-01) | 17 event topics catalogued with payload, emission rule, consumer set, milestone. M0+M1+M2-IB.3b-i implemented: order.*, broker.connection, risk.breach, account.update (incl. 30s diff-suppress emission timer per ADR-033), artefact.freshness_warning. `DomainEvent = OrderEvent \| ConnectionStatus \| RiskBreach \| AccountUpdate \| ArtefactFreshnessWarning`. `BrokerEvent = OrderEvent \| ConnectionStatus \| AccountUpdate`. M4/M5/M7 events remain forward-planned. | DESIGN |
| **INV-6** | [`docs/inv/ports_adapters.md`](./docs/inv/ports_adapters.md) | STABLE v0.3.1 (2026-04-28) | 6 Ports (Broker, MarketData, Clock, Persistence, Alert, EventBus). M0+M1 adapters live: PaperBroker (incl. replace), PaperMarketData, InMemoryPersistence, InMemoryEventBus, Sim/WallClock, LogAlert. **v0.3 (M2-IG.2)**: §2.1/§2.2 grew IG read+write rows + explicit PARKED markers on IB/EODHD; §3 references [ADR-034](./docs/decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004) + new `Broker registry isolation` import-linter contract; new §3.1 catalogues `blive.adapters.shared.*` cross-cutting modules (rate limiter + credentials). **v0.3.1 (M2-IB.1)**: PARKED markers removed from IB/EODHD rows (M2-IB ACTIVE); IG rows MISSING → DRAFT (architectural surface; bridge-paused, never wire-validated per RETRO-M2-IG). Port Protocol surfaces unchanged. | DESIGN |
| **INV-7** | `docs/inv/rest_endpoints.md` | MISSING (eventually superseded by OpenAPI) | path, method, auth class, request/response, idempotency | M6 |
| **INV-8** | [`docs/inv/metrics.md`](./docs/inv/metrics.md) | DRAFT v0.1 (2026-06-05) | **M3.2 stub** — the five empirical-window metrics (per-instrument fill-rate, regime-flip count, warning-2161 cap-binding, RiskEngine breach count, FSM-trace coverage) + supporting raw counters, sourced from the per-run results sink (`RunRecord` in `src/blive/runtime/m3_2_record.py`). Full Prometheus name/label/scrape surface deferred to M7. | DESIGN, M7 |
| **INV-9** | [`docs/inv/alerts.md`](./docs/inv/alerts.md) | DRAFT v0.1 (2026-06-05) | **M3.2 stub** — the two paper-mode alerts (RiskEngine breach `risk.breach/{RC}`; kill-switch armed `risk.breach/RC-13`) on the `LogAlert` channel. Full alerting stack (Alertmanager, channel routing, runbooks) deferred to M7. | M7 |
| **INV-10** | [`docs/inv/asset_classes.md`](./docs/inv/asset_classes.md) | DRAFT v0.1 (2026-04-26) | 13 asset classes catalogued with btest support, EODHD All-in-One coverage, IB tradability, v1 priority. | REQUIREMENTS |
| **INV-11** | `docs/inv/modes.md` | DRAFT (inline REQUIREMENTS §5.6) | Paper / IB Paper / Shadow / Live — capabilities, transitions, gates | REQUIREMENTS |
| **INV-12** | `docs/inv/backup_artifacts.md` | MISSING | what gets backed up, frequency, retention, restore SLA | M5 |
| **INV-13** | [`docs/inv/order_state_transitions.md`](./docs/inv/order_state_transitions.md) | STABLE v0.1 (2026-04-26) | 9 states × 9 triggers → 14 legal transitions (T1..T14); side effects per row; reason / fill payload discipline; cancel-/reject-reason taxonomy; idempotency rules. Implementation in `blive.domain.order_fsm`; tests cover every row + illegal sample. | DESIGN |
| **INV-14** | [`docs/inv/ib_error_codes.md`](./docs/inv/ib_error_codes.md) | DRAFT v0.10 (2026-06-05) | IB error codes blive's adapter handles (typed-exception map + operator action). M2-IB.3b-ii: 162 + 200 observed. M2-IB.4a: 10311 / 201 / 10147 / 202 / 399 promoted. **M2-IB.6.1 / .6.2:** PRIIPs-KID variant of 201 documented, plus the broker-side **reason-extraction taxonomy**: `trade.log` alone is insufficient for `Inactive` rejections; `ib.errorEvent` stash + deferred emission are now load-bearing. **M2-IB.6.2c:** 2161 (PMA cap) catalogued. **M3.1 (v0.8):** error 110 promoted from v0.7 side-finding to catalogue row — canonical symptom of EODHD-vs-IB unit-of-quote divergence per ADR-050; operator action points at the convention catalogue at `src/blive/adapters/eodhd/conventions.py`. Forward-list of KB-3 §8 codes (100 / 322 / 354 / 366 / 1100..1102 / 1300) remains for later promotion. **M3.5 (v0.10):** error 10141 (paper-trading disclaimer on Gateway restart) promoted from the reconnect drill; 1100/1101/1102 stay forward-listed (no typed connectivity handler yet — M5). | DESIGN |

---

## 4. Data Dictionaries (DDs)

Schema-level documentation. Each `docs/dd/<name>.md` lists every field with type, semantics, invariants, sample, lineage.

| Id | File | Status | Coverage | Needed by |
|----|------|--------|----------|-----------|
| **DD-1** | [`docs/dd/domain_objects.md`](./docs/dd/domain_objects.md) | STABLE v0.3 (2026-06-05) | 11 types: Instrument, Bar, Trade, Order, Fill, OrderEvent, Position, AccountSnapshot, OrderUpdate, ConnectionStatus, BrokerEvent (alias). Plus 7 enums (OrderSide/Type/TIF/State/EventKind, AssetClass, Severity) and the `Tradability` literal alias (`spot`/`cfd`/`spread_bet`) added at v0.2 per [ADR-037](./docs/decisions/DECISIONS.md#adr-037--instrumenttradability-field-spot--cfd--spread_bet). Field-level invariants enforced in `__post_init__`. **v0.3 (M3.4)**: §2.8 AccountSnapshot mixed-currency footnote — `equity` is the consolidated `BASE` total, not a per-currency sleeve (live-confirmed GBP+USD on IB `DUP886336`; the M3.4 equity-bug fix). | DESIGN |
| **DD-2** | [`docs/dd/event_schemas.md`](./docs/dd/event_schemas.md) | DRAFT v0.2 (2026-05-01) | Field-level for `OrderEvent` / `ConnectionStatus` (M0), `RiskBreach` (M1), `AccountUpdate` (M2-IB.3b-i; per ADR-033), `ArtefactFreshnessWarning` (M2-IB.3b-i; per ADR-022). All implemented in `blive.domain.events`. M4/M5/M7 events catalogued in INV-5 but not yet detailed. | DESIGN |
| **DD-3** | [`docs/dd/config_schemas.md`](./docs/dd/config_schemas.md) | DRAFT v0.2 (2026-04-27) | `LiveStrategyConfig` + 6 sub-objects (`LiveOverrides`, `LiveBorrowProvider`, `LiveFinancingProvider`, `LiveKillSwitch`, `ArtefactPaths`, `RiskOverrides`); merge order; worked `tkan_v4_momentum_timing_1x` example. M1 RC subset only; M4-tier RC keys forward-compat-ignored. **v0.2 (M2-IG.2 amendment per ADR-034)**: top-level `broker: Literal["paper","ig","ib"]` (default `"paper"`) + optional per-broker config blocks `paper_config` / `ig_config` / `ib_config`. | DESIGN |
| **DD-4** | `docs/dd/storage_schemas.md` | MISSING | SQLite DDL for every table, indexes, migrations | DESIGN, M4 |
| **DD-5** | `docs/dd/api_schemas.md` | MISSING (eventually OpenAPI) | REST request/response schemas | M6 |
| **DD-6** | `docs/dd/metric_schemas.md` | MISSING | Prometheus metric definitions in code-checkable form | M7 |
| **DD-7** | [`docs/dd/instrument_dictionary.md`](./docs/dd/instrument_dictionary.md) | STABLE v1.5 (2026-06-05) | `Instrument` field-by-field map to IB `Contract`; `AssetClass` → `secType` table; `venue` (MIC) → IB `exchange` table (Phase 1: `XPAR → SBF`); §3.1 Yahoo-suffix → MIC sub-table (per ADR-041); ConID lazy lookup + in-memory cache; ambiguity discipline. **v1.0 (M2-IB.3a-resolved)**: STABLE flip — Phase 1 path empirically validated (CAC.PA → conId=11183823 via probe 2026-05-01). **v1.1 (M2-IB.5)**: §3 grew `primaryExchange` column (US-SMART). **v1.2 (M2-IB.6.1)**: XLON row "Used by" updated for Phase 1 PRIIPs. **v1.3 (M2-IB.6 close)**: XLON row split by `asset_class` (XLON+ETF → SMART/LSEETF; XLON+EQUITY → LSE direct) per ADR-048. **v1.4 (M3.1)**: footnote on EODHD-vs-IB unit-of-quote convention layer per ADR-050 — `Instrument` stays vendor-neutral; conversion lives at the pipeline boundary in `blive.adapters.eodhd.conventions`. | DESIGN |
| **DD-8** | [`docs/dd/ig_instrument_dictionary.md`](./docs/dd/ig_instrument_dictionary.md) | DRAFT v0.1 (2026-04-27) | `Instrument` field-by-field map to IG epic; epic taxonomy (`IX.D.{symbol}.{mode}.IP` family + KC, CS, CC, etc.); `AssetClass × tradability` → IG epic family table (Phase 1: `INDEX × cfd` → `IX.D.CAC40.CASH.IP` guess); epic resolution via `/markets/{epic}` lookup with `/markets?searchTerm=…` fallback; per-instrument precision lookup consumed by Sizer per [ADR-037](./docs/decisions/DECISIONS.md#adr-037--instrumenttradability-field-spot--cfd--spread_bet). Substrate for [ADR-039](./docs/decisions/DECISIONS.md#adr-039--phase-1-strategy-under-ig-bridge-cac-40-cfd); STABLE flip on first successful resolution against IG demo at M2-IG.3. | DESIGN |

---

## 5. Decision & Question Logs

| Id | File | Status | Purpose |
|----|------|--------|---------|
| **DEC** | `docs/decisions/DECISIONS.md` | MISSING | ADR-NNN entries, append-only with supersede chain |
| **OQ** | `docs/decisions/OPEN_QUESTIONS.md` | MISSING | OQ-NNN entries, each with target resolution date + depends-on |

**ADR seed list** (drafts to write at the same time as the file is created):

- ADR-001 — Project name `blive` (rationale: pairing with `btest`).
- ADR-002 — Adopt `ib_async` v2.1+ as wire-level driver behind a single adapter.
- ADR-003 — Borrow architecture from NautilusTrader, do not depend on it.
- ADR-004 — Hexagonal ports/adapters with import-linter enforcement.
- ADR-005 — Single-process, single-asyncio-loop kernel for v1.
- ADR-006 — SQLite for persistence in v1; Postgres migration deferred.
- ADR-007 — In-process event bus for v1; Redis Streams as opt-in.
- ADR-008 — RiskEngine no-bypass: architectural enforcement.
- ADR-009 — Crash-only design; restart path = cold-start path.
- ADR-010 — Reuse `btest`'s `FactorEngine`/`SignalEngine`/`PortfolioEngine` by import; vendor specific modules only on upstream-break.
- ADR-011 — 3-page minimal web UI; mobile and OAuth deferred.
- ADR-012 — Parity diagnostic is mandatory daily; degraded mode if broken.

**OQ seed list** (12 items already in REQUIREMENTS §16, ready to externalize on creation).

---

## 5.5 Retrospectives (RETRO-M{N})

Frozen per-milestone records per [ADR-024](./docs/decisions/DECISIONS.md#adr-024--add-session-retrospective-artefact-type). Lifecycle: `DRAFT → STABLE` only.

| Id | File | Status | Closes | Notes |
|----|------|--------|--------|-------|
| **RETRO-template** | [`docs/retros/_template.md`](./docs/retros/_template.md) | STABLE | — | template; copy to `M{N}_retrospective.md` at milestone close |
| **RETRO-M0** | [`docs/retros/M0_retrospective.md`](./docs/retros/M0_retrospective.md) | STABLE v1.0 (2026-04-26) | M0 (G1 PASSED) | M0 close: substrate (DD-1, INV-13, INV-5, INV-6) + domain code + paper/memory/clock adapters + 113 tests + import-linter rule with negative test |
| **RETRO-M1** | [`docs/retros/M1_retrospective.md`](./docs/retros/M1_retrospective.md) | STABLE v1.0 (2026-04-27) | M1 (G2 PARTIAL) | M1 close: ADR-027..029 ACCEPTED; DD-3 → DRAFT; INV-5/INV-6 → STABLE; OQ-030 raised; strategy loader / Sizer / RiskEngine M1-subset / PaperMarketData / LogAlert / PaperBroker.replace / paper-mode pipeline; 175 tests + CI smoke-import; G2 real-data ±1 bps deferred to operator EODHD+TKAN run |
| **RETRO-M2-IG** | [`docs/retros/M2-IG_retrospective.md`](./docs/retros/M2-IG_retrospective.md) | STABLE v1.0 (2026-04-28) | M2-IG bridge (G3-IG NOT_REACHED — operator-driven close, not gate failure) | IG bridge close at architectural surface: ~2 sessions delivered M2-IG.1 substrate + M2-IG.2 cross-cutting infra + M2-IG.3 read side + M2-IG.4 minimum-viable submit; 359 tests; 7 tags. ADR-030/033/034..039 ACCEPTED; ADR-031/032 stay PROPOSED for M2-IB. M2-IG.5 strategy run + production Lightstreamer wrapper DEFERRED (no scheduled revival). Phase 1 strategy reverts to ADR-021 ETF on IB Paper. Recommendations §"NEXT_PROMPT v0.4" maps M2-IG file structure 1:1 onto M2-IB equivalents. |
| **RETRO-M2-IB** | [`docs/retros/M2-IB_retrospective.md`](./docs/retros/M2-IB_retrospective.md) | STABLE v1.0 (2026-05-06) | M2-IB (G3-IB-A3 PASSED at architectural surface; OQ-031 deferred to M3) | M2-IB close across the .1 → .6 ladder: substrate (.1) → IBClient + credentials (.2) → resolver / read / market-data / 30s account-update timer (.3) → write-side FSM + REJECTED disambiguation + happy-path bypass + post-acceptance fix (.4) → CAC.PA single-instrument architectural surface (.5) → Phase 1 A3 substrate switch → multi-instrument pipeline + 5-ticker EODHD + LongShortPortfolio dispatch + IB SMART (.6.1) → US-RTH PRIIPs validation + broker errorEvent fix (.6.2a) → LSE-RTH first IB-paper FILL (.6.2b) → IB warning 2161 PMA-cap investigation + ADAPTIVE_MKT (.6.2c) → close. ADRs raised: 042..049. Three milestone-defining surprises: ADR-021/CAC.PA SUPERSEDED for A3 / ADR-047 PRIIPs/KID for UK retail / ADR-049 PMA-cap is structural for retail leveraged ETPs regardless of order type. OQ-031 carried into M3 for deployment decision. |
| **RETRO-M3** | [`docs/retros/M3_retrospective.md`](./docs/retros/M3_retrospective.md) | STABLE v1.0 (2026-06-05) | M3 (Phase 1 deployment-decision; G4 PASSED) | M3 close across M3.1 → M3.6: unit-of-quote (ADR-050) + tick-grid (ADR-051); bounded M3.2 capture; **OQ-031 RESOLVED Option 1 (ADR-052)** + OQ-032 raised (the leverage *trilemma* — PRIIPs / PMA / Cash); M3.4 mixed-currency P&L (found + fixed the `equity`-reads-base-sleeve bug); M3.5 chaos drill + KB-7 (IB 10141 + the M5 reconnect gap); KB-2 / KB-3 STABLE. Three surprises: the unit-of-quote bug was *two* bugs (magnitude + tick-grid); the OQ-031 option set omitted the leverage-preserving margin path (operator caught it); M3.4 caught a real ~10% equity understatement. G4 PASSED (all 10). Phase 1 complete. |

---

## 6. Lifecycle Tags — what's needed when

To avoid premature elaboration, each artifact is tagged by which lifecycle stage *blocks on it*. Earlier stages must complete before later ones, but artifacts can be drafted ahead.

### 6.1 Needed NOW to finalize REQUIREMENTS (v0.1 → v1.0)

These are the gaps that turn confident-sounding claims in REQUIREMENTS into facts:

| Artifact | What it unblocks in REQUIREMENTS |
|----------|---------------------------------|
| **KB-5 strategy_taxonomy** | §1, §3, §5, §15 — without knowing the actual strategy mix, scope decisions are guesses |
| **KB-1 btest_dsl_inventory** | §5.1 reuse claims; §8 parity contract |
| **KB-2 ib_capability_matrix** | §5.3 order types; §10 gotchas; §15 out-of-scope |
| **KB-3 ib_pacing_spec** | §5.5 rate-limit defaults; §10 gotcha mitigations |
| **KB-4 frameworks_survey** | §9 (move detail out of REQUIREMENTS body) |
| **KB-6 cost_margin_dictionary** | §8 parity envelopes (numbers need derivation, not guess) |
| **KB-9 uk_regulatory** | §6.3 audit/security requirements |
| **KB-13 companion_projects** | §1, §3 (boundaries with btest/harp) |
| **KB-12 GLOSSARY extracted** | every section depends on consistent terminology |
| **KB-10 DECISIONS bootstrap** (ADR-001..012) | makes REQUIREMENTS skim-friendly by referencing ADRs instead of repeating rationale |
| **KB-11 OPEN_QUESTIONS** | externalize §16 |
| **INV-1 strategies** | §1 scope |
| **INV-4 risk_checks** | §5.5 |
| **INV-10 asset_classes** | §15 out-of-scope |

### 6.2 Needed for DESIGN (M0–M2)

KB-7 failure_modes (full), KB-15 parity_methodology, all DDs (DD-1..7), INV-2/3/5/6/8/13/14.

### 6.3 Needed for IMPLEMENTATION (M2–M6)

INV-7, INV-9, DD-5, KB-8 operational_events.

### 6.4 Needed for OPERATIONS (M6+)

`RUNBOOK.md`, INV-12, full OpenAPI, monitoring dashboard JSON.

---

## 7. File Layout

```
blive/
  README.md                                  ← short overview, links to everything
  REQUIREMENTS.md                            ← v0.2 DRAFT (current)
  CONTEXT_INVENTORY.md                       ← this file
  CONTEXT_PROTOCOL.md                        ← v0.2 DRAFT (the discipline)
  TASK_REGISTRY.md                           ← v0.1 DRAFT (Phase 1 plan)
  NEXT_PROMPT.md                             ← session kickoff prompt
  DESIGN.md                                  ← future (post-REQUIREMENTS freeze)
  TASK_REGISTRY.md                           ← future
  RUNBOOK.md                                 ← future
  CLAUDE.md                                  ← STABLE v1.0; session-bootstrap pointer per ADR-042
  docs/
    GLOSSARY.md                              ← KB-12
    kb/
      btest_dsl_inventory.md                 ← KB-1
      ib_capability_matrix.md                ← KB-2
      ib_pacing_spec.md                      ← KB-3
      frameworks_survey.md                   ← KB-4
      strategy_taxonomy.md                   ← KB-5
      cost_margin_dictionary.md              ← KB-6
      failure_modes.md                       ← KB-7
      operational_events.md                  ← KB-8
      uk_regulatory.md                       ← KB-9
      companion_projects.md                  ← KB-13
      parity_methodology.md                  ← KB-15
    PHASE_1_READINESS.md                     ← Phase 1 readiness audit (STABLE v0.1)
    PHASE_2_READINESS.md                     ← Phase 2 readiness audit (DRAFT v0.1)
    retros/
      _template.md                           ← RETRO frontmatter + sections
      M{N}_retrospective.md                  ← per-milestone (created at M_{N} close)
    method/
      paper/cognitive_cartography.tex        ← canonical paper source
      paper/references.bib                   ← bibliography
      Amendments_Log.md                      ← methodology amendments staging for paper iteration
      Research_Plan_for_Paper_Iteration_*.md ← research plans informing iterations
    decisions/
      DECISIONS.md                           ← KB-10
      OPEN_QUESTIONS.md                      ← KB-11
      adr/
        ADR-001-name-blive.md                ← optional one-file-per-ADR variant
        ADR-002-adopt-ib-async.md
        ...
    inv/
      strategies.md                          ← INV-1
      order_types.md                         ← INV-2
      tif_values.md                          ← INV-3
      risk_checks.md                         ← INV-4
      domain_events.md                       ← INV-5
      ports_adapters.md                      ← INV-6
      rest_endpoints.md                      ← INV-7
      metrics.md                             ← INV-8
      alerts.md                              ← INV-9
      asset_classes.md                       ← INV-10
      modes.md                               ← INV-11
      backup_artifacts.md                    ← INV-12
      order_state_transitions.md             ← INV-13
      ib_error_codes.md                      ← INV-14
    dd/
      domain_objects.md                      ← DD-1
      event_schemas.md                       ← DD-2
      config_schemas.md                      ← DD-3
      storage_schemas.md                     ← DD-4
      api_schemas.md                         ← DD-5
      metric_schemas.md                      ← DD-6
      instrument_dictionary.md               ← DD-7
```

Two structural choices to note:

- **One file per ADR** (`docs/decisions/adr/ADR-NNN-slug.md`) is more scalable than one big DECISIONS.md once we cross ~10 ADRs. The DECISIONS.md becomes the index. We may start in one file and split later.
- **All inventories and DDs live under `docs/`** so they don't clutter the project root. Only the ~6 living top-level docs (README, REQUIREMENTS, CONTEXT_INVENTORY, DESIGN, TASK_REGISTRY, RUNBOOK, CLAUDE) sit at the root.

---

## 8. Standard Header for Every Artifact

Every KB / INV / DD / ADR file starts with this YAML-ish frontmatter so an agent can scan ownership and freshness without reading the body:

```markdown
---
id: KB-2
title: IB Capability Matrix
status: DRAFT          # MISSING | DRAFT | STABLE | STALE | DEPRECATED
owner: Claude
last_reviewed: 2026-04-26
sources:
  - https://interactivebrokers.github.io/tws-api/...
  - https://www.interactivebrokers.com/campus/...
depends_on: []         # other artifact ids this references
referenced_by:         # backlinks; can be auto-generated
  - REQUIREMENTS.md §10
  - DESIGN.md §IB
---
```

---

## 9. Maintenance Rules

1. **CONTEXT_INVENTORY.md is the index of indexes.** Adding a new KB/INV/DD/ADR/OQ requires a row update here in the same commit.
2. **Status field is mandatory** on every artifact and must be one of the five values listed above.
3. **`STABLE` artifacts** are reviewed at every milestone freeze; if last_reviewed is older than the most recent freeze, status auto-degrades to `STALE`.
4. **Decision log is append-only.** Reverse a decision via a new ADR with `Supersedes: ADR-NNN`; never edit the original.
5. **Inventories must be machine-checkable** where feasible: a test asserts every IB error code in code is listed in `INV-14`, every metric in code is in `INV-8`, etc. Drift detected at CI time, not in production.
6. **Cross-references use stable ids** (KB-N, INV-N, DD-N, ADR-N, OQ-N), not file paths. File paths can be reorganized; ids should not.
7. **The Glossary (KB-12) is authoritative.** If two artifacts disagree on a term, the Glossary wins or both are wrong; conversation is required.
8. **Every artifact links its sources.** Especially KBs sourced from external docs: link with date accessed.

---

## 10. Priority Queue — what to write next

Ordered by what unblocks REQUIREMENTS finalization:

**Latest reconciliation (2026-06-05 / M3 CLOSED — G4 PASSED):** Phase 1 (M0 → M3) is **complete**. M3.6 flipped **KB-2 / KB-3 → STABLE v1.0** (Phase-1 surface; stale DD-7/INV-14 refs fixed; 2161/Adaptive + ADR-040 + KB-7-reconnect findings folded in). [RETRO-M3](./docs/retros/M3_retrospective.md) written + frozen (G4 PASSED on all 10 exit criteria). The M3 arc: ADR-050/051 (unit-of-quote magnitude + tick-grid — *two* entangled error-110 causes) → bounded M3.2 capture (QQL3 0/69 vs IBTM 6/6) → **ADR-052** (OQ-031 Option 1 — accept the non-fill) + **OQ-032** (the leverage *trilemma*: PRIIPs / PMA / Cash each block leveraged equity exposure) → **M3.4** (found + fixed the `AccountSnapshot.equity`-reads-base-sleeve bug, ~10% understatement on the live mixed-currency account) → **M3.5** (chaos drill → KB-7 FM-1 + IB 10141; native auto-reconnect = M5) → **M3.6** (KB-2/KB-3 STABLE). Tests 591; all gates green (formatters pinned). M3 → M4 is the Phase 1 → Phase 2 boundary; per [§8.3.2](./CONTEXT_PROTOCOL.md) the next two sessions are a **readiness-audit refresh** ([NEXT_PROMPT](./NEXT_PROMPT.md) v1.5) then **plan-drafting** (OQ-032 + the VIX/TQQQ/VXX notebook). **Next active path: Phase-2 readiness audit (substrate-only).**

**Prior reconciliation (2026-06-05 / M3.5 chaos drill + KB-7 stub):** A controlled IB Gateway stop/start drill (`scripts/probe_ib_reconnect.py`; operator stopped + restarted the live paper Gateway) substituted for the 23:45 ET restart (streamlined-clean). **Observed:** the broker does **not** auto-detect an unexpected drop — `IBBroker.is_connected` (cached) stayed stale-`True` while `ib.isConnected()` went `False` (no `disconnectedEvent` handler); recovery needs `disconnect()+connect()`; the restart surfaced **IB error 10141** (paper-trading disclaimer) + a transient `clientId 1 already in use`; on reconnect positions reconciled with the pre-drop baseline. The recovery path + reconciliation work via an external driver; native detect / auto-reconnect / continuous reconciliation = **M5** (REQUIREMENTS §5.7). Substrate: **KB-7 `failure_modes` MISSING → DRAFT v0.1** (FM-1); **INV-14 v0.9 → v0.10** (10141 promoted; 1100/1101/1102 stay forward-listed); new fixture `scripts/probe_ib_reconnect.py`. **G4 exit-criteria #5 (chaos) + #6 (Phase 2 stubs KB-7/KB-15/INV-8/INV-9 all DRAFT) ✓ MET.** Tests unchanged at 591 (manual fixture). **Next active path: M3.6 — KB-2 / KB-3 STABLE flip → M3-close (RETRO-M3 + G4 report).**

**Prior reconciliation (2026-06-05 / M3.4 mixed-currency P&L — found + fixed equity bug):** M3.4 run live against IB Paper `DUP886336` under the streamlined-clean posture. Reconciling the existing mixed state (USD cash + GBP-hedged sleeve) — no QQL3 position needed (OQ-031/ADR-052: it can't fill) — surfaced a real read-side defect: `AccountSnapshot.equity` read `NetLiquidationByCurrency[base_currency]` (the GBP **sleeve**, £902,839) not the consolidated `BASE` total (£1,003,886), dropping the ~£101k USD sleeve. **Fixed** (`IBBroker._build_account_snapshot` BASE-primary; `_infer_base_currency` hardened to the unit-`ExchangeRate` signal) + a mixed-currency regression test + new `scripts/probe_ib_account_ccy.py` diagnostic; DD-1 §2.8 v0.2 → v0.3; re-confirmed live (equity £1,003,855). **Bug-fix, no ADR** (DD-1 already specified equity = total NAV). Tests 590 → 591; all gates green. G4 exit-criterion #4 ✓ MET (wording amended "QQL3 position" → "USD exposure"). The pre-existing M2-IG-era full-tree black/isort drift was cleared in a separate hygiene commit (`5166e20`; formatters pinned `black==26.3.1` / `isort==8.0.1`). **Next active path: M3.5 — controlled Gateway stop/start drill + KB-7 stub.**

**Prior reconciliation (2026-06-05 / M3.3 OQ-031 resolved):** The operator resolved [OQ-031](./docs/decisions/OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account) on the M3.2 capture with **Option 1** — Phase 1 **accepts** the PMA-bound leveraged-leg non-fill (QQL3 0/69 fills = 0% vs IBTM 6/6 = 100%; 2161 cap-binding 0; zero rejects/breaches/error-110) as a deployment characteristic; **no code change**, live behaviour Treasury-leg-dominated. Recorded as [ADR-052](./docs/decisions/DECISIONS.md#adr-052--phase-1-accepts-the-pma-bound-leveraged-leg-non-fill-oq-031-option-1) (ACCEPTED, drafted PROPOSED then confirmed same-session); OQ-031 OPEN → RESOLVED-BY-ADR-052; G4 exit-criterion #1 ✓ MET. The leveraged-leg redesign is deferred to Phase 2 as **OQ-032** — its option set carries the *full* design space, including the leverage-preserving **margin-on-a-1×-UCITS** path (≈3× via 3:1 margin on a low-volatility UCITS that likely dodges the volatility-triggered PMA cap, per [ADR-016](./docs/decisions/DECISIONS.md#adr-016--leverage-support-both-margin-financed-and-leveraged-etf-instruments)) that the four OQ-031 options had omitted; the honest scope is a *trilemma* (PRIIPs blocks US leveraged ETPs, PMA blocks UK ones, Cash blocks margin-leverage). `refined-by: ADR-052` backref added to ADR-043 + ADR-047 (QQL3 leg provisional). Substrate: DECISIONS v0.22 → v0.23; OPEN_QUESTIONS v0.4 → v0.5; TASK_REGISTRY v0.11 → v0.12; CONTEXT_INVENTORY v0.19 → v0.20; [NEXT_PROMPT](./NEXT_PROMPT.md) v1.3 → v1.4. No code change; tests unchanged at 590. **Next active path: M3.4 — mixed-currency P&L reconciliation.**

**Prior reconciliation (2026-06-05 / M3.2 capture-complete):** M3.2's bounded-capture criterion is **MET** on the live IB-Paper + EODHD wire (LSE RTH). A `--max-bars 5` smoke first validated the chain end-to-end (real IBTM fill, sink row written), then two flip-spanning captures (`max-bars 40` + `60`, 2 flips each) landed in `~/.blive/data/m3_2_window/runs.jsonl`: **QQL3 0 / 69 fills (0%), IBTM 6 / 6 (100%), 2161 cap-binding 0, zero rejects / breaches / error-110** — the empirical OQ-031 signal (the leveraged equity leg doesn't fill; the Treasury leg does; ADAPTIVE_MKT didn't trip the *visible* cap yet QQL3 still didn't fill). New `scripts/flatten_ib_paper.py` added + used to reset the accumulated paper IBTM (230 → 0). M3.2 data deliverable done. Substrate: CONTEXT_INVENTORY v0.18 → v0.19; TASK_REGISTRY v0.10 → v0.11; [NEXT_PROMPT](./NEXT_PROMPT.md) v1.2 → v1.3. No new ADRs / OQs (capture + flatten are operational; OQ-031's *resolution* is M3.3 and gets its own ADR). **Next active path: M3.3 — OQ-031 resolution** (operator-led deployment-mode decision on the captured evidence).

**Prior reconciliation (2026-06-05 / M3.2 results-capture + re-scope):** M3.2's **code deliverables landed this commit** — the per-run results sink ([`src/blive/runtime/m3_2_record.py`](./src/blive/runtime/m3_2_record.py) → `~/.blive/data/m3_2_window/runs.jsonl`), the additive capture surface on `IBMultiRunResult` / `IBBroker` / `runtime.signals`, and INV-8 `metrics` + INV-9 `alerts` MISSING → DRAFT v0.1 (M3.2-only stubs). Tests 568 → 590; mypy `src` / black / isort / lint-imports all green. No new ADRs / OQs (the sink shape is a refinement per [NEXT_PROMPT](./NEXT_PROMPT.md)). **M3.2 then re-scoped (same session, operator call, TASK_REGISTRY plan-call #6): "10 LSE-RTH calendar trading days" → bounded deterministic capture** — regime variety from the replay window (`--max-bars`, offline-verifiable via the new `--dry-run`; `--max-bars 60` spans 2 flips), QQL3's ≈0 fill-rate under the 2161 cap already structural. Close criterion: ≥1 RTH capture run over a flip-spanning window (QQL3 ≈0 + IBTL/IBTM fills); **operator-driven, remains OPEN until that row exists**; M3.3 (OQ-031) then consumes `runs.jsonl`. (The M3.1 + M3.1b CLOSED history is in the v0.19 banner above.) Next active path (superseded by the capture-complete note above): **M3.2 bounded capture (operator) → M3.3**.

**Prior reconciliation (2026-05-06 / M3 plan-drafted):** `TASK_REGISTRY.md` v0.5 → v0.6 written this session as the third (and final) of the three [CONTEXT_PROTOCOL §8.3.2](./CONTEXT_PROTOCOL.md) phase-boundary sessions. Legacy "M3 — IB Adapter (Write Side)" section replaced with the **deployment-decision M3** plan (sub-milestones M3.1 EODHD-vs-IB unit-of-quote reconciliation → M3.2 10-day empirical paper-mode window → M3.3 OQ-031 resolution → M3.4 mixed-currency P&L reconciliation → M3.5 INV-14 extension + chaos drills → M3.6 KB-2 / KB-3 STABLE flip → M3-close). Five plan-drafting calls recorded inline (Q1 inform-then-resolve / Q2 10-day calendar-bound window / Q3 EODHD-vs-IB pull forward to M3 / Q4 A3-only / Q5 stub-DRAFT only what M3 produces). G4 gate rewritten around the 10 deployment-decision exit criteria. Sketched M4+ refreshed (M4 picks up RC-01..RC-07 + RC-11; M5 loses Phase 2 readiness audit; M5/M7 stub-DRAFT framings shift to "extends M3's stub"). Risk register grows six Phase-2-entry rows. No new ADRs / OQs raised — substrate-only session. M2 → Phase 2 transition's §8.3.2 three-session pattern fully discharged. Next active path: **M3.1 — EODHD-vs-IB unit-of-quote reconciliation** (kickoff prompt at NEXT_PROMPT v1.0).

**Prior reconciliation (2026-05-06 / Phase 2 readiness audit complete):** [`PHASE_2_READINESS.md`](./docs/PHASE_2_READINESS.md) DRAFT v0.1 written as the second of the three §8.3.2 phase-boundary sessions. Eight-dimension audit informed by M2-IB.6's real wire outcomes (PRIIPs / KID hard block, LSE-ETF SMART discriminator, structural PMA-cap on UK retail leveraged ETPs). Five cross-cutting questions raised as the agenda for the M3 plan-drafting session.

**Prior reconciliation (2026-05-06 / M2-IB.6 closed):** M2-IB.6 closed at the LSE-RTH wire run on Wed 2026-05-06 09:33 BST — first IB-paper FILL on M2-IB.6 landed (IBTM, 19 × £128.5) via the ADR-048 SMART/LSEETF routing. Investigation of IB warning 2161 (Price Management Algo regulatory disruptive-orders cap) on the QQL3 leg empirically confirmed the cap binds structurally on UK retail accounts regardless of order type — captured in [INV-14 v0.7](./docs/inv/ib_error_codes.md), [OQ-031](./docs/decisions/OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account), and [ADR-049](./docs/decisions/DECISIONS.md#adr-049--ordertypeadaptive_mkt-for-ibalgo-adaptive-routing-empirical-pma-cap-finding). Operator decided to address OQ-031 in M3 rather than block M2-IB.6 close. ADR-048 + ADR-049 flipped PROPOSED → ACCEPTED. RETRO-M2-IB written + frozen.

**Done this session (2026-04-26)**:

- ~~**KB-5 `strategy_taxonomy.md`**~~ — DRAFT v0.1.2.
- ~~**KB-11 `OPEN_QUESTIONS.md`**~~ — DRAFT v0.1.2 (now includes OQ-023..027 sub-questions raised in PHASE_1_READINESS).
- ~~**KB-10 `DECISIONS.md`**~~ — DRAFT v0.1. ADR-001..019 ACCEPTED.
- ~~**REQUIREMENTS.md v0.2**~~ — applied KB references; collapsed inline survey/OQs/glossary into pointers.
- ~~**`docs/PHASE_1_READINESS.md`**~~ — eight-dimension readiness audit; gates Phase 1 plan.
- ~~**`TASK_REGISTRY.md`**~~ — DRAFT v0.1, Phase 1 plan with M0–M3 detailed and G0–G4 gates.

**Outstanding queue (in order)**:

1. ~~Operator confirmation of OQ-024..OQ-027.~~ ✓ Done 2026-04-26; ADR-020..023 added; G0 gate **PASSED**.
2. ~~**M0 execution**~~ ✓ Done 2026-04-26. **G1 gate exit criteria met** — see [RETRO-M0](./docs/retros/M0_retrospective.md).
3. ~~**M1 execution**~~ ✓ Done 2026-04-27. ADR-027..029 ACCEPTED; DD-3 → DRAFT; INV-5/INV-6 → STABLE; OQ-030 raised; strategy loader / Sizer / RiskEngine M1-subset (RC-08/09/12/13) / PaperMarketData / LogAlert / PaperBroker.replace() / paper-mode pipeline shipped; 175 tests green; CI smoke-import for btest engines added. RETRO-M1 written. **G2 gate criteria 1–4: see [RETRO-M1](./docs/retros/M1_retrospective.md) for partial-pass detail (synthetic-fixture parity green; full real-data ±1 bps test deferred to operator-driven `tests_slow/g2_parity` run with EODHD CAC.PA + TKAN artefact).**
4. **Operator-side prereqs for G2 → M2**:
   - IB Paper account commissioned (operator). **OPEN.**
   - **EODHD subscription for CAC.PA** — ✓ **verified 2026-04-27** (CAC.PA daily EOD + delayed real-time quotes confirmed in tier). Open small follow-up for M2: correct CAC-40 *index* ticker on EODHD (try `PX1.INDX` / `^FCHI`); not a G2 blocker since [ADR-021](./docs/decisions/DECISIONS.md#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) trades the ETF.
   - Docker host decision (Linux VM vs Windows). **OPEN.**
   - **Real-data G2 ±1 bps parity run** — pipeline ready; needs EODHD CAC.PA daily history fixture + TKAN `pred_cache.pkl` + `cact_momentum.parquet`. **OPEN.** EODHD CAC.PA path now confirmed; the fetch script for the fixture is itself an M2 deliverable per [NEXT_PROMPT.md](./NEXT_PROMPT.md) v0.3.
5. ~~**M2-IB substrate phase**~~ ✓ Committed 2026-04-27 at `M2-substrate-IB.checkpoint` (ADR-030..033 PROPOSED; DD-7/DD-2/KB-8 DRAFT; KB-2/KB-3 v0.1.1 review pass).
6. ~~**M2-IB execution** — PARKED 2026-04-27 pending operator's IB Paper account reopening. Resumes when IB account ready and M2-IG bridge has stabilised.~~ **Superseded by item 13** (M2-IB unparked 2026-04-28; IB Paper account commissioned 2026-04-28, enabled 2026-04-29). Historical record kept for traceability.
7. ~~**M2-IG.1 batch 1 substrate**~~ ✓ Committed 2026-04-27 at `M2-IG.1-batch1` (ADR-034 multi-broker registry, ADR-035 secrets handling, TASK_REGISTRY v0.2 milestone restructure).
8. ~~**M2-IG.1 batch 2 substrate**~~ ✓ Committed 2026-04-27 at `M2-IG.1-batch2`.
9. ~~**M2-IG.2 cross-cutting infra code**~~ ✓ Committed 2026-04-27 at `M2-IG.2-complete` (rate limiter + credentials + broker_registry + DD-1/DD-3/INV-6/KB-8 amendments + new import-linter contract + secrets/ scaffolding).
10. ~~**M2-IG.3 read side**~~ ✓ Committed 2026-04-28 at `M2-IG.3-readside-complete` (IGClient + IGInstrumentResolver + IGBroker read + IGMarketData REST + Lightstreamer abstraction; production wrapper deferred).
11. ~~**M2-IG.4 minimum-viable submit**~~ ✓ Committed 2026-04-28 at `M2-IG.4-market-submit` (IGBroker.submit MARKET path; cancel/replace deferred to working-order Phase 2 needs).
12. ~~**M2-IG.5 strategy run + RETRO-M2-IG**~~ ⚠ **Bridge closed 2026-04-28 at architectural surface**: retro half done at [`docs/retros/M2-IG_retrospective.md`](./docs/retros/M2-IG_retrospective.md); strategy-run half DEFERRED with no scheduled revival (operator pivoted to M2-IB resumption with the IB Paper account becoming available 2026-04-29). Production Lightstreamer wrapper, ig_pipeline.py, 5-day demo run all parked.
13. **M2-IB resumption (current active path)** — sub-milestones M2-IB.1 (substrate at `M2-substrate-IB.checkpoint`) / .2 (IBClient + IBCredentials) / .3 (IBInstrumentResolver + IBBroker read + IBMarketData) / .4 (write side + reconciliation, optionally consolidated with M3) / .5 (strategy run on IB Paper for ≥ 5 trading days + RETRO-M2-IB). Mirror M2-IG file structure 1:1 per [RETRO-M2-IG §"Recommendations"](./docs/retros/M2-IG_retrospective.md#recommendations-for-next_promptmd-v04-m2-ib-resumption). Reuse `blive.adapters.shared.{rate_limiter, credentials}` + `runtime.broker_registry` unchanged. ADR-031 + ADR-032 flip PROPOSED → ACCEPTED on first IB exercise; DD-7 / KB-2 / KB-3 STABLE flip on first IB Paper handshake. See [`NEXT_PROMPT.md`](./NEXT_PROMPT.md) v0.4 for the kickoff prompt.
    - ~~**M2-IB.1 — Substrate verification.**~~ ✓ Committed 2026-04-28 at tag `M2-IB.1-substrate-verified` (INV-6 STABLE v0.3.1; PARKED markers removed; IG rows MISSING → DRAFT-architectural; CONTEXT_INVENTORY §10 item 6 superseded).
    - ~~**M2-IB.2 — IBClient + IBCredentials.**~~ ✓ Committed 2026-04-28 at tag `M2-IB.2-client-credentials` (`blive.adapters.ib.{credentials, client, rate_limiter, __init__}` + 34 unit tests against `AsyncMock(spec=ib_async.IB)`; ADR-031 PROPOSED → ACCEPTED; KB-10 v0.9 → v0.10).
    - ~~**M2-IB.3-prereq — operator-side closure.**~~ ✓ Closed 2026-05-01 at tag `M2-IB.3-prereq-confirmed`. ADR-040 (Phase 1 deployment target = Windows native IB Gateway) ACCEPTED 2026-04-28. `~/.blive/secrets/ib.env` populated by operator. `scripts/probe_ib_handshake.py` ran clean — connected to IB Paper Gateway in 0.53s (well under the G3-IB 5s target); rate limiter consumed + refilled correctly; clean disconnect. The wire is alive.
    - ~~**M2-IB.3a — IBInstrumentResolver (architectural surface).**~~ ✓ Tag `M2-IB.3a-resolver` 2026-05-01. `IBInstrumentResolver` shipped per DD-7 §5 v0.2.
    - ~~**M2-IB.3a-resolved — wire-level validation + substrate flips.**~~ ✓ Tag `M2-IB.3a-resolved` 2026-05-01. Resolve probe ran cleanly against IB Paper (CAC.PA → conId=11183823 in 0.04s; cache hit 0ms). Surfaced + fixed: IB rejects EODHD/Yahoo-style `.PA` suffixes — added Yahoo-suffix translation table per [ADR-041](./docs/decisions/DECISIONS.md#adr-041--yahoo-suffix-translation-in-ib-instrument-resolver) (XPAR/.PA, XLON/.L, XETR/.DE, XAMS/.AS). Substrate flips: ADR-032 PROPOSED → ACCEPTED; ADR-041 PROPOSED → ACCEPTED (same-session); DD-7 v0.2 DRAFT → v1.0 STABLE; KB-10 v0.11 → v0.12 (no PROPOSED ADRs remain).
    - ~~**M2-IB.3b-i — IBBroker read methods.**~~ ✓ Tag `M2-IB.3b-i-broker-read` 2026-05-01. `IBBroker(client, resolver, clock)` ships with connect/disconnect (auto-subscribes via `connectAsync`'s internal `reqAccountUpdatesAsync`), positions / account_snapshot / open_orders, events() iterator emitting `ConnectionStatus`. `submit/cancel/replace` raise `NotImplementedError` (M2-IB.4). Wire-level probe ran clean against IB Paper: equity=£1,000,177 (GBP-denominated UK paper account); 0.51s connect+initial-batch; rate-limiter usage as designed. M2 event types (`AccountUpdate`, `ArtefactFreshnessWarning`) implemented in `blive.domain.events`; INV-5 v0.3, DD-2 v0.2.
    - ~~**M2-IB.3b-i-timer — 30s diff-suppress AccountUpdate emission.**~~ ✓ Tag `M2-IB.3b-i-timer` 2026-05-01. `IBBroker` background task started by `connect` / cancelled by `disconnect`. Per-field thresholds (0.01 currency / 0.001 leverage) per ADR-033. First tick emits baseline; subsequent ticks emit only on above-threshold change. `BrokerEvent` union widened to `OrderEvent | ConnectionStatus | AccountUpdate`. INV-5 v0.3.1. 9 new tests against direct `_account_update_tick` invocation for deterministic diff-suppress verification.
    - ~~**M2-IB.3b-ii — IBMarketData.**~~ ✓ Tag `M2-IB.3b-ii-market-data` 2026-05-01. `IBMarketData(client, resolver, clock)` ships `historical_bars` via `reqHistoricalDataAsync` (KB-3 §2 pacing exercised; BID_ASK doubles tokens). `subscribe_bars` / `subscribe_trades` raise NotImplementedError (M2-IB.5 pipeline integration). `create_ib_broker` + `create_ib_market_data` factories registered in `broker_registry`. **Wire-level findings**: AAPL/NASDAQ historical bars work cleanly via delayed-data tier; `CAC.PA` on SBF returns IB error 162 ("No market data permissions") — **operator-side action**: subscribe to SBF historical data in IB Account Management before M2-IB.5 strategy run. INV-14 (IB error codes) MISSING → DRAFT v0.1 with 162 + 200 catalogued. KB-2 / KB-3 STABLE flip deferred to M2-IB.4 close (write-side §3 / §4 / §6 / §7 surface coverage still needed).
    - ~~**M2-IB.4a-rejected — writeside REJECTED disambiguation wire-validated.**~~ ✓ Tag `M2-IB.4a-rejected` 2026-05-02. `IBBroker.submit/cancel` ship; per-trade FSM via `statusEvent` / `fillEvent` callbacks; `_OrderTrackingState` per-order; `replace()` deferred to M2-IB.4b. New helpers `_last_error_log_entry` + `_rejected_reason_from_log_entry` for the IB Cancelled-with-errorCode → REJECTED disambiguation. Wire probe (`scripts/probe_ib_submit.py`) against IB Paper: CAC.PA direct-routed to SBF tripped error 10311 (precaution); broker correctly emitted REJECTED with reason `"ib:10311 …"`. INV-14 v0.2 catalogued 10311 + 201 + 10147.
    - ~~**M2-IB.4a-happy — SUBMITTED → ACCEPTED → CANCELED on AAPL/SMART.**~~ ✓ Tag `M2-IB.4a-happy` 2026-05-02. Probe-local `_SmartUsResolver` subclass routes US-venue spot equities via SMART (sidesteps the direct-routing precaution). AAPL @ $1.00 LMT BUY against IB Paper: SUBMITTED → ACCEPTED → engine cancel → CANCELED reason='engine'. 202 ("Order Canceled") added to INV-14 v0.3.
    - ~~**M2-IB.4a-happy-cacpa — bypass works, post-acceptance disambiguation fix.**~~ ✓ Tag `M2-IB.4a-happy-cacpa` 2026-05-02. Operator ticked API → Precautions item #1 (master) + #7; probe with `_PHASE_1_INSTRUMENT` (CAC.PA on SBF, direct-routed) reached ACCEPTED on the wire (held until next session per warning 399) and engine-cancel produced CANCELED. Surfaced + fixed a broker bug: post-acceptance Cancelled with errorCode-in-log was wrongly classified REJECTED; fixed by gating disambiguation on `tracking.accepted_emitted`. Code 399 catalogued in INV-14 v0.4. **Bypass for direct-routing restriction works** — earlier framing of "hard restriction not bypassable" was wrong.
    - ~~**M2-IB.4b — IBBroker.replace() (cancel-then-new wrapper).**~~ DEFERRED. Phase 1 daily-rebalance strategy doesn't modify in-flight orders; `replace()` raises `NotImplementedError`. Lands when a strategy needs in-flight modification (Phase 2+).
    - ~~**M2-IB.5 prereqs trio (EODHD refresh / IB pipeline / SMA stub).**~~ ✓ Committed 2026-05-02. (a) `scripts/refresh_eodhd_parquet.py` + `secrets/eodhd.env.example` — broker-agnostic credentials loader for `EODHD_API_KEY`, fetches `https://eodhd.com/api/eod/{ticker}`, writes PaperMarketData-compatible parquet, round-trip validates schema. (b) `src/blive/runtime/ib_pipeline.py` — sibling to `paper_pipeline.py`; broker-injected, signal-decoupled (takes `position_series` directly); 6 unit tests covering happy / cancel / kill-switch / position-flip paths. (c) `src/blive/runtime/signals.py` — `sma_crossover_position(bars, sma_window)` stub returning the position series the pipeline consumes; 7 unit tests. **Operator instruction honoured: TKAN deferred until end-to-end paper testing is done; SMA stub is the placeholder.** All three commit cleanly with mypy / black / isort / lint-imports green.
    - ~~**M2-IB.5 driver — `scripts/run_m2ib5_paper.py`.**~~ ✓ Committed 2026-05-02. End-to-end glue: connects IBBroker, loads EODHD parquet, computes SMA stub, runs `run_ib_pipeline`, prints `IBRunResult` summary. Defaults: MKT order type, `--max-bars 60` (~3 months capped), SMA(50), nav_slice 0.05.
    - ~~**M2-IB.5 architectural-surface wire run (out-of-RTH).**~~ ✓ 2026-05-02 (Saturday, markets closed). 60-bar replay against IB Paper: 35 submits (long-regime days), 0 fills (markets closed; orders held until Mon 09:00 MET via warning 399), 35 canceled (engine-timeout), 0 rejected, 0 breaches. FSM coverage exercised x35: T1 (init→submit_pending), SUBMITTED, ACCEPTED on PreSubmitted, CANCELED via engine cancel + IB error 202. Post-acceptance disambiguation fix held throughout — no misclassifications. Run time 352s (35 submits × ~10s timeout each). **M2-IB.5 architectural surface validated**.
    - ~~**M2-IB.5 in-RTH FILLED validation.**~~ CLOSED-EARLY-BY-OPERATOR 2026-05-02. M2-IB.5 closes at architectural surface — the single-instrument pipeline + IB write-side wire validation are durable substrate but no longer the strategy-run target. Strategy designation switched from A2 (`tkan_v4_momentum_timing` on CAC.PA) to A3 (`triple_lev_sma_filter_dsl` on TQQQ/TMF/IEF) per [ADR-043](./docs/decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2). The CAC.PA + SMA-stub `run_m2ib5_paper.py` driver stays in repo as durable substrate for the single-instrument-pipeline shape. M2-IB.5 in-RTH FILLED for CAC.PA is no longer a Phase 1 target.
    - **M2-IB.6-substrate.** ✓ Committed 2026-05-02 (this batch). ADR-043 ACCEPTED (Phase 1 switch); ADR-021 SUPERSEDED-BY-ADR-043; KB-5 §7 phased priority reordered; INV-1 v0.1 → v0.2 (A2/A3 phase columns swapped); TASK_REGISTRY M2-IB.5 close + M2-IB.6 scope opened.
    - ~~**M2-IB.6.1 — multi-instrument pipeline + 5-ticker EODHD refresh + LongShortPortfolio btest dispatch + IB SMART resolver convention.**~~ ✓ Completed across 2026-05-02 → 2026-05-04. Code path landed (`run_m2ib6_ib_paper.py`, multi-instrument pipeline, 5-ticker refresh, LongShortPortfolio dispatch, resolver support), then was empirically tightened by two wire findings: **ADR-047** (PRIIPs / KID rejection on TQQQ / TMF / IEF for UK retail) and **ADR-048 PROPOSED** (`XLON + ETF → SMART/LSEETF` after bare `LSE` surfaced error 200).
    - ~~**M2-IB.6.2a — US-RTH PRIIPs validation probe.**~~ ✓ Completed 2026-05-04 at head `abebc5a`. `scripts/probe_tqqq_us_rth.py` rerun during US RTH returned the full formatted 201 / KID reason text; ADR-047 is empirically validated, and INV-14 v0.6 now documents the dual-channel `statusEvent` + `ib.errorEvent` rejection shape.
    - ~~**M2-IB.6.2b — LSE-RTH filled validation.**~~ ✓ Completed 2026-05-06 09:33 BST. First IB-paper FILL on M2-IB.6 landed (IBTM, 19 × £128.5) via the ADR-048 SMART/LSEETF routing — no error 200 regression, no PRIIPs surfaces under the substituted universe. QQL3 surfaced IB warning 2161 (Price Management Algo regulatory cap), prompting the .6.2c investigation.
    - ~~**M2-IB.6.2c — IB warning 2161 PMA-cap investigation.**~~ ✓ Completed 2026-05-06. Four-run wire matrix on QQL3 (raw MKT 10s + 60s waits → ADAPTIVE_MKT → LMT @ $50): empirically confirmed the cap binds STRUCTURALLY on UK retail accounts regardless of order type. Added `OrderType.ADAPTIVE_MKT` (IBALGO Adaptive variant) — kept as catalogue infrastructure for non-cap-bound venues even though it does not bypass the cap on UK retail. INV-14 v0.7 documents the validation matrix; OQ-031 raised; ADR-049 ACCEPTED.
    - ~~**M2-IB.6-close.**~~ ✓ Committed 2026-05-06. ADR-048 + ADR-049 flipped PROPOSED → ACCEPTED in a single batch; DD-7 §3 amended (XLON split by `asset_class` per ADR-048); RETRO-M2-IB written + frozen at [`docs/retros/M2-IB_retrospective.md`](./docs/retros/M2-IB_retrospective.md); successor NEXT_PROMPT.md replaced v0.7 → v0.8 targeting Phase 2 readiness audit. Tag `M2-IB.6-close`.
14. ~~**Phase 2 readiness audit** (per [CONTEXT_PROTOCOL §8.3.2](./CONTEXT_PROTOCOL.md) phase-boundary protocol).~~ ✓ Done 2026-05-06. [`docs/PHASE_2_READINESS.md`](./docs/PHASE_2_READINESS.md) DRAFT v0.1 written: eight-dimension audit informed by M2-IB.6's real wire outcomes; five cross-cutting questions raised as the agenda for the M3 plan-drafting session. No new ADRs / OQs raised; substrate-only session per protocol. Successor [`NEXT_PROMPT.md`](./NEXT_PROMPT.md) replaced v0.8 → v0.9 targeting M3 plan-drafting.
15. ~~**M3 plan-drafting session** (per [CONTEXT_PROTOCOL §8.3.2](./CONTEXT_PROTOCOL.md) phase-boundary protocol — third and final session of the M2 → Phase 2 transition). Operator-led on the five cross-cutting questions in [`docs/PHASE_2_READINESS.md`](./docs/PHASE_2_READINESS.md); agent drafts the M3 plan in `TASK_REGISTRY.md` ...~~ ✓ Done 2026-05-06. [`TASK_REGISTRY.md`](./TASK_REGISTRY.md) v0.5 → v0.6 with the deployment-decision M3 plan; the five plan-drafting calls (Q1 inform-then-resolve / Q2 10-day calendar-bound window / Q3 EODHD-vs-IB pull forward to M3 / Q4 A3-only / Q5 stub-DRAFT only what M3 produces) recorded inline. Sketched M4+ refreshed; G4 rewritten around the 10 deployment-decision exit criteria; risk register grows six Phase-2-entry rows. M2 → Phase 2 transition's §8.3.2 three-session pattern fully discharged. Successor [`NEXT_PROMPT.md`](./NEXT_PROMPT.md) replaced v0.9 → v1.0 targeting M3.1.
16. ~~**M3.1 — EODHD-vs-IB unit-of-quote reconciliation.**~~ ✓ Implementation landed 2026-05-06 (this commit; ADR-050 PROPOSED held for wire-validation flip). Operator chose **Hybrid B-now / A-later** with the A-route bounded to **free IB MD tiers only** (no LSEETF / paid subscription, accepted as a permanent constraint). Probe `scripts/probe_qql3_unit_of_quote.py` ran 2026-05-06 against EODHD: refuted H1 split-adjusted (close == adjusted_close ratio 1.0) and H2 currency-unit (CurrencyCode = USD); operative cause is EODHD-side recent reverse-split lag. Implementation: new `src/blive/adapters/eodhd/conventions.py` with `MANUAL_SCALE` divisor=10 for QQL3 (operator-confirmed against IB live reference); `run_ib_multi_pipeline` `_price_lookup` + LMT construction route through the catalogue; RC-10 (±50% threshold, calibrated for leveraged-ETP volatility) lands in `blive.risk` per [INV-4 v0.2](./docs/inv/risk_checks.md). Substrate: ADR-050 PROPOSED added; INV-4 v0.1 → v0.2; INV-14 v0.7 → v0.8 (error 110 promoted); KB-15 MISSING → DRAFT v0.1 (stub-DRAFT, unit-of-quote section only); DD-7 v1.4 footnote on the convention layer. Tests: 519 → 541 (8 conventions + 8 RC-10 + 1 pipeline integration). Pending: **wire-validation smoke** (`scripts/run_m2ib6_ib_paper.py --max-bars 5` during LSE RTH); on success, ADR-050 PROPOSED → ACCEPTED in a header-only edit per the M2-IB pattern.
17. **M3.2 — Empirical paper-mode capture (bounded deterministic; re-scoped 2026-06-05 from "10 LSE-RTH-day window").** ✓ **Results-capture code + INV-8/INV-9 stubs landed 2026-06-05** (this commit). The per-run results sink (`src/blive/runtime/m3_2_record.py` → `~/.blive/data/m3_2_window/runs.jsonl`) is wired into `scripts/run_m2ib6_ib_paper.py`; the additive capture surface on `IBMultiRunResult` (`accepted_count` / `submitted_by_symbol` / `observed_error_codes` + `cap_binding_2161_count`) + `IBBroker.observed_error_codes` (2161 tally) + `signals.equity_leg_regime_flips` yields per-instrument fill-rate, FSM-trace coverage, warning-2161 cap-binding, breach count, and regime-flip count per run. INV-8 `metrics` + INV-9 `alerts` MISSING → DRAFT v0.1. Tests 568 → 590; all gates green. **Re-scoped 2026-06-05 (operator call, plan-call #6): exit = bounded deterministic capture, not 10 calendar days** — regime variety from the replay window (`--max-bars`), offline-verifiable via `--dry-run`. **✓ CAPTURE-COMPLETE 2026-06-05:** two flip-spanning LSE-RTH captures (`max-bars 40` + `60`) in `runs.jsonl` — **QQL3 0/69 fills (0%), IBTM 6/6 (100%), 2161=0, zero rejects/breaches/error-110** (the empirical OQ-031 signal; ADAPTIVE_MKT didn't trip the visible cap yet QQL3 still didn't fill). `scripts/flatten_ib_paper.py` added + used to reset the accumulated paper IBTM (230 → 0). **M3.2 data deliverable done.**

18. ~~**M3.3 — OQ-031 resolution.**~~ ✓ **RESOLVED 2026-06-05 — Option 1** ([ADR-052](./docs/decisions/DECISIONS.md#adr-052--phase-1-accepts-the-pma-bound-leveraged-leg-non-fill-oq-031-option-1)). Operator accepted the PMA-bound leveraged-leg non-fill (QQL3 0/69 vs IBTM 6/6) as a Phase-1 deployment characteristic; **no code change**; OQ-031 OPEN → RESOLVED-BY-ADR-052; the leveraged-leg redesign deferred to Phase 2 as **OQ-032** (full design space incl. the leverage-preserving margin-on-a-1×-UCITS path). G4 exit-criterion #1 ✓ MET.

19. **M3.4 — mixed-currency P&L reconciliation.** Live observation of QQL3 (USD) + IBTL / IBTM (GBP-hedged) at simultaneous non-zero positions; MaintMargin / GrossPositionValue / NetLiquidation reconcile across the currency pair (the 30s diff-suppress AccountUpdate timer per ADR-033 is the observation surface). Kickoff at [NEXT_PROMPT v1.4](./NEXT_PROMPT.md). **Front of the queue.**

Outside the Phase 1 critical path:

- **Vision / `README.md`** — minimal stub committed at M0; full vision paragraph still pending.
- **Design-phase artefacts** (KB-7 failure_modes, KB-8 operational_events, KB-15 parity_methodology, DD-2..7, INV-2/3/7/8/9/11/12/14) — produced as M1/M2/M3 deliverables per `TASK_REGISTRY.md` rather than in advance.

After this batch, `REQUIREMENTS.md` gets the v0.2 pass that *removes* content now living in KBs and replaces with id references — slimmer, more authoritative, easier to iterate further.

---

## 11. Self-Critique / Next-Pass TODOs

Notes for v0.2 of this file:

- [ ] Add a "tooling" section: which agents/skills/scripts maintain which artifacts (e.g. a script that audits inventory machine-checkability).
- [ ] Add a "review cadence" table — which artifacts review monthly vs. per-milestone vs. on-change.
- [ ] Decide whether `CLAUDE.md` (project-level Claude instructions) should be authored now or after KB-5; current view: now, but minimal — points to this file and REQUIREMENTS.
- [ ] Add a top-level `README.md` with the 30-second pitch and links to (1) REQUIREMENTS, (2) this file, (3) ADRs, (4) future RUNBOOK.
- [ ] Consider whether to mirror the SMIM project's `TASK_REGISTRY.md` structure verbatim or adapt; the SMIM model has worked for the user before.
- [ ] Confirm the ADR-vs-OQ split is right — some open questions are better expressed as "ADR-X status=PROPOSED" than as a separate OQ.
- [ ] Add a section on how this file is consumed by the agent at session start (read-first protocol), so future sessions warm up faster.
