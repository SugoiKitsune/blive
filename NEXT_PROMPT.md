# Session kickoff prompt — Phase 2 plan-drafting (M3 → M4 / Phase 1 → Phase 2 boundary, session 3 of 3)

> **v1.6 (2026-06-06).** The **third and final** [CONTEXT_PROTOCOL §8.3.2](./CONTEXT_PROTOCOL.md) phase-boundary session: (1) implementation close ✓ [M3 close]; (2) readiness-audit refresh ✓ [[PHASE_2_READINESS](./docs/PHASE_2_READINESS.md) v0.2, 2026-06-06]; (3) **this session — plan-drafting**. The audit raised the agenda; this session **resolves the open decisions and drafts the Phase-2 (M4..M8) plan** in [`TASK_REGISTRY.md`](./TASK_REGISTRY.md). Single-mode (plan-drafting): the operator resolves the OQs (→ new ADRs), the agent drafts the plan — **no implementation / wire-probes / code**. The empirical validations the decisions imply (no-PMA-on-1×-UCITS probe, VXX tradability probe, EODHD VIX-futures coverage check) are **M4 plan items**, not this-session work — running them here is the §8.3.2-forbidden mode-mix.

> Working directory must be `C:\Users\olegr\PycharmProjects\blive`. If your shell starts elsewhere, switch first.

---

