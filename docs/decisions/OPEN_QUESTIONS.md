---
id: KB-11
title: Open Questions
status: DRAFT
owner: shared (Oleg primary, Claude assist)
last_reviewed: 2026-06-06
version: 0.6
sources: []
depends_on: []
referenced_by:
  - REQUIREMENTS.md §16 (originally hosted OQ-001..012)
  - KB-5 strategy_taxonomy.md §9 (raised OQ-013..022)
  - CONTEXT_PROTOCOL.md §5 (governs status transitions)
---

# KB-11 — Open Questions

## Purpose

Track every deliberately-unresolved question with target resolution date, options under consideration, and dependency graph. Pulls together what was inline in `REQUIREMENTS.md §16` and what has accumulated in KBs.

## Conventions

Status (per [CONTEXT_PROTOCOL §5.4](../../CONTEXT_PROTOCOL.md#5-decision--question-discipline) plus one transitional state):

- **OPEN** — not yet discussed.
- **IN_DISCUSSION** — being weighed; default options proposed.
- **RESOLVED-PENDING-ADR** — answered in conversation; ADR pending in KB-10 (transitional state used while ADRs are being back-filled).
- **RESOLVED-BY-ADR-NNN** — formally recorded.
- **ABANDONED** — no longer relevant.

OQ ids are stable. Resolved OQs are not deleted; they retain history.

---

## Section A — OQs originating in REQUIREMENTS §16

These were inline in REQUIREMENTS v0.1; externalised here on 2026-04-26.

### OQ-001 — Single process or split (engine + UI)?

- **status:** IN_DISCUSSION (default: single process for v1)
- **opened:** 2026-04-26 · **target_resolution:** M0
- **depends_on:** —
- **Background:** REQUIREMENTS §16. Whether the engine and web UI live in one Python process or are split for ops resilience.
- **Options:** (a) single process — simpler dev, simpler deploy. (b) split (engine + UI as separate processes) — more ops complexity but UI restart doesn't kill engine.
- **Resolution criteria:** revisit if v1 ops experience shows UI bugs taking down trading.

### OQ-002 — Event bus: in-process vs Redis Streams from M1?

- **status:** IN_DISCUSSION (default: in-process; Redis as opt-in)
- **opened:** 2026-04-26 · **target_resolution:** M1
- **depends_on:** —
- **Background:** REQUIREMENTS §16.
- **Options:** (a) in-process asyncio queues — simple, sufficient for v1 single-host. (b) Redis Streams from M1 — durable, multi-process, but operational dependency.
- **Resolution criteria:** Redis becomes mandatory if HA / multi-process is required pre-M8.

### OQ-003 — Persistence: SQLite vs Postgres vs DuckDB?

- **status:** IN_DISCUSSION (default: SQLite v1)
- **opened:** 2026-04-26 · **target_resolution:** M4
- **depends_on:** —
- **Options:** (a) SQLite — single file, easy backup, plenty fast at our event rate. (b) Postgres — concurrent writers, network access, more ops. (c) DuckDB — analytics-friendly columnar, less battle-tested for OLTP.
- **Resolution criteria:** SQLite stays unless event throughput exceeds ~1000/s sustained or multi-host writes are needed.

### OQ-004 — `ib_async` dependency strategy?

- **status:** IN_DISCUSSION (default: pin minor `>=2.1,<2.2`, treat as vendored adapter)
- **opened:** 2026-04-26 · **target_resolution:** M2
- **depends_on:** —
- **Options:** (a) pin minor and depend; (b) vendor-fork; (c) pin patch.
- **Resolution criteria:** if upstream breaks, switch to vendor-fork.

### OQ-005 — Strategy isolation: one process per strategy or one process for all?

- **status:** IN_DISCUSSION (default: one process for all, `Actor`-isolated)
- **opened:** 2026-04-26 · **target_resolution:** M5
- **depends_on:** —
- **Options:** (a) one process; (b) one process per strategy.
- **Resolution criteria:** revisit if any strategy demands > 50% of a core or has incompatible Python deps.

### OQ-006 — Intra-bar trading richness?

- **status:** IN_DISCUSSION (default: rebalance + emergency-exit only at v1)
- **opened:** 2026-04-26 · **target_resolution:** M5
- **depends_on:** OQ-013 (resolved), KB-5 §4 frequency roadmap
- **Options:** (a) v1 = rebalance windows only; (b) v1 = full intra-bar event reactions.
- **Resolution criteria:** richer intra-bar trading is a frequency-roadmap concern; defer until F1+ work begins.

### OQ-007 — FX: real-time conversion vs daily close?

- **status:** IN_DISCUSSION (default: realised FX P&L per fill via IB rate; daily reval at close)
- **opened:** 2026-04-26 · **target_resolution:** M3
- **depends_on:** —
- **Options:** (a) realised per fill + daily reval (current default); (b) live FX feed for intra-day reval.
- **Resolution criteria:** revisit if FX P&L volatility distorts intra-day risk measures.

### OQ-008 — UI auth: shared secret vs local-only vs OAuth?

- **status:** IN_DISCUSSION (default: shared secret + TLS for v1)
- **opened:** 2026-04-26 · **target_resolution:** M6
- **depends_on:** —
- **Options:** (a) shared secret bearer; (b) local-only loopback; (c) OAuth/SSO.
- **Resolution criteria:** OAuth/SSO becomes interesting if more than one operator.

### OQ-009 — `btest` engine reuse: import as library or fork relevant modules?

- **status:** IN_DISCUSSION (default: import; fork only on upstream-break)
- **opened:** 2026-04-26 · **target_resolution:** M1
- **depends_on:** KB-1 btest_dsl_inventory (MISSING)
- **Options:** (a) `pip install -e ../btest` style; (b) vendor specific modules.
- **Resolution criteria:** if `btest` introduces breaking changes faster than `blive` can absorb, switch to vendor.

### OQ-010 — Capital allocation: explicit per-strategy NAV slice or shared account?

- **status:** IN_DISCUSSION (default: explicit slice tracked in `blive`, IB account ground truth)
- **opened:** 2026-04-26 · **target_resolution:** M4
- **depends_on:** OQ-013 (resolved)
- **Options:** (a) explicit slice; (b) shared pot.
- **Resolution criteria:** explicit is safer for risk attribution.

### OQ-011 — CLI alongside web UI?

- **status:** IN_DISCUSSION (default: yes from M6, parity with REST surface)
- **opened:** 2026-04-26 · **target_resolution:** M6
- **depends_on:** —
- **Options:** (a) CLI shipped from M6; (b) REST + curl is enough.
- **Resolution criteria:** ship CLI when first headless ops scenario emerges (typically operator running on a remote box without browser).

### OQ-012 — Parity tolerance bands: are §8 numbers right?

- **status:** OPEN (calibrate from real fills in M7)
- **opened:** 2026-04-26 · **target_resolution:** M7
- **depends_on:** A2 / A3 strategies running in IB Paper for ≥ 30 days
- **Background:** REQUIREMENTS §8 currently has provisional bands (slippage ±5 bps, borrow ±25 bps annualised, financing ±15 bps annualised, parity residual ±15 bps over 5d).
- **Resolution criteria:** observe live fills, fit empirical envelope, replace provisional numbers in REQUIREMENTS.

---

## Section B — OQs raised in KB-5 strategy_taxonomy

### OQ-013 — Which strategies are funded for v1, and what NAV slice?

- **status:** RESOLVED-BY-ADR-013 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** KB-5 §3, §7
- **Resolution:** v1 focus is **ETF and index strategies only**. Single-name SP500 cross-sectional strategies (`xsec_momentum_long_short_sp500`, `harp_quarterly_momentum`, `tiny_momentum_ls`) are catalogued but **deferred to post-M8**. Phased priority codified in [ADR-013](DECISIONS.md#adr-013--v1-scope-etf-and-index-strategies-only): Phase 1 (M3) A2 → Phase 2 (post-M5) A3 → Phase 3 (post-M7) A1a → Phase 4+ (post-M8) leveraged variants, A3 generalisations, UK equities.
- **Sub-question still open:** NAV slice per strategy is not yet decided; carry forward as part of M3 planning.
- **Cross-references:** [ADR-013](DECISIONS.md#adr-013--v1-scope-etf-and-index-strategies-only), KB-5 §3, §7, §8.

### OQ-014 — Data source switch from `sfera://` (Bloomberg) to live equivalent?

- **status:** RESOLVED-BY-ADR-014 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** —
- **Resolution:** support **all** data sources (`parquet://`, `sfera://`, `eodhd://`, `ib://`, `yf://`, `fred://`) via the existing clean API abstraction (`btest`'s `data/sources/registry.py` pattern). Each source is a pluggable adapter implementing the `DataSource` protocol; the strategy declares its source URL and the registry resolves it. No source-specific hard-coding above the adapter layer.
- **Cross-references:** [ADR-014](DECISIONS.md#adr-014--data-sources-via-clean-api-abstraction), REQUIREMENTS §5.2, §7.1; KB-5 §6.

### OQ-015 / OQ-018 — ML model training in-process or static artefacts? Artefact lifecycle?

- **status:** RESOLVED-BY-ADR-015 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** OQ-013 (RESOLVED-BY-ADR-013)
- **Resolution:** architectural assumption is that ML models are **live-trained** eventually. For **v1**, `blive` consumes **static artefacts** produced offline by `btest`. Training itself is out of scope for v1; loader is in scope, trainer is not. Strategy spec records artefact path, build hash, last-trained timestamp; staleness alerts fire on configurable freshness windows.
- **Sub-questions still open:** artefact freshness window defaults; M8+ retraining pipeline owner. Both deferred to M3 / M8 as appropriate.
- **Cross-references:** [ADR-015](DECISIONS.md#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1), KB-5 §2 (A2), §7 (Phase 1).

### OQ-016 — Synthetic leverage via margin or only via leveraged-ETF instruments?

- **status:** RESOLVED-BY-ADR-016 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** OQ-013 (RESOLVED-BY-ADR-013)
- **Resolution:** **support both**. Margin-financed leverage (target_leverage > 1, IB margin, ESTER/SOFR spread on financed half) AND leveraged-ETF instruments (TQQQ, TMF, SPXL, UPRO, SOXL). Choice is per-strategy. Parity envelopes differ per leverage path.
- **Cross-references:** [ADR-016](DECISIONS.md#adr-016--leverage-support-both-margin-financed-and-leveraged-etf-instruments), KB-5 §2 (A2 leveraged variants, A3), KB-5 §8 (cost parity), OQ-012.

### OQ-017 — Triple Leveraged ETF instrument set?

- **status:** RESOLVED (2026-04-26, by inspection of `triple_leveraged_etf_dsl.ipynb`)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26
- **depends_on:** —
- **Resolution:** `{TQQQ, TMF, IEF}`. TQQQ leg parks in IEF when QQQ < SMA-200 (5% hysteresis re-entry); TMF leg parks in IEF when TLT < SMA-200; otherwise 50/50 across the two risk-on legs. Implemented via `LongShortPortfolio` with empty `short_book`, `MaskSelector`, and `ExternalFactor(per_instrument=True)`. See KB-5 §2 A3.
- **Cross-references:** KB-5 §2 (A3), §3 (strategies table).

### OQ-019 — Live data: EODHD real-time vs IB streaming vs hybrid?

- **status:** RESOLVED-BY-ADR-017 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** —
- **Resolution:** **hybrid**. `MarketDataPort` admits multiple concurrent providers; routing is per-instrument (and possibly per-frequency). Default mapping pending calibration: IB streaming for IB-traded instruments; EODHD real-time / delayed for instruments outside our IB tier; EODHD historical for warm-up / backtest replay. Architecture forbids hard-wiring a single provider above the adapter layer (CONTEXT_PROTOCOL §2.2 / ADR-004).
- **Sub-questions still open:** per-instrument default routing rules — pending calibration in M2.
- **Cross-references:** [ADR-017](DECISIONS.md#adr-017--live-data-hybrid-eodhd--ib-streaming-per-instrument-routing), REQUIREMENTS §5.2, KB-5 §6.

### OQ-020 — Multi-currency P&L: real-time vs daily reval?

- **status:** IN_DISCUSSION (REQUIREMENTS §5.4 has working answer: realised FX per fill via IB rate, daily reval)
- **opened:** 2026-04-26 · **target_resolution:** M4
- **depends_on:** —
- **Background:** Earlier OQ-007 in Section A is the same question framed from REQUIREMENTS §16; OQ-020 is the strategy-taxonomy framing. Treat as the same question; resolution applies to both.
- **Resolution criteria:** revisit if FX P&L volatility on multi-currency strategies (A1a global indices, European A2 strategies) distorts intra-day risk attribution.

### OQ-021 — UK equity strategies in scope post-M8?

- **status:** RESOLVED-BY-ADR-018 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** OQ-013 (RESOLVED-BY-ADR-013)
- **Resolution:** **in scope later** — deferred but not abandoned. UK-listed cash equities (LSE-Main / AIM) become candidates post-M8. Likely entry: UK-only A1 cross-sectional from SMIM research universe (`equities/smim/UK-LC` or `UK-MC`).
- **Sub-questions still open:** concrete UK strategy spec — deferred to post-M8 planning.
- **Cross-references:** [ADR-018](DECISIONS.md#adr-018--uk-equity-strategies-deferred-to-post-m8), KB-5 §5 (asset classes), KB-13 (MISSING — clarifies smim relationship).

### OQ-022 — Generalise A3 to other leveraged-ETF pairs?

- **status:** RESOLVED-BY-ADR-019 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** OQ-013 (RESOLVED-BY-ADR-013)
- **Resolution:** **yes**. A3 is parameterised by `(risk_on_pair, safe_haven_park, trend_filter, hysteresis)`; `triple_lev_sma_filter_dsl` is one instance. Future instances on roadmap: SOXL/SQQQ (semis), UPRO/SPXU (broad index), cross-sector rotations (XLK/XLF). Engine code from M5 must remain generic — no TQQQ/TMF/IEF specialisations baked into engine. Concrete generalisation deferred to Phase 4+ (post-M8).
- **Cross-references:** [ADR-019](DECISIONS.md#adr-019--a3-archetype-generalises-to-other-leveraged-etf-pairs), KB-5 §2 (A3), §7 (Phase 4+).

---

## Section B' — Sub-questions raised after parent-OQ resolution

These sub-questions surfaced when the parent decisions (OQ-013, 014, 015, 018) were resolved, or in subsequent KBs (KB-13 ForgeFolio integration). Each carries a proposed default; operator confirmation pending.

### OQ-023 — ForgeFolio read-only integration with blive event log?

- **status:** OPEN
- **opened:** 2026-04-26 · **target_resolution:** post-M8
- **depends_on:** Phase 4+ work
- **Background:** [KB-13](../kb/companion_projects.md#forgefolio--portfolio-monitoring--analysis-pyqt6-gui) raised this. blive produces a daily NDJSON trade tape (REQUIREMENTS §6.3); ForgeFolio is a separate desktop monitoring app reading IB Flex Query independently. Whether they should share the trade-tape feed is a post-v1 question.
- **Options:** (a) keep them independent forever; (b) ForgeFolio reads blive's NDJSON tape on a schedule; (c) blive emits a ForgeFolio-shaped event stream.
- **Resolution criteria:** revisit when ForgeFolio integration becomes operationally desirable.

### OQ-024 — NAV slice for the Phase 1 strategy?

- **status:** RESOLVED-BY-ADR-020 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** OQ-013 (RESOLVED-BY-ADR-013)
- **Resolution:** **5–10% of total account NAV, hard cap 10%**. Combined with RC-07 (single-name notional ≤ 8% of strategy NAV), this caps any single position at ≤ 0.8% of total NAV — conservative for a paper-account technology-validation phase.
- **Cross-references:** [ADR-020](DECISIONS.md#adr-020--phase-1-nav-slice-510-of-total-cap-10), [TASK_REGISTRY](../../TASK_REGISTRY.md), [INV-4 RC-07](../inv/risk_checks.md).

### OQ-025 — Which CAC ETF proxy for the Phase 1 strategy?

- **status:** RESOLVED-BY-ADR-021 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** OQ-014 (RESOLVED-BY-ADR-014)
- **Resolution:** **`CAC.PA` (Lyxor CAC 40 UCITS ETF, distributing share class)** — most liquid CAC tracker on Euronext Paris (XPAR). Price-return tracking; ≈3–4% annual dividend gap vs. CACT (TR index) absorbed into the Phase 1 parity envelope and explicitly logged.
- **Sub-decisions deferred:** whether to retrain TKAN on `CAC.PA` price-return history (would close the gap; out of v1 scope per ADR-015); revisit at G4 gate.
- **Cross-references:** [ADR-021](DECISIONS.md#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf), [ADR-014](DECISIONS.md#adr-014--data-sources-via-clean-api-abstraction), [KB-5 §3](../kb/strategy_taxonomy.md), [TASK_REGISTRY](../../TASK_REGISTRY.md).

### OQ-026 — TKAN artefact freshness window default?

- **status:** RESOLVED-BY-ADR-022 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** OQ-015 (RESOLVED-BY-ADR-015)
- **Resolution:** **30 days hard (RC-12 block); 21 days warning alert**. Conservative for a daily-frequency strategy where retraining is minutes to hours offline. Re-tune from observed retraining cadence after first month of live (paper) operation.
- **Cross-references:** [ADR-022](DECISIONS.md#adr-022--tkan-artefact-freshness-window-30d-hard-21d-warning), [ADR-015](DECISIONS.md#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1), [INV-4 RC-12](../inv/risk_checks.md).

### OQ-027 — TKAN artefact prod location and retraining ownership?

- **status:** RESOLVED-BY-ADR-023 (2026-04-26)
- **opened:** 2026-04-26 · **resolved:** 2026-04-26 · **decider:** Oleg
- **depends_on:** OQ-018 (RESOLVED-BY-ADR-015)
- **Resolution:**
  - **Path scheme:** `~/.blive/artefacts/{strategy_id}/{model_name}/pred_cache.pkl` (e.g. `~/.blive/artefacts/tkan_v4_momentum_timing/tkan_v4/pred_cache.pkl`).
  - **Hash recording:** SHA256 of artefact in strategy spec snapshot per REQUIREMENTS §5.12.
  - **Retraining:** manual; operator runs btest's `TKAN_v4_train.py` then `scripts/refresh_artefact.py` (M2 deliverable) which copies + checksums + records.
  - **Auto-train pipeline:** out of v1 (consistent with ADR-015).
- **Cross-references:** [ADR-023](DECISIONS.md#adr-023--tkan-artefact-path-and-refresh-ownership), [ADR-015](DECISIONS.md#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1), [REQUIREMENTS §5.12](../../REQUIREMENTS.md), [TASK_REGISTRY](../../TASK_REGISTRY.md).

---

## Section B'' — Agentic-execution layer (raised from ADR-026)

### OQ-028 — Which agentic memory framework / tooling for L0+L1?

- **status:** OPEN (default proposed below; revisit at L0+L1 implementation)
- **opened:** 2026-04-26 · **target_resolution:** before L0+L1 implementation begins
- **depends_on:** ADR-026
- **Background:** [ADR-026](DECISIONS.md#adr-026--adopt-agentic-execution-layer-reduce-human-action-surface) codifies the agentic-execution layer but leaves the choice of framework open. Candidates have different trade-offs in maturity, lock-in, and substrate compatibility:
  - **Custom lightweight agent** — minimal dependency; full control; slow to feature-parity with frameworks; easy to integrate with our markdown substrate.
  - **Letta (formerly MemGPT)** — mature, Python-first, integration cost; designed for general agentic memory rather than disciplined substrate.
  - **Sculptor / ARC** — research-stage; Active Context Management primitives map well to L0; less mature.
  - **Native IDE / harness tooling** (e.g. Claude Code MCP servers, similar) — leverage existing infrastructure; risk of vendor lock; substrate-aware tools become possible without separate framework.
  - **Graph-native first** (Neo4j + Cypher MCP) — skips the markdown-era and goes directly to L4; bigger one-time investment, but L0/L1 become trivial graph queries.
- **Proposed default:** **custom-light for L0** (an agent that just reads `CONTEXT_INVENTORY.md` and walks `depends_on` closures); evaluate Letta or Sculptor for L1+ once L0 is operational and the cost of building the watchdog manually becomes the binding constraint.
- **Resolution criteria:** pick whichever path supports our markdown substrate and gives us L0+L1 in ≤ 2 working sessions of integration. Revisit at G4 gate or earlier if implementation friction is high.
- **Cross-references:** [ADR-026](DECISIONS.md#adr-026--adopt-agentic-execution-layer-reduce-human-action-surface), [`docs/method/Amendments_Log.md`](../method/Amendments_Log.md).

### OQ-029 — When to implement L0+L1?

- **status:** OPEN (default proposed below; revisit at G4)
- **opened:** 2026-04-26 · **target_resolution:** at or before G4 gate
- **depends_on:** ADR-026; OQ-028 (framework choice)
- **Background:** [ADR-026](DECISIONS.md#adr-026--adopt-agentic-execution-layer-reduce-human-action-surface) sets the direction but does not commit to a milestone. Options:
  - **Concurrent with M3** — split focus; M3 may slip; L0+L1 may benefit from being designed against real M3 substrate state.
  - **New M3.5 milestone** — dedicated layer-0 / 1 work, well-scoped, between M3 and M4.
  - **As part of M5 Reconciliation / ops** — bundles related operational work but pushes the savings later.
  - **After Phase 1 (post-G4)** — leverages M3 outcomes and parity calibration; clean phase boundary.
- **Proposed default:** **post-G4, as a Phase 2 entry concern** — L0+L1 land in a dedicated milestone after Phase 1 closes, leveraging real Phase 1 substrate state to calibrate the integrity watchdog. This keeps Phase 1 manual (acceptable for the small scale) and uses Phase 2's larger scope to motivate the agentic layer's value.
- **Resolution criteria:** revisit at G4. If Phase 1 manual burden is becoming the bottleneck during M2 or M3, accelerate to "concurrent with M3" or "M3.5". Otherwise, post-G4.
- **Cross-references:** [ADR-026](DECISIONS.md#adr-026--adopt-agentic-execution-layer-reduce-human-action-surface), [TASK_REGISTRY](../../TASK_REGISTRY.md), [OQ-028](#oq-028--which-agentic-memory-framework--tooling-for-l0l1).

### OQ-030 — Which btest interpreter does blive call for `TimingPortfolio` (and other non-LongShort archetypes)?

- **status:** RESOLVED-BY-ADR-030 (2026-04-27)
- **opened:** 2026-04-27 · **target_resolution:** G2 gate
- **depends_on:** [ADR-010](DECISIONS.md#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import); [KB-1 §6, §7](../kb/btest_dsl_inventory.md)
- **Background:** [ADR-010](DECISIONS.md#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import) commits blive to importing `FactorEngine`, `SignalEngine`, `PortfolioEngine` from btest. M1 work surfaced two facts:
  1. `PortfolioEngine` is a free function `compute_target_weights_for_date()` (not a class), and it only handles `LongShortPortfolio`.
  2. The Phase 1 strategy (`tkan_v4_momentum_timing`) uses `TimingPortfolio`, which btest interprets via `quantdsl_backtest.runners.single_asset.SingleAssetRunner` — a different module that bundles factor evaluation, signal evaluation, and position derivation in one batch interpreter, **not** the three engines named in ADR-010.
- **Options:**
  1. **Call `SingleAssetRunner` from blive's pipeline** for `TimingPortfolio`-based strategies; call `FactorEngine + SignalEngine + compute_target_weights_for_date` for `LongShortPortfolio`-based strategies. Each archetype maps to its native btest interpreter. (Working default for M1.)
  2. **Reimplement TimingPortfolio's logic inside blive** as a streaming-friendly evaluator that sits alongside FactorEngine/SignalEngine. Closer to ADR-010's prose but introduces the very drift ADR-010 was meant to prevent.
  3. **Extend btest's engine package** to expose a `TimingPortfolioEngine` matching the LongShort one. Upstream change; cross-project coordination cost.
- **Proposed default (working answer for M1):** Option 1. The Strategy Loader inspects `strategy.portfolio` type and the M1 pipeline dispatches to the appropriate btest interpreter. ADR-010's spirit — reuse btest's engines, don't fork — is preserved; the prose's "three engines" is a partial enumeration that needs amendment when this OQ resolves.
- **Resolution criteria:** at G2 review, decide whether to (a) amend ADR-010 prose to acknowledge `SingleAssetRunner` and any future archetype-specific interpreters, (b) advocate Option 3 with btest, or (c) keep ADR-010 unchanged and treat the dispatch as an undocumented but stable pattern. Plus: confirm `LongShortPortfolio` archetype works under the same M1 pipeline shape when Phase 3 (`lagging_indecies`) lands at M7.
- **Cross-references:** [ADR-010](DECISIONS.md#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import); [KB-1 §6, §7](../kb/btest_dsl_inventory.md); [`runners/single_asset.py`](`btest/src/quantdsl_backtest/runners/single_asset.py`); M0 retro recommendation 1; M1 work this session.

### OQ-031 — Phase 1 deployment under PMA-bound retail account

- **status:** RESOLVED-BY-ADR-052 (2026-06-05)
- **opened:** 2026-05-06 · **target_resolution:** before Phase 1 live cutover (G3-IB → G4 transition)
- **depends_on:** [ADR-047](DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043); [ADR-049 PROPOSED](DECISIONS.md#adr-049--ordertypeadaptive_mkt-for-ibalgo-adaptive-routing-empirical-pma-cap-finding); [INV-14 v0.7](../inv/ib_error_codes.md)
- **Background:** The 2026-05-06 LSE-RTH validation runs of `scripts/run_m2ib6_ib_paper.py` empirically confirmed that **IB warning 2161 (Price Management Algo / regulatory disruptive-orders cap) binds structurally** on QQL3 (3× Nasdaq leveraged ETP on LSEETF) for the operator's UK retail IB Paper account. The cap pegs the effective limit to IB's live bid/ask reference; in rising markets, BUY orders capped at the bid don't fill. Tested across raw MKT (10s + 60s waits), `OrderType.ADAPTIVE_MKT` (IBALGO Adaptive — IB's recommended workaround in the warning text), and LMT @ $50 (well above IB ref ~$39 but within allowed-range envelope) — all subject to the cap; 0 QQL3 fills across 16 placeOrders. The `priceManagementOff` order flag is institutional-only. IBTM (1× UCITS Treasury ETF) is unaffected — fills land cleanly. Implication: Phase 1 deployment of A3 has a **regime-dependent fill profile** on its leveraged equity leg — fills happen only when the market mean-reverts to the cap level. In extended uptrends, the strategy spends time long the equity leg without acquiring full position, then is forced to acquire on regime-flips into safe-haven (when ask drops to bid). This is **opposite to the intended trend-following profile**.
- **Options:**
  1. **Accept the constraint as a real-world Phase 1 deployment characteristic.** Document the regime-dependent fill profile in the strategy's risk-and-execution-profile note. M7 parity envelope absorbs the divergence from the article's backtest fill-rate assumptions. Operator monitors fill-rate empirically over the first ~5 trading days of live deployment; if the fill-rate is unacceptable (TBD threshold), revisit. **No code change.**
  2. **Pursue MiFID II Professional Client classification** to enable the `priceManagementOff` order flag (institutional-only opt-out from PMA). Per [ADR-047 §"Alternatives Considered" item 2](DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043), this requires meeting wealth / experience / transaction-frequency thresholds. Operator declined at M2-IB.6.1; revisit if Option 1's fill-rate is unacceptable.
  3. **Substitute the leveraged equity leg with a non-leveraged analogue** (e.g. directly hold QQQ via UK-listed UCITS or remove the 3× leverage entirely). Materially changes the strategy's risk profile (1×/1× vs intended 3×/1× post-ADR-047 vs original 3×/3× from the notebook); equivalent to a different strategy. Captured here for completeness; would amend ADR-043 + ADR-047.
  4. **Restructure as a passive-limit-only strategy** that explicitly accepts the PMA cap as the execution model — submits at the cap, accepts the regime-dependent fill rate as the strategy's intended behaviour rather than a constraint. Closer to a mean-reversion strategy than the trend-following A3; would need a fresh ADR + parity envelope.
- **Proposed default (working answer):** Option 1 for the first ~5 trading days of paper-mode validation; revisit the choice based on empirical fill-rate data before live cutover. The architectural surface (M2-IB.6) closes on Option 1 — the cap is a real wire finding that does not block FSM / pipeline validation; the operational decision is downstream.
- **Resolution criteria:** before live cutover (G3-IB → G4 gate). Operator decides between Options 1–4 based on (a) the M2-IB.6 retro's fill-rate evidence, (b) the strategy's empirical regime-bias when the parity envelope re-derives at M7, (c) the operator's own risk tolerance for PMA-bound execution.
- **Cross-references:** [ADR-047](DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043); [ADR-049 PROPOSED](DECISIONS.md#adr-049--ordertypeadaptive_mkt-for-ibalgo-adaptive-routing-empirical-pma-cap-finding); [INV-14 v0.7](../inv/ib_error_codes.md); M2-IB.6.2b/c wire-finding (2026-05-06).

### OQ-032 — Phase 2 A3 leveraged-leg redesign: how (or whether) to restore leveraged equity exposure

- **status:** OPEN
- **opened:** 2026-06-05 · **target_resolution:** Phase 2 entry (M3 → M4 boundary)
- **depends_on:** [ADR-052](DECISIONS.md#adr-052--phase-1-accepts-the-pma-bound-leveraged-leg-non-fill-oq-031-option-1); [ADR-043](DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2); [ADR-047](DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043); [ADR-049](DECISIONS.md#adr-049--ordertypeadaptive_mkt-for-ibalgo-adaptive-routing-empirical-pma-cap-finding); [ADR-016](DECISIONS.md#adr-016--leverage-support-both-margin-financed-and-leveraged-etf-instruments); OQ-031 (RESOLVED-BY-ADR-052)
- **Background:** [ADR-052](DECISIONS.md#adr-052--phase-1-accepts-the-pma-bound-leveraged-leg-non-fill-oq-031-option-1) resolved OQ-031 with Option 1 — Phase 1 accepts that the QQL3 (3×) leveraged equity leg structurally does not fill on the operator's PMA-bound UK-retail **Cash** account (M3.2 capture: QQL3 0/69 fills vs IBTM 6/6), so live behaviour is Treasury-leg-dominated. The deeper finding is a **trilemma**: a UK-retail Cash account has **no** open path to leveraged equity exposure — **PRIIPs / KID** blocks US-domiciled leveraged ETPs (per [ADR-047](DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043)), the **PMA cap (warning 2161)** blocks UK-listed leveraged ETPs (per [ADR-049](DECISIONS.md#adr-049--ordertypeadaptive_mkt-for-ibalgo-adaptive-routing-empirical-pma-cap-finding) / OQ-031), and a **Cash** account blocks margin-financed leverage. Phase 2 decides **how — or whether — to restore the strategy's intended 3× equity exposure.** This OQ owns that redesign.
- **Options under consideration:**
  1. **Leverage-preserving — margin on a 1× Nasdaq-100 UCITS ETF (to be validated).** Hold a plain 1× UK-listed Nasdaq-100 UCITS ETF and obtain ≈3× via 3:1 margin, instead of a leveraged ETP. The PMA cap triggers on product volatility / leverage — a 1× UCITS (~1–1.5% median daily range) very likely does **not** trip 2161 (vs QQL3's 3.91%), so it fills — and margin supplies the leverage. **The only path that delivers the intended 3×/1× profile.** Cost: requires a **Margin** account (the current paper account is Cash + GBP-base), incurs margin interest (financing parity per [KB-6 §4](../kb/cost_margin_dictionary.md) becomes load-bearing), and the no-PMA-on-1× assumption needs its own wire validation. Per [ADR-016](DECISIONS.md#adr-016--leverage-support-both-margin-financed-and-leveraged-etf-instruments) blive already supports margin-financed leverage as a first-class path.
  2. **Leverage-preserving — Pro Client classification** (OQ-031 Option 2). MiFID II Professional Client status enables `priceManagementOff`, so QQL3 itself fills. Keeps the leveraged-ETP path. Declined at M2-IB.6.1; gated on wealth / experience / transaction-frequency thresholds.
  3. **De-lever to 1×/1×** (OQ-031 Option 3 direction). Substitute a 1× UK-listed UCITS Nasdaq-100 analogue for QQL3 outright — the strategy fills on both legs but **drops the leverage** (1×/1×, not 3×/1×). Amends ADR-043 + ADR-047; needs a `--dry-run` regime check + an RTH capture on the new leg.
  4. **Embrace the cap — passive-limit / mean-reversion restructure** (OQ-031 Option 4). Keep the leveraged ETP but redefine the strategy around the PMA cap as its execution model. Fresh ADR + re-derived parity envelope.
  5. **Replace A3 with a different Phase-2 archetype** (A1 / A1a, forward-listed in [TASK_REGISTRY Sketched M4+](../../TASK_REGISTRY.md#sketched-m4-post-phase-1)) instead of resolving the leverage question for A3.
- **Resolution criteria:** decide at Phase 2 entry, informed by (a) the M7 parity-envelope re-derivation (financing parity for the margin path; regime-bias for any path), (b) the operator's live-cutover intent (Treasury sleeve vs. a two-leg strategy at the intended 3× profile), (c) the account-type lever (Cash → Margin is a real, distinct change with its own costs), (d) appetite for the re-validation half-session. The chosen redesign gets its own ADR (amending ADR-043 / ADR-047 or superseding as warranted).
- **Cross-references:** [ADR-052](DECISIONS.md#adr-052--phase-1-accepts-the-pma-bound-leveraged-leg-non-fill-oq-031-option-1); [ADR-043](DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2); [ADR-047](DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043); [ADR-049](DECISIONS.md#adr-049--ordertypeadaptive_mkt-for-ibalgo-adaptive-routing-empirical-pma-cap-finding); [ADR-016](DECISIONS.md#adr-016--leverage-support-both-margin-financed-and-leveraged-etf-instruments); [INV-14 v0.9](../inv/ib_error_codes.md); [KB-9 §5.5](../kb/uk_regulatory.md) (PRIIPs).

---

## Section B''' — Phase-2 strategy & execution (raised from PHASE_2_READINESS v0.2 audit)

These three OQs were raised by the 2026-06-06 Phase-2
readiness-audit refresh ([PHASE_2_READINESS](../PHASE_2_READINESS.md)
v0.2), driven by the incoming Phase-2 strategy candidate
**R-LEV-001 "VIX Term Structure Rotation"** (the operator's
`lab/research/r_lev_001_triple_leveraged_etf` deep-analysis
notebook + `STRATEGY_METADATA.md`). All three are *coupled* — they
all turn on whether R-LEV-001 is adopted as the Phase-2 strategy,
which is decided alongside [OQ-032](#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure)
in the session-3 plan-drafting session. Append-only per
[CONTEXT_PROTOCOL §2.5](../../CONTEXT_PROTOCOL.md).

### OQ-033 — Phase-2 VIX strategy: UX1 / UX6 VIX-futures term-structure data sourcing

- **status:** OPEN
- **opened:** 2026-06-06 · **target_resolution:** Phase 2 entry (M3 → M4 boundary / session-3 plan-drafting)
- **depends_on:** [OQ-032](#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure); [OQ-034](#oq-034--phase-2-vix-strategy-uk-retail-tradability-of-the-tqqq--vxx--ief-universe); [ADR-014](DECISIONS.md#adr-014--data-sources-via-clean-api-abstraction); [ADR-017](DECISIONS.md#adr-017--live-data-hybrid-eodhd--ib-streaming-per-instrument-routing)
- **Background:** R-LEV-001 keys off the ratio **UX6 / UX1** (6-month vs front-month VIX futures) compared to its 252-day rolling median (risk-on / contango → 100% TQQQ; risk-off / backwardation → vol-then-IEF). blive sources **EODHD + IB**; it does not yet source VIX-futures term structure. **Operator decision (2026-06-06): source from EODHD** — *not* from sfera, and *not* by consuming sfera's pre-computed `vix_vxx_rotation.parquet` (blive recomputes the signal itself from raw EODHD data). The open part is therefore *empirical, not a sourcing-channel choice*: does EODHD actually carry a usable VIX-futures term-structure series, with enough history for the 252-day median warm-up?
- **Options / sub-questions:**
  1. **Which EODHD series.** UX1/UX6 direct (if EODHD exposes the Bloomberg-style continuation tickers), vs EODHD's own continuous VIX-futures front-/6-month series, vs deriving the tenors from individual CFE contract chains. Needs a coverage probe.
  2. **History depth.** ≥ 252 trading days (1y) is required before the rolling median is defined; confirm EODHD's history reaches far enough (the research backtest runs 2011–2026).
  3. **Fallback — IB CFE futures subscription.** Only if EODHD's coverage is insufficient: an IB CFE VIX-futures market-data subscription (+ futures data permissions). Higher cost / permission overhead; route of last resort.
- **Resolution criteria:** an EODHD coverage + history probe at Phase 2 entry / early M4; EODHD suffices ⇒ done, else fall back to IB CFE. Feeds the M4+ data-adapter plan. (No sfera / static-parquet handoff — settled by the operator.)
- **Cross-references:** [OQ-032](#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure); [OQ-034](#oq-034--phase-2-vix-strategy-uk-retail-tradability-of-the-tqqq--vxx--ief-universe); [OQ-035](#oq-035--phase-2-order-type--tif-surface-moo--opg-for-market-on-open-execution); [ADR-014](DECISIONS.md#adr-014--data-sources-via-clean-api-abstraction); [ADR-017](DECISIONS.md#adr-017--live-data-hybrid-eodhd--ib-streaming-per-instrument-routing); the R-LEV-001 `STRATEGY_METADATA.md`.

### OQ-034 — Phase-2 VIX strategy: UK-retail tradability of the TQQQ / VXX / IEF universe

- **status:** OPEN
- **opened:** 2026-06-06 · **target_resolution:** Phase 2 entry (M3 → M4 boundary / session-3 plan-drafting)
- **depends_on:** [OQ-032](#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure) (the Professional-vs-retail / leverage decision); [ADR-047](DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043); [KB-9 §5.5](../kb/uk_regulatory.md) (PRIIPs / KID); [DD-7](../dd/instrument_dictionary.md)
- **Background:** R-LEV-001's universe is **entirely US-domiciled** — TQQQ (3× Nasdaq leveraged ETF), VXX (1× short-term VIX-futures ETN), IEF (7–10yr US Treasury ETF) — so KID-less for UK **retail**. **Operator status (2026-06-06): staying retail near-term → route B (retail) is active; route A (Professional Client) is deferred** (not currently elective-professional-eligible; revisit on eligibility change). Tradability forks on the OQ-032 classification choice: **route A (Professional Client, deferred)** — PRIIPs/KID is a *retail*-only block, so a Professional Client trades the US originals directly (the 2161 PMA cap was seen only on the UK-listed substitute QQL3/LSEETF and most likely does **not** bind on US-listed TQQQ via SMART/NASDAQ — **needs IB confirmation**; leverage comes from the 3× ETP, so no margin needed); **route B (retail)** — the book must be substituted: IEF → IBTM (known), TQQQ → the OQ-032 margin path, vol leg → a UK-retail-eligible UCITS. **Independent of route**, the operator's design decision is to **replace VXX with a mid-term 3- or 6-month vol product** (less roll-decay than VXX's front-month) — a deliberate change to the risk-off leg, not merely a substitution.
- **Options under consideration:**
  1. **Route B + full UCITS substitution (active).** UK-retail UCITS for every leg: a 1× Nasdaq-100 UCITS (+ the OQ-032 margin-on-1×-UCITS path to recover ~3×), IBTM, and a **UCITS mid-term 3-/6-month vol product** (which must itself clear PRIIPs / complexity + the PMA cap). The operator's near-term path.
  2. **Route A + design substitution (deferred).** Trade US TQQQ + IEF as-is and swap VXX for a US-listed mid-term vol product — cleanest, but needs Professional classification the operator does not currently hold. Revisit on eligibility change.
  3. **Defer R-LEV-001; keep A3** (redesigned per OQ-032) if the retail UCITS universe proves too costly to make tradeable.
- **Resolution criteria:** decide at Phase 2 entry (session 3) jointly with OQ-032's route A/B choice; on route B confirm a UK-retail-eligible mid-term vol UCITS exists; a tradability / US-venue-cap probe validates the chosen instruments at early M4. Amends / extends [ADR-047](DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043) if a new universe is codified.
- **Cross-references:** [OQ-032](#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure); [OQ-033](#oq-033--phase-2-vix-strategy-ux1--ux6-vix-futures-term-structure-data-sourcing); [OQ-035](#oq-035--phase-2-order-type--tif-surface-moo--opg-for-market-on-open-execution); [ADR-047](DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043); [ADR-049](DECISIONS.md#adr-049--ordertypeadaptive_mkt-for-ibalgo-adaptive-routing-empirical-pma-cap-finding); [KB-9 §5.5](../kb/uk_regulatory.md); [DD-7](../dd/instrument_dictionary.md); the R-LEV-001 `STRATEGY_METADATA.md`.

### OQ-035 — Phase-2 order-type & TIF surface: MOO / OPG for Market-On-Open execution

- **status:** OPEN
- **opened:** 2026-06-06 · **target_resolution:** Phase 2 entry (scope) / M4+ (implementation)
- **depends_on:** [KB-2](../kb/ib_capability_matrix.md) (order types / TIFs); INV-2 (order types, MISSING); INV-3 (TIFs, MISSING); [ADR-049](DECISIONS.md#adr-049--ordertypeadaptive_mkt-for-ibalgo-adaptive-routing-empirical-pma-cap-finding)
- **Background:** R-LEV-001 executes **MOO (Market-On-Open, T+1)** — signal at T close → execute at T+1 open. blive's order-type surface is `MKT` / `LMT` / `ADAPTIVE_MKT` only ([ADR-049](DECISIONS.md#adr-049--ordertypeadaptive_mkt-for-ibalgo-adaptive-routing-empirical-pma-cap-finding)); it has no `OPG`-class order type or opening-auction TIF. [INV-2](../inv/order_types.md) (order types) and [INV-3](../inv/tif_values.md) (TIFs) are MISSING per [CONTEXT_INVENTORY §3](../../CONTEXT_INVENTORY.md). So MOO is not expressible today. ([KB-2](../kb/ib_capability_matrix.md) catalogues IB's MOO / OPG support — the gap is in blive's domain / adapter surface, not IB's.)
- **Options under consideration:**
  1. **Add an `OPG`-class order type + opening-auction TIF** to the domain `OrderType` / `TIF` enums + the IB adapter mapping, and author INV-2 / INV-3 as the catalogues. Cleanest; the right home for the gap.
  2. **Approximate MOO with a timed `MKT` at the open** (submit at RTH open via the scheduler) — avoids new order types but loses the opening-auction semantics + is exposed to open-volatility slippage. A stopgap.
  3. **Defer** — only scope MOO / OPG if R-LEV-001 (or another MOO strategy) is actually adopted (OQ-032 / OQ-034). If Phase 2 stays on daily-RTH A3, the current surface suffices.
- **Resolution criteria:** a **scope decision at Phase 2 entry** (does Phase 2 need MOO / OPG — yes iff R-LEV-001 is adopted) and, if yes, an **implementation milestone** (likely M4, alongside the strategy). Authoring INV-2 / INV-3 is the substrate deliverable once a second order-type family lands.
- **Cross-references:** [OQ-032](#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure); [OQ-033](#oq-033--phase-2-vix-strategy-ux1--ux6-vix-futures-term-structure-data-sourcing); [OQ-034](#oq-034--phase-2-vix-strategy-uk-retail-tradability-of-the-tqqq--vxx--ief-universe); [ADR-049](DECISIONS.md#adr-049--ordertypeadaptive_mkt-for-ibalgo-adaptive-routing-empirical-pma-cap-finding); [KB-2](../kb/ib_capability_matrix.md); the R-LEV-001 `STRATEGY_METADATA.md`.

---

## Section C — Index by status

### RESOLVED-BY-ADR-NNN (formally recorded in [KB-10](DECISIONS.md))

| OQ | ADR | Title |
|----|-----|-------|
| OQ-013 | ADR-013 | v1 scope: ETF and index strategies only |
| OQ-014 | ADR-014 | Data sources via clean API abstraction |
| OQ-015 | ADR-015 | ML training: live-trained eventually, static artefacts in v1 |
| OQ-016 | ADR-016 | Leverage: support both margin-financed and leveraged-ETF instruments |
| OQ-018 | ADR-015 | (shared resolution with OQ-015) |
| OQ-019 | ADR-017 | Live data: hybrid EODHD + IB streaming |
| OQ-021 | ADR-018 | UK equity strategies deferred to post-M8 |
| OQ-022 | ADR-019 | A3 archetype generalises to other leveraged-ETF pairs |
| OQ-024 | ADR-020 | Phase 1 NAV slice: 5–10% of total, cap 10% |
| OQ-025 | ADR-021 | CAC ETF proxy: `CAC.PA` (Lyxor CAC 40 UCITS ETF) |
| OQ-026 | ADR-022 | TKAN artefact freshness window: 30d hard, 21d warning |
| OQ-027 | ADR-023 | TKAN artefact path and refresh ownership |
| OQ-030 | ADR-030 | Per-archetype btest interpreter dispatch (amends ADR-010) |
| OQ-031 | ADR-052 | Phase 1 deployment under PMA-bound retail account (Option 1: accept the leveraged-leg non-fill) |

### RESOLVED (no ADR needed, factual finding)

OQ-017 — Triple Leveraged ETF instrument set is `{TQQQ, TMF, IEF}`.

### OPEN

| OQ | Question | Target |
|----|----------|--------|
| OQ-012 | Parity tolerance bands | calibrate at M7 |
| OQ-023 | ForgeFolio integration | post-M8 |
| OQ-028 | Agentic memory framework / tooling for L0+L1 | before L0+L1 implementation |
| OQ-029 | Timing of L0+L1 implementation | at or before G4 gate |
| OQ-032 | Phase 2 A3 leveraged-leg redesign (how/whether to restore leveraged equity exposure) | Phase 2 entry (M3 → M4) |
| OQ-033 | VIX-futures (UX1/UX6) term-structure data sourcing for the Phase-2 strategy | Phase 2 entry (M3 → M4) |
| OQ-034 | Incoming VIX strategy universe (TQQQ/VXX/IEF) UK-retail tradability | Phase 2 entry (M3 → M4) |
| OQ-035 | MOO/OPG order-type + TIF surface for Market-On-Open execution | Phase 2 entry / M4+ |

### IN_DISCUSSION (have a working default in REQUIREMENTS §16; ADRs not yet written)

OQ-001..OQ-011, OQ-020.

---

## Section D — Maintenance

- New OQs are appended; existing OQs are not deleted.
- Status transitions are recorded inline in the OQ block (date + decider).
- When an ADR lands in KB-10, update the status from `RESOLVED-PENDING-ADR` to `RESOLVED-BY-ADR-NNN`.
- Weekly review per [CONTEXT_PROTOCOL §6.3](../../CONTEXT_PROTOCOL.md#63-review-cadence): scan for stale `IN_DISCUSSION` items past their target resolution date.

## Changelog

- **v0.1 (2026-04-26)** — initial bootstrap. OQ-001..012 externalised from REQUIREMENTS §16. OQ-013..022 captured from KB-5 v0.1.1. 8 RESOLVED-PENDING-ADR after Oleg's 2026-04-26 session, 1 RESOLVED, 1 OPEN, 12 IN_DISCUSSION.
- **v0.1.1 (2026-04-26)** — KB-10 ADR-001..019 landed. Promoted OQ-013, OQ-014, OQ-015, OQ-016, OQ-018, OQ-019, OQ-021, OQ-022 from RESOLVED-PENDING-ADR to RESOLVED-BY-ADR-NNN. Section C status index updated to a 4-state table.
- **v0.1.2 (2026-04-26)** — Phase 1 readiness audit raised OQ-023 (KB-13 ForgeFolio), OQ-024..OQ-027 (sub-questions of resolved OQ-013/014/015/018 that block detailed Phase 1 planning). All carry proposed defaults; operator confirmation pending. New Section B' added.
- **v0.1.3 (2026-04-26)** — Operator confirmed OQ-024..OQ-027. Promoted to RESOLVED-BY-ADR-020 (NAV slice), ADR-021 (CAC ETF proxy), ADR-022 (TKAN freshness window), ADR-023 (TKAN artefact path/ownership). Section C tables updated. G0 gate now passable.
- **v0.1.4 (2026-04-26)** — ADR-026 (agentic-execution layer) added; OQ-028 (memory framework choice) and OQ-029 (implementation timing) raised. New Section B'' for layer-related questions.
- **v0.2 (2026-04-27 / M1 close)** — OQ-030 raised at M1 close (btest interpreter dispatch for non-LongShort archetypes); IN_DISCUSSION pending G2 review.
- **v0.3 (2026-04-27 / M2-IG.1 substrate ACCEPTED batch)** — OQ-030 status flipped IN_DISCUSSION → RESOLVED-BY-ADR-030 alongside the eight-ADR ACCEPTED flip. Section C tables updated. Now: 13 RESOLVED-BY-ADR (013–016, 018, 019, 021, 022, 024–027, 030); 1 RESOLVED-by-finding (017); 4 OPEN (012, 023, 028, 029); 11 IN_DISCUSSION (001–011, 020).
- **v0.4 (2026-05-06 / M2-IB.6.2c)** — OQ-031 raised: Phase 1 deployment under PMA-bound retail account. The M2-IB.6.2b/c LSE-RTH validation runs empirically confirmed that IB warning 2161 (Price Management Algo / regulatory disruptive-orders cap) binds structurally on QQL3 (3× Nasdaq leveraged ETP on LSEETF) for UK retail accounts, regardless of order type (raw MKT, OrderType.ADAPTIVE_MKT, LMT-with-aggressive-offset all subject). 0 QQL3 fills across 16 placeOrders today; IBTM (1× UCITS Treasury ETF) is unaffected. Implication: A3's effective execution profile on the leveraged equity leg is regime-dependent (fills only on flat/down moves). Four resolution options: (1) accept the constraint, monitor empirically; (2) pursue Pro Client classification for `priceManagementOff` opt-out; (3) substitute non-leveraged equity leg; (4) restructure as passive-limit-only. Working default: Option 1 for the first ~5 trading days, revisit pre-cutover. OPEN section grows to 5 (012, 023, 028, 029, **031**).
- **v0.5 (2026-06-05 / M3.3 OQ-031 resolution)** — **OQ-031 RESOLVED-BY-ADR-052** (status field only; body untouched, append-only) on the M3.2 empirical capture (QQL3 0/69 fills = 0% vs IBTM 6/6 = 100%, 2161 cap-binding 0, zero rejects/breaches/error-110): Option 1 — accept the PMA-bound leveraged-leg non-fill as a Phase-1 deployment characteristic, no code change. **OQ-032 raised** — Phase 2 A3 leveraged-leg redesign (how / whether to restore leveraged equity exposure), target Phase 2 entry. Its option set carries the *full* design space, including the leverage-preserving **margin-on-a-1×-UCITS** path (≈3× via 3:1 margin on a low-volatility UCITS that likely dodges the volatility-triggered PMA cap, per ADR-016) that the four OQ-031 options omitted — the honest scope is a *trilemma* (PRIIPs blocks US leveraged ETPs, PMA blocks UK ones, Cash blocks margin-leverage). Section C updated: RESOLVED-BY-ADR gains OQ-031→ADR-052 (14 total); OPEN swaps OQ-031 out for OQ-032 (stays at 5: 012, 023, 028, 029, **032**).
- **v0.6 (2026-06-06 / Phase-2 readiness-audit refresh)** — Three new OQs raised by the [PHASE_2_READINESS](../PHASE_2_READINESS.md) v0.1 → v0.2 refresh, driven by the incoming Phase-2 strategy candidate **R-LEV-001 "VIX Term Structure Rotation"** (TQQQ / VXX / IEF, UX6/UX1 term-structure signal, MOO execution). All target **Phase 2 entry (session-3 plan-drafting)**: **OQ-033** (UX1/UX6 VIX-futures term-structure data — **sourced from EODHD** per operator, no sfera/parquet; open part is whether EODHD's coverage suffices); **OQ-034** (UK-retail tradability of the all-US-domiciled TQQQ/VXX/IEF universe — forks on **Professional-vs-retail**: Pro lifts PRIIPs → trade the US originals, retail needs UCITS substitutes; **VXX to be replaced with a mid-term 3-/6-month vol product**; cross-links OQ-032); **OQ-035** (MOO/OPG order-type + TIF surface — INV-2/INV-3 MISSING). New **Section B'''** added. Section C OPEN grows 5 → 8 (012, 023, 028, 029, **032, 033, 034, 035**). The **Cash → Margin account-type** decision was *deliberately not* raised as a separate OQ — it is homed inside [OQ-032](#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure) (SSOT per [CONTEXT_PROTOCOL §2.1](../../CONTEXT_PROTOCOL.md)); the audit surfaces it as a Phase-2-entry operator-action dependency instead. No OQ resolved this session (audit-only; OQ-032 resolution is session 3).