> **⚠️ Standing host gotchas (no Gateway/code needed this session, but keep for reference):**
>
> 1. **`uv run` is blocked by Smart App Control.** Run via the venv Python directly: `$env:PYTHONPATH = "...\src"; & "...\.venv\Scripts\python.exe" -m pytest` (likewise mypy / black / isort). Formatters are pinned (`black==26.3.1`, `isort==8.0.1`); full-tree clean. Python **3.12** ([ADR-053](docs/decisions/DECISIONS.md#adr-053--upgrade-to-python-312)).
> 2. **The IB paper account (`DUP886336`) is Cash + GBP-base** — load-bearing for the **active route B** (the Cash → Margin conversion is OQ-032's leverage-preserving lever). Route A (Professional Client) — deferred (operator not currently eligible) — would sidestep it by trading the US originals (leverage via the 3× ETP).
> 3. **`scripts/probe_ib_reconnect.py`** (M3.5 reconnect fixture) and **`scripts/probe_ib_account_ccy.py`** (M3.4 per-currency dump) exist if referenced — but do **not** run probes this session.

---

## You are the Phase-2 plan-drafting session (session 3 of 3)

`blive` is a multi-broker live execution engine, sibling to `btest`. **Phase 1 (M0 → M3) is complete; G4 PASSED.** This is the **third** of the three §8.3.2 phase-boundary sessions. The readiness audit ([PHASE_2_READINESS](./docs/PHASE_2_READINESS.md) v0.2) is the load-bearing input: it re-audited the eight dimensions against M3's *real* outcomes and raised **six cross-cutting questions** as this session's agenda.

Follow **Cognitive Cartography**: one fact has one home; stable IDs mandatory; ADRs / OQs / RETROs append-only; substrate stays aligned with reality.

### State at session entry

- **M3 CLOSED 2026-06-05; G4 PASSED. Phase-2 readiness audit refreshed 2026-06-06** ([PHASE_2_READINESS](./docs/PHASE_2_READINESS.md) v0.2 — eight dimensions re-audited; v0.1's five M3-plan questions retired; six new cross-cutting questions = this session's agenda).
- **Substrate:** DECISIONS v0.24 (ADR-001..053 ACCEPTED except ADR-021 SUPERSEDED-BY-ADR-043; next free id **ADR-054**); OPEN_QUESTIONS **v0.6** — **8 OPEN**: OQ-012, OQ-023, OQ-028, OQ-029, **OQ-032** (the central decision), **OQ-033 / OQ-034 / OQ-035** (the audit's new ones); TASK_REGISTRY v0.15 (Phase 1 plan — to be extended with the Phase-2 plan); CONTEXT_INVENTORY v0.26.
- **Tests 591 green**; mypy `src` / black / isort / lint-imports all green (full-tree). **No PROPOSED ADRs** in the working tree.
- **Incoming strategy candidate:** R-LEV-001 "VIX Term Structure Rotation" — the operator's `lab/research/r_lev_001_triple_leveraged_etf` deep-analysis notebook + `docs/STRATEGY_METADATA.md` (UX6/UX1 term-structure → TQQQ / VXX / IEF; MOO execution; ~6000%/yr turnover; backtest CAGR 157.5% / Sharpe 3.39 / MDD −33.9% / vol 46.4%; already productionised outside blive as a sfera signal → parquet).

### The six cross-cutting questions to resolve (the audit's agenda — see [PHASE_2_READINESS §"Cross-cutting summary"](./docs/PHASE_2_READINESS.md))

1. **[OQ-032](./docs/decisions/OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure) — the leverage trilemma + the Phase-2 strategy's shape.** THE central decision. The trilemma is a *retail-Cash* phenomenon, and **the operator will stay retail near-term** (not currently elective-professional-eligible), so **route B (retail) is the active path** and **route A (Professional Client) is deferred** (revisit on eligibility). The live decision is the **retail leverage lever**: margin-on-a-1×-Nasdaq-UCITS to preserve ~3× (**needs a Cash → Margin conversion** + no-PMA validation + financing parity, [KB-6 §4](./docs/kb/cost_margin_dictionary.md)) vs de-lever to 1× vs restructure; and does Phase 2 **adopt R-LEV-001** or **redesign A3**? Resolve → a new ADR (PROPOSED if it needs M4 validation before ACCEPTED). The **Cash → Margin conversion** is the lead-time-bearing operator prerequisite. (Route A — Professional Client — would trade the US originals directly and is the cleaner path if/when eligible; documented in the audit, deferred.)
2. **Is R-LEV-001 the Phase-2 target?** Resolve **[OQ-033](./docs/decisions/OPEN_QUESTIONS.md#oq-033--phase-2-vix-strategy-ux1--ux6-vix-futures-term-structure-data-sourcing)** (UX1/UX6 VIX-futures data — **from EODHD**; open part is whether EODHD's coverage suffices, IB CFE as fallback; no sfera/parquet), **[OQ-034](./docs/decisions/OPEN_QUESTIONS.md#oq-034--phase-2-vix-strategy-uk-retail-tradability-of-the-tqqq--vxx--ief-universe)** (universe & instrument design — route A trades the US originals, route B needs UCITS substitutes; **VXX → a mid-term 3-/6-month vol product** either way), **[OQ-035](./docs/decisions/OPEN_QUESTIONS.md#oq-035--phase-2-order-type--tif-surface-moo--opg-for-market-on-open-execution)** (MOO/OPG order types) + the **signal-ingestion path** (port to btest DSL vs a blive-native signal module computing from EODHD).
3. **M5-reconnect minimal fix** — a Phase-2-entry precondition (the `disconnectedEvent` honesty fix) or M5-internal? ([KB-7](./docs/kb/failure_modes.md) FM-1.)
4. **Risk-calibration & RC-catalogue timing** — does the incoming 46 %-vol / ~6000 %-turnover profile pull RC-01 / RC-11 / RC-02..07 + live-equity sizing (M3.4-unblocked) forward of M4's default?
5. **L0/L1 agentic-execution tooling ([OQ-028](./docs/decisions/OPEN_QUESTIONS.md#oq-028--which-agentic-memory-framework--tooling-for-l0l1) / [OQ-029](./docs/decisions/OPEN_QUESTIONS.md#oq-029--when-to-implement-l0l1)) — lowest-stakes, orthogonal to the trading work.** The agent layer that automates *this discipline* (auto warm-up = L0; drift watchdog = L1); its "post-G4" trigger has now fired. Default: **reaffirm deferral** (custom-light L0, revisit if manual burden bites) unless you want it as real Phase-2 scope.
6. **Phase-2 substrate prerequisites** — which MISSING / stub artefacts (DD-4 SQLite, INV-2 order types / INV-3 TIFs, KB-7 / KB-15 / INV-8 / INV-9 extensions, full RC-01..RC-08 + RC-11 catalogue) must be ≥ DRAFT *before* Phase 2 entry vs land inside their owning M4+ milestone.

### Scope (this session)

1. **Operator resolves the OQs** (esp. OQ-032 + OQ-033/034/035; reaffirm OQ-028/029). Each substantive choice → an ADR (append-only; `PROPOSED` → `ACCEPTED`; `PROPOSED`-pending-M4-validation is fine where wire-work is the gate). Flip the resolved OQs to `RESOLVED-BY-ADR-NNN` (status field only; bodies append-only).
2. **Agent drafts the Phase-2 (M4..M8) plan** in [`TASK_REGISTRY.md`](./TASK_REGISTRY.md) (extend it, or split to `TASK_REGISTRY_PHASE_2.md` if scope warrants per §8.3.2) — milestones, deliverables, gates (G5..), exit criteria, substrate transitions, dependencies; informed by the resolved OQs + the R-LEV-001 notebook + the audit's per-dimension findings. Promote the current "Sketched M4+" section into a real plan.
3. **Do NOT** run wire-probes / write code / execute the empirical validations the decisions imply — those are **M4 plan items**. Keep this single-mode (plan-drafting).

### Step 1 — Warm-up

Per [CLAUDE.md](./CLAUDE.md): read [`CONTEXT_PROTOCOL.md`](./CONTEXT_PROTOCOL.md) §0/§3/§8.3.2; [`CONTEXT_INVENTORY.md`](./CONTEXT_INVENTORY.md) (v0.26 banner + §10); **[`PHASE_2_READINESS.md`](./docs/PHASE_2_READINESS.md) v0.2** (the audit — load-bearing); **[OQ-032](./docs/decisions/OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure) + OQ-033 / OQ-034 / OQ-035** in [OPEN_QUESTIONS](./docs/decisions/OPEN_QUESTIONS.md); [RETRO-M3](./docs/retros/M3_retrospective.md); the **R-LEV-001 notebook** (`lab/research/r_lev_001_triple_leveraged_etf/` — `docs/STRATEGY_METADATA.md` + `notebooks/r_lev_001_deep_analysis.ipynb`); [`TASK_REGISTRY.md`](./TASK_REGISTRY.md) (the M4+ sketch to promote); [KB-6 §4](./docs/kb/cost_margin_dictionary.md) (financing parity — load-bearing if the margin path wins). Reply with the standard **5-line warm-up summary** and **wait for "go"**.

### Step 2 — At session end

1. Commit (surface the message draft first): new ADR(s) for the resolved OQs; OPEN_QUESTIONS status flips; the Phase-2 plan in TASK_REGISTRY; CONTEXT_INVENTORY §10 + banner; this `NEXT_PROMPT.md` replaced with **v1.7 targeting M4 (Phase-2 entry / first implementation milestone)**.
2. This **closes the §8.3.2 three-session phase boundary** — Phase 2 implementation begins at M4.

### Discipline reminders

- **Single mode (plan-drafting).** No code / wire-probes — §8.3.2. Empirical validations the decisions imply are M4 deliverables, not this session.
- **OQ-032 is the keystone** — resolve it first; OQ-033/034/035 largely follow from whether R-LEV-001 is adopted.
- **Decision option-sets must include the intent-preserving option** (the RETRO-M3 discipline note — the OQ-031 omission lesson). For OQ-032 the intent-preserving paths are **Professional-Client (trade the US originals) and margin-on-a-1×-UCITS** — surface the *full* space before recommending.
- Stable IDs everywhere; OQs get target dates; append-only ADR/OQ/RETRO bodies. When in doubt: re-read the protocol, ask, do not guess.

---

**Begin warm-up now.**
