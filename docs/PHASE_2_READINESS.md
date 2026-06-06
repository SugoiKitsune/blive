---
id: PHASE_2_READINESS
title: Phase 2 Readiness Audit
status: DRAFT
owner: shared
last_reviewed: 2026-06-06
version: 0.2
sources:
  - docs/PHASE_1_READINESS.md
  - docs/retros/M3_retrospective.md
  - docs/retros/M2-IB_retrospective.md
  - TASK_REGISTRY.md
  - CONTEXT_INVENTORY.md
  - lab/research/r_lev_001_triple_leveraged_etf (incoming Phase-2 strategy candidate; external to this repo)
depends_on:
  - RETRO-M3
  - RETRO-M2-IB
  - PHASE_1_READINESS
  - OQ-032
referenced_by: []
---

# Phase 2 Readiness Audit

## Purpose

A phase-boundary gate document. Before drafting the **Phase 2
(M4 → M8)** plan, this audit checks whether we have enough
substrate to plan well, and identifies what specifically blocks
or merely informs the planning. Mirrors
[`PHASE_1_READINESS`](./PHASE_1_READINESS.md) in shape; informed
this time by the *real* outcomes of **all of Phase 1 (M0 → M3,
G4 PASSED)** rather than the pre-execution architectural state.

Per [CONTEXT_PROTOCOL §8.3.2](../CONTEXT_PROTOCOL.md), this is the
**second of the three** M3 → M4 / Phase-1 → Phase-2 boundary
sessions: (1) implementation close ✓ [M3 close]; (2) **this
session — readiness-audit refresh**; (3) plan-drafting. It is an
**audit, single-mode** — it does **not** draft the Phase-2 plan,
resolve [OQ-032](./decisions/OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure),
or write code.

**Wall-clock state**: as of the `M3-close` commit / tag on
2026-06-05 (+ the ADR-053 Python-3.12 tooling commit `601b1a2`).
G4 PASSED on all 10 exit criteria. The load-bearing input here is
[RETRO-M3 v1.0](./retros/M3_retrospective.md); substrate is
internally consistent, no PROPOSED ADRs remain, 591 tests green.

## What changed since v0.1 (the refresh)

[v0.1](#changelog) was written 2026-05-06 at the `M2-IB.6-close`
commit — **before M3 ran**. At that point "M3" and "Phase 2" were
conflated: v0.1 audited readiness to draft *the M3 plan* (which
it called "the M3 / Phase 2 plan"). M3 has since been planned,
executed, and **closed as the final Phase-1 milestone** (M0 → M3
= Phase 1; G4 PASSED). The genuine phase boundary is therefore
**now**, at M3 → M4, and the forward question is the *real*
Phase 2 (M4 .. M8) plan that session 3 drafts.

v0.2 does three things:

1. **Closes v0.1's loop** — the five cross-cutting questions v0.1
   raised as the M3-plan agenda are now *answered by M3*; see the
   table below.
2. **Re-audits the eight dimensions** against M3's real outcomes
   (the leverage trilemma / [OQ-032](./decisions/OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure),
   the M3.4 equity-bug fix, the M3.5 reconnect gap / KB-7 FM-1,
   the structural QQL3 non-fill / [ADR-052](./decisions/DECISIONS.md#adr-052--phase-1-accepts-the-pma-bound-leveraged-leg-non-fill-oq-031-option-1),
   the ADR-050/051 unit-of-quote + tick-grid fixes). Each
   dimension carries a **Δ since v0.1** note.
3. **Folds in the incoming Phase-2 strategy candidate** —
   R-LEV-001 "VIX Term Structure Rotation" (the operator's
   `lab/research/r_lev_001_triple_leveraged_etf` deep-analysis
   notebook + `STRATEGY_METADATA.md`) — and raises the new OQs it
   forces (OQ-033 / OQ-034 / OQ-035).

### The incoming Phase-2 strategy candidate (R-LEV-001) in one paragraph

A **VIX term-structure rotation**: ratio = UX6 / UX1 (6-month vs
front-month VIX futures); compare to its 252-day rolling median.
**Risk-ON / contango** (ratio > median) → 100% **TQQQ**;
**Risk-OFF / backwardation** (ratio < median) → 100% **VXX** for
the first 3 days (capture the vol spike), then 100% **IEF** from
day 4 (safe harbour); counter resets on every risk-on flip.
**MOO** (Market-On-Open, T+1) execution; ~42 regime switches/year
(~6000%/yr turnover). Backtest 2011–2026: CAGR 157.5%, Sharpe
3.39, MDD −33.9%, vol 46.4%. Already productionised *outside*
blive (sfera signal `vix_vxx_rotation.py` → a `signals` parquet),
sourcing UX1/UX6 from Bloomberg (`bbgidx.index_prices`) — though
blive will **re-source from EODHD**, not consume sfera's output.
For blive this is **more** data-, leverage-, and vol-dependent
than the current A3; its all-US-domiciled universe re-raises the
retail-tradability question — which **Professional-Client
classification would lift** (route A), or a retail substitution
must solve (route B) (see Dimensions 1, 2, 3, 7).

### v0.1's five cross-cutting questions — now answered by M3

| v0.1 question (the M3-plan agenda) | M3 outcome |
|---|---|
| 1. OQ-031 sequencing (resolve vs inform) | **Both** — M3 ran the bounded empirical capture *and* resolved OQ-031: [ADR-052](./decisions/DECISIONS.md#adr-052--phase-1-accepts-the-pma-bound-leveraged-leg-non-fill-oq-031-option-1) Option 1 (accept the non-fill). |
| 2. Empirical fill-rate window scope | Re-scoped (plan-call #6) to a **bounded deterministic capture**; result: QQL3 **0/69** fills vs IBTM **6/6**; 2161 cap-binding 0; zero rejects/breaches/error-110. |
| 3. EODHD-vs-IB unit-of-quote reconciliation timing | **Shipped in M3** — [ADR-050](./decisions/DECISIONS.md#adr-050--eodhd-vs-ib-unit-of-quote-conversion-at-sizing-time-hybrid-b-now--a-later-free-md-only) (magnitude, ÷10) + [ADR-051](./decisions/DECISIONS.md#adr-051--normalize-ib-order-prices-to-the-contract-tick-grid-at-submit-time) (tick-grid) + RC-10 (price sanity). Was *two* entangled error-110 bugs. |
| 4. Strategy-slot scope (A3-only vs invite A1/A1a) | **A3-only** (plan-call #4); A1/A1a stay forward-listed. |
| 5. Phase-2 substrate prerequisites | **Partially** — KB-7 / KB-15 / INV-8 / INV-9 are now DRAFT stubs (M3 produced them); the full RC catalogue + DD-4 (SQLite) remain M4. |

The v0.1 questions are retired. The **new** agenda — what gates the
Phase-2 plan-drafting session — is in the next section.

## Conventions

Status per dimension: ✓ READY · ⚠ PARTIAL · ✗ BLOCKING.

The question being asked is now: **can we draft a credible Phase 2
(M4 .. M8) plan in session 3, or does something have to be
settled first?**

---

## Cross-cutting summary — six questions that gate the Phase-2 plan-drafting session

These become the *agenda* of session 3 (plan-drafting), not its
output. None is resolved here. They supersede v0.1's five.

1. **[OQ-032](./decisions/OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure)
   — the leverage trilemma and the Phase-2 strategy's shape.**
   The trilemma (PRIIPs blocks US leveraged ETPs per
   [ADR-047](./decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043);
   PMA / warning 2161 blocks UK leveraged ETPs per
   [ADR-049](./decisions/DECISIONS.md#adr-049--ordertypeadaptive_mkt-for-ibalgo-adaptive-routing-empirical-pma-cap-finding);
   Cash blocks margin) binds for a **retail** account — and **the
   operator will stay retail near-term** (not currently eligible for
   elective-professional classification), so **route B (retail) is
   the active path** and **route A (Professional Client) is
   deferred** (documented below; revisit if eligibility changes).
   The live OQ-032 decision is therefore the **retail leverage
   lever**:
   - **Preserve ~3× via margin on a 1× Nasdaq-100 UCITS** (OQ-032
     Option 1) — hold a UK-retail-eligible 1× Nasdaq-100 UCITS ETF
     and obtain ≈3× through 3:1 margin (a low-vol 1× UCITS very
     likely dodges the 2161 PMA cap; **needs a Cash → Margin
     account conversion** + a no-PMA validation + financing parity,
     [KB-6 §4](./kb/cost_margin_dictionary.md)).
   - **De-lever to 1×** (Option 3) — drop the leverage; simplest;
     changes the strategy's risk/return.
   - **Restructure** (Option 4) — redefine around the cap; fresh
     ADR + parity envelope.
   **The operator picks among these in session 3** (this audit does
   not resolve it). The **Cash → Margin** conversion is the
   lead-time-bearing prerequisite for the leverage-preserving
   sub-path (the paper account `DUP886336` is Cash + GBP-base).
   *Deferred — route A (Professional Client):* lifts PRIIPs (trade
   the US originals; leverage via the 3× ETP; Cash suffices) but
   needs elective-pro eligibility (2 of 3 — ~£/€500k portfolio /
   financial-sector experience / ≥ 10 significant trades per
   quarter) the operator does not currently meet; the cleaner path
   if/when eligible. Both routes are homed inside OQ-032 (margin
   path = Option 1; Professional = Option 2).
2. **Is the incoming VIX strategy (R-LEV-001) the Phase-2
   target?** It forces three new OQs:
   **[OQ-033](./decisions/OPEN_QUESTIONS.md#oq-033--phase-2-vix-strategy-ux1--ux6-vix-futures-term-structure-data-sourcing)**
   (UX1/UX6 VIX-futures term-structure data — to be sourced from
   **EODHD**; the open part is whether EODHD's coverage + history
   suffice),
   **[OQ-034](./decisions/OPEN_QUESTIONS.md#oq-034--phase-2-vix-strategy-uk-retail-tradability-of-the-tqqq--vxx--ief-universe)**
   (universe & instrument design — route A makes the US originals
   tradeable, route B needs UCITS substitutes; **the VXX leg is
   replaced with a mid-term 3-/6-month vol product either way** — a
   deliberate design choice, less roll-decay than VXX's
   front-month), and
   **[OQ-035](./decisions/OPEN_QUESTIONS.md#oq-035--phase-2-order-type--tif-surface-moo--opg-for-market-on-open-execution)**
   (MOO/OPG order types blive lacks) — plus a **signal-ingestion
   path** call (port R-LEV-001 to the btest DSL vs a blive-native
   signal module computing from EODHD; **no** sfera / static-parquet
   handoff). Session 3 decides: adopt, adapt, or defer it.
3. **M5-reconnect minimal fix — a Phase-2-entry precondition, or
   M5-internal?** The M3.5 drill confirmed no native disconnect
   detection ([KB-7](./kb/failure_modes.md) FM-1); RETRO-M3
   recommends at least the `disconnectedEvent` fix for any
   multi-day live run. The full watchdog + continuous
   reconciliation is M5. Where does the minimal fix sit?
4. **Risk-calibration & RC-catalogue timing.** The incoming
   strategy's vol 46.4% / MDD −33.9% / ~6000% turnover makes RC-01
   (gross leverage) / RC-11 (drawdown scaling) / RC-02..07
   (exposure / concentration) load-bearing *earlier* than M4's
   default. M3.4 also unblocked wiring **live equity** (now a
   correct consolidated BASE total) into sizing (still synthetic
   $100k). Does session 3 pull the full RC catalogue + live-equity
   sizing forward?
5. **L0/L1 agentic-execution tooling
   ([OQ-028](./decisions/OPEN_QUESTIONS.md#oq-028--which-agentic-memory-framework--tooling-for-l0l1)
   / [OQ-029](./decisions/OPEN_QUESTIONS.md#oq-029--when-to-implement-l0l1))
   — lowest-stakes; orthogonal to the trading work.** ADR-026 /
   [CONTEXT_PROTOCOL §11](../CONTEXT_PROTOCOL.md) plan an agent
   layer that automates *this discipline itself* (auto substrate
   warm-up = L0; a drift / staleness watchdog = L1). The plan
   parked it "post-G4"; G4 has now passed, so the trigger has
   fired — the only question is build-any-now vs keep-deferring.
   **Proposed default: reaffirm deferral (custom-light L0 only;
   revisit if the manual substrate burden bites).** Flagged for
   completeness; not load-bearing for the Phase-2 plan.
6. **Phase-2 substrate prerequisites.** Which MISSING / stub
   artefacts must be ≥ DRAFT *before* Phase 2 entry vs land inside
   their owning M4+ milestone: DD-4 `storage_schemas` (MISSING —
   M4 SQLite), **INV-2 order types / INV-3 TIFs** (MISSING — now
   load-bearing via OQ-035), KB-7 / KB-15 / INV-8 / INV-9 (DRAFT
   stubs — extend?), full RC-01..RC-08 + RC-11 catalogue.

---

## 1. Strategy & universe — ⚠ PARTIAL (leverage-trilemma-gated; incoming strategy reinforces it)

**Δ since v0.1.** v0.1's gate was OQ-031 (deployment under the
PMA cap). M3 *resolved* OQ-031 — [ADR-052](./decisions/DECISIONS.md#adr-052--phase-1-accepts-the-pma-bound-leveraged-leg-non-fill-oq-031-option-1)
Option 1, on the M3.2 capture (QQL3 **0/69** vs IBTM **6/6**) —
and surfaced the deeper structural finding: the **leverage
trilemma** ([OQ-032](./decisions/OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure)).
The Phase-2 strategy candidate (R-LEV-001) is now known and
*intensifies* the same constraint.

- **READY**
  - A3 (`triple_lev_sma_filter_dsl`) is wire-validated and
    deployed (Phase 1) on the PRIIPs-compliant `QQL3` / `IBTL` /
    `IBTM` universe per [ADR-047](./decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043);
    multi-instrument pipeline + `LongShortPortfolio` dispatch
    ([ADR-044](./decisions/DECISIONS.md#adr-044--multi-instrument-pipeline-support-companion-to-adr-043) /
    [ADR-045](./decisions/DECISIONS.md#adr-045--longshortportfolio-btest-dispatch-extends-adr-030))
    proven.
  - The **deployment characteristic is now empirically
    pinned**: the leveraged equity leg (QQL3) structurally does
    not fill on the PMA-bound Cash account; Phase 1 runs
    Treasury-dominated (ADR-052). No ambiguity remains for
    Phase 1.
  - The incoming R-LEV-001 signal is **already validated and
    productionised** elsewhere (sfera), so blive inherits a
    proven signal, not an unproven idea — its logic + metadata are
    a known quantity to port (blive recomputes from EODHD; no
    sfera / parquet dependency).
- **GAPS**
  - **The intended 3× equity exposure is unrealised** on the
    current account (OQ-032). A3's regime profile is partly
    inverted; backtest CAGR/Sharpe/MDD do not carry forward; the
    M7 parity envelope re-derives.
  - **The incoming VIX strategy's universe is entirely
    US-domiciled** (TQQQ, VXX, IEF) → KID-less for UK retail, so on
    the **active route B (retail)** the whole book needs UCITS
    substitutes: **TQQQ → a 1× Nasdaq-100 UCITS + the OQ-032 margin
    path** (to recover ~3×), **IEF → IBTM** (known), and **VXX → a
    mid-term 3-/6-month vol UCITS** (a deliberate design choice —
    less roll-decay than VXX's front-month — which must itself be
    UK-retail-eligible + clear the PMA cap). Instrument selection +
    the no-PMA / tradability probes are session-3 / M4 work
    (→ OQ-034). (Route A would trade the US originals directly, but
    is deferred — see the cross-cutting agenda.)
  - **Signal-ingestion path undecided** — port R-LEV-001 to the
    btest DSL (so blive's [ADR-010](./decisions/DECISIONS.md#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import)
    engine reuse applies) vs a blive-native signal module computing
    the UX6/UX1 regime from EODHD data. (No sfera / static-parquet
    handoff — blive re-sources from EODHD per the operator.)
  - A1 (`xsec_momentum_long_short_sp500`) / A1a (`lagging_indecies`)
    remain un-exercised against IB (unchanged from v0.1).
- **BLOCKED**
  - **OQ-032** OPEN — the central Phase-2 decision; resolved in
    session 3.
  - **OQ-034** OPEN — the universe's tradability + the VXX →
    mid-term-vol design, which fork on the route A/B choice.
- **Phase-2 entry question.** Which strategy is Phase 2's target
  — A3 **redesigned** to restore leverage (OQ-032), or the VIX
  rotation **adopted** (OQ-034) — and on which route (A
  Professional / B retail)? On route A both strategies trade their
  US originals directly; on route B both need the UCITS-substitute
  treatment.

---

## 2. Data feeds — ⚠ PARTIAL (Phase-1 reconciliation shipped; VIX-futures feed is a new gap)

**Δ since v0.1.** v0.1's headline gap — the EODHD-vs-IB QQL3 10×
discrepancy — is **resolved**: ADR-050 (unit-of-quote magnitude;
`MANUAL_SCALE` ÷10 in `adapters/eodhd/conventions.py`) + ADR-051
(tick-grid snap) + RC-10 (price sanity, INV-4 v0.2), with
[KB-15](./kb/parity_methodology.md) `parity_methodology` written
as a DRAFT stub. The *new* data gap is the incoming strategy's
VIX-futures dependency.

- **READY**
  - EODHD daily refresh + hybrid per-instrument routing
    ([ADR-017](./decisions/DECISIONS.md#adr-017--live-data-hybrid-eodhd--ib-streaming-per-instrument-routing));
    `IBMarketData` historical bars wire-validated.
  - **Unit-of-quote reconciliation solved for the Phase-1
    universe** (ADR-050/051 + RC-10); the convention catalogue is
    the curation surface for any future vendor-vs-IB divergence.
- **GAPS**
  - **UX1 / UX6 VIX-futures term-structure data is not yet sourced
    by blive** (→ [OQ-033](./decisions/OPEN_QUESTIONS.md#oq-033--phase-2-vix-strategy-ux1--ux6-vix-futures-term-structure-data-sourcing)).
    **Decision taken (operator, 2026-06-06): source from EODHD** —
    no sfera coupling, no static-signal parquet handoff. The open
    part is empirical, not a channel choice: whether EODHD carries
    a usable VIX-futures term-structure series (UX1/UX6, or
    continuous front-/6-month) with ≥ 252-day history for the
    rolling-median warm-up; an IB CFE futures subscription is the
    fallback only if EODHD's coverage falls short.
  - **No live IB market-data subscription** — sizing / LMT still
    off the EODHD close (a constraint the operator *accepted*
    permanently as ADR-050's free-MD-only A-route). Carries into
    Phase 2 unless revisited.
  - The **VXX-leg replacement** (a mid-term 3-/6-month vol product,
    OQ-034) needs its own EODHD reference series + execution price.
- **BLOCKED**
  - Whether EODHD's VIX-futures coverage suffices (OQ-033) — an
    early-M4 probe; any live-MD subscription trade-off.
- **Phase-2 entry question.** Does EODHD carry a VIX-futures
  term-structure series sufficient for the UX6/UX1 signal
  (coverage + ≥ 252-day history) and for the chosen mid-term vol
  substitute — or is an IB CFE futures subscription needed as a
  fallback (OQ-033)?

---

## 3. Engine surface — ✓ READY (for daily-RTH A3); ⚠ PARTIAL (MOO + replace() gaps for Phase-2 candidates)

**Δ since v0.1.** The order-type surface is **unchanged** by M3
(M3 was deployment-decision + data + reconciliation; it added
RC-10 in *risk*, not new order types). The incoming strategy's
MOO execution makes the v0.1 "no MOC/LOC/OPG" gap concrete and
load-bearing.

- **READY**
  - `MKT` / `LMT` / `ADAPTIVE_MKT` ([ADR-049](./decisions/DECISIONS.md#adr-049--ordertypeadaptive_mkt-for-ibalgo-adaptive-routing-empirical-pma-cap-finding))
    + per-symbol `order_type_by_symbol`; multi-instrument routing
    correct; FSM emission wire-validated across SUBMITTED →
    ACCEPTED → CANCELED / REJECTED / FILLED ([INV-14](./inv/ib_error_codes.md)
    reason-extraction taxonomy).
  - Tick-grid normalisation at submit (ADR-051) — orders now
    conform to the contract tick grid (eliminated error 110 on
    LSEETF).
- **GAPS**
  - **MOO (Market-On-Open) is not in the surface** (→ [OQ-035](./decisions/OPEN_QUESTIONS.md#oq-035--phase-2-order-type--tif-surface-moo--opg-for-market-on-open-execution)).
    R-LEV-001 executes MOO/T+1; blive has no `OPG`-class order
    type or opening-auction TIF. INV-2 (order types) / INV-3
    (TIFs) remain MISSING.
  - `IBBroker.replace()` still raises `NotImplementedError`
    (M2-IB.4b deferred) — the VIX strategy's high turnover does
    daily *full-book rotation*, not in-flight modification, so
    replace() is likely still **not** required; confirm in
    session 3.
- **BLOCKED**
  - None structurally — the gaps land in their own milestone when
    a strategy needs them; OQ-035 is the scope decision.
- **Phase-2 entry question.** Does Phase 2 add MOO/OPG + an
  opening-auction TIF (OQ-035), and at which milestone — *before*
  the VIX strategy can run, or as an M4 deliverable alongside it?

---

## 4. Risk engine — ⚠ PARTIAL (M1-subset + RC-10; incoming profile raises the stakes)

**Δ since v0.1.** RC-10 (price sanity) is **now implemented**
(ADR-050; INV-4 v0.2) — the M1-subset grew to RC-08 / RC-09 /
**RC-10** / RC-12 / RC-13. M3.4's equity fix means the RiskEngine
*can now trust* `AccountSnapshot.equity` (a latent bug, removed).
But M3's capture was deliberately bounded and QQL3-non-filling, so
it produced little P&L calibration data — that gap persists, and
the incoming strategy sharpens it.

- **READY**
  - RC-08 / RC-09 / **RC-10** / RC-12 / RC-13 implemented and
    exercised; no-bypass enforced ([ADR-008](./decisions/DECISIONS.md#adr-008--riskengine-no-bypass-architectural-enforcement)).
  - Zero breaches across the M3 captures (clean — though partly
    because the leveraged leg didn't trade).
  - `AccountSnapshot.equity` is now the consolidated BASE total
    (M3.4; [DD-1](./dd/domain_objects.md) v0.3) — sizing / risk
    can finally read live equity correctly.
- **GAPS**
  - RC-01 (gross leverage) / RC-02..RC-07 (exposure / weight /
    daily loss / per-strategy + global rate limits / concentration)
    / RC-11 (drawdown scaling) still **not implemented** — full
    catalogue at [INV-4](./inv/risk_checks.md).
  - **Calibration data still thin** — the bounded M3 capture +
    non-filling leveraged leg gave little live P&L to fit
    thresholds against ([OQ-012](./decisions/OPEN_QUESTIONS.md#oq-012--parity-tolerance-bands-are-8-numbers-right) /
    [PHASE_1_READINESS §5](./PHASE_1_READINESS.md)).
  - **Sizing still off a synthetic $100k view** — the M3.4 fix
    unblocked wiring live equity in, but that wiring is M4/M5.
- **BLOCKED**
  - Full-catalogue calibration needs a richer live (paper) window
    than M3 produced.
- **Phase-2 entry question.** Does the incoming strategy's
  aggressive profile (vol 46.4%, MDD −33.9%, ~6000% turnover)
  force RC-01 / RC-11 / RC-02..07 + live-equity sizing *before* it
  runs, rather than M4's default ordering? The conservative
  Phase-1 NAV slice ([ADR-020](./decisions/DECISIONS.md#adr-020--phase-1-nav-slice-510-of-total-cap-10):
  5–10 %, cap 10 %) was sized for a technology-validation phase,
  not a 46 %-vol strategy.

---

## 5. Reconciliation (M5 territory) — ⚠ PARTIAL (mixed-currency + KB-7 stub done; native reconnect + persistence still M5/M4)

**Δ since v0.1.** Both v0.1 gaps here moved. (a) **Mixed-currency
P&L reconciliation is done** — M3.4 reconciled USD + GBP live
*and found + fixed* the `AccountSnapshot.equity`-reads-base-sleeve
bug (~10 % understatement). (b) **KB-7 `failure_modes` is now
DRAFT** (FM-1 from the M3.5 chaos drill). The reconnect gap is now
*documented* rather than unknown — but it is still a gap.

- **READY**
  - Startup snapshot via `reqAccountUpdatesAsync`; 30 s
    diff-suppress `AccountUpdate` timer ([ADR-033](./decisions/DECISIONS.md#adr-033--accountupdate-emission-timer-30s-diff-suppress));
    crash-only restart = cold-start ([ADR-009](./decisions/DECISIONS.md#adr-009--crash-only-design-restart-path--cold-start-path)).
  - **Mixed-currency reconciliation validated live** on
    `DUP886336` (equity £1,003,855; DD-1 v0.3) — the v0.1
    "exercised synthetically" gap is closed.
  - **KB-7 FM-1** catalogues the Gateway-drop / daily-restart
    failure mode + the external recovery path + reconciliation,
    with `scripts/probe_ib_reconnect.py` as the fixture.
- **GAPS**
  - **No native disconnect detection / auto-reconnect** (KB-7
    FM-1): `IBBroker.is_connected` stays stale-`True`; recovery
    needs `disconnect()+connect()`; a Gateway restart raises
    **IB 10141** (paper disclaimer) + a `clientId`-in-use
    transient. RETRO-M3 recommends the *minimal* `disconnectedEvent`
    fix for any multi-day run; the full watchdog + continuous
    reconciliation loop is **M5**.
  - **No persistent state** — `InMemoryPersistence` only; SQLite
    ([ADR-006](./decisions/DECISIONS.md#adr-006--sqlite-for-persistence-in-v1) +
    DD-4 `storage_schemas` MISSING) is the **M4** cut.
  - Daily 23:45 ET restart still operator-managed manual relogin
    ([ADR-040](./decisions/DECISIONS.md#adr-040--phase-1-deployment-target-windows-host-with-native-ib-gateway)).
- **BLOCKED**
  - M5 work forward-planned per TASK_REGISTRY M4+ sketch.
- **Phase-2 entry question.** Is the **minimal `disconnectedEvent`
  fix a Phase-2-entry precondition** (cross-cutting Q3), or does it
  wait for M5 proper? The incoming strategy's daily MOO + ~42
  switches/year raises the cost of a silently-missed reconnect
  (a missed open = a missed rotation). Does Phase 2 entry also
  require SQLite persistence (M4) for restart-safe position
  tracking?

---

## 6. Operations / observability — ⚠ PARTIAL (M3.2 stubs + RunRecord sink exist; full stack still M4+)

**Δ since v0.1.** v0.1 flagged INV-8 / INV-9 MISSING and "no
fill-rate dashboard". M3.2 produced **INV-8 `metrics` + INV-9
`alerts` DRAFT stubs** and the per-run `RunRecord` results sink
(`runtime/m3_2_record.py` → `~/.blive/data/m3_2_window/runs.jsonl`)
capturing fill-rate, regime-flip count, 2161 cap-binding, breach
count, FSM-trace coverage. So a minimal *capture* surface exists
(not a live dashboard).

- **READY**
  - `ConnectionStatus` / `ArtefactFreshnessWarning` /
    `AccountUpdate` / `RiskBreach` events ([INV-5](./inv/domain_events.md) +
    [DD-2](./dd/event_schemas.md)); dual-channel `trade.statusEvent`
    + `ib.errorEvent` subscription.
  - **INV-8 / INV-9 DRAFT stubs + the RunRecord sink** — the
    empirical-window metrics/alerts are catalogued and captured.
- **GAPS**
  - No structured-logging stack (M4); no Prometheus / Grafana, no
    Web UI (M6 / M7); the RunRecord sink is a file, not a live
    fill-rate dashboard.
  - Daily NDJSON trade tape still unverified at scale (M5 / KB-7).
- **BLOCKED**
  - M4 / M6 / M7 deliverables forward-planned.
- **Phase-2 entry question.** What observability is *load-bearing*
  for the incoming strategy's higher activity (per-open fill-rate,
  turnover, regime-switch visibility, mixed-currency P&L) versus
  nice-to-have (full Prometheus / Grafana) — and does the
  RunRecord sink suffice for Phase-2 entry, or does M4 pull
  structured logging forward?

---

## 7. Regulatory / compliance — ⚠ PARTIAL (Professional-vs-retail is the gating choice; incoming book is all US-domiciled)

**Δ since v0.1.** The PRIIPs picture sharpened into the trilemma
(OQ-032) — a **retail** phenomenon. **The operator will stay
retail near-term** (not currently elective-professional-eligible),
so PRIIPs **binds**: the incoming strategy's entirely-US-domiciled
universe (TQQQ / VXX / IEF) must be served by UK-retail-eligible
UCITS substitutes. (Professional classification — route A — would
lift the KID block and is the cleaner path if/when eligible;
deferred.)

- **READY**
  - PRIIPs / KID reach catalogued ([KB-9 §5.5](./kb/uk_regulatory.md));
    Phase-1 universe substituted (ADR-047). HMRC + MiFID-II
    audit-trail shape satisfied. Deployment target codified
    (ADR-040).
- **GAPS**
  - **Route B (retail) is active**, so the US-domiciled universe is
    PRIIPs-blocked and needs UCITS substitutes: IEF → IBTM (solved);
    TQQQ → a 1× Nasdaq-100 UCITS + the OQ-032 margin path; the
    **VXX-replacement mid-term vol product must itself be a
    UK-retail-eligible UCITS** — diligence required (→ OQ-034).
  - **Professional-Client classification (route A; OQ-032 Option 2)
    is deferred** — it would lift the PRIIPs/KID block (a
    *retail*-only requirement) and let the US originals trade
    directly (also unlocking `priceManagementOff` for the PMA cap),
    but the operator is **not currently eligible** (MiFID II
    2-of-3) and would lose retail protections (FSCS, negative-
    balance protection, Ombudsman). Revisit if eligibility changes.
  - No CFD-specific KB-9 section; cross-exchange / non-UK-account
    surfaces uncatalogued (unchanged from v0.1).
- **BLOCKED**
  - Operator's accountant / lawyer review (off-blive);
    Pro-Client + Cash→Margin account decisions (operator).
- **Phase-2 entry question.** On the active retail path: does a
  UK-retail-eligible 1× Nasdaq-100 UCITS **and** a mid-term vol
  UCITS exist that clear PRIIPs / complex-product diligence (beyond
  KB-9 §5.5) and the PMA cap?

---

## 8. OQs that gate Phase 2 entry — ⚠ PARTIAL (8 OPEN: 4 carried + OQ-032 + 3 new)

**Δ since v0.1.** OQ-031 **resolved** (ADR-052). OQ-032 **raised**
(the central Phase-2 decision). This audit raises **three new OQs**
(OQ-033 / OQ-034 / OQ-035). The OPEN set is now eight.

The eight OPEN OQs in [KB-11 v0.6](./decisions/OPEN_QUESTIONS.md):

| OQ | Question | Target | Phase-2-entry posture |
|----|----------|--------|----------------------|
| [OQ-012](./decisions/OPEN_QUESTIONS.md#oq-012--parity-tolerance-bands-are-8-numbers-right) | Parity tolerance bands | calibrate at M7 | Defer; M7 is native. M3's thin capture means Phase-2 paper data seeds it. |
| [OQ-023](./decisions/OPEN_QUESTIONS.md#oq-023--forgefolio-read-only-integration-with-blive-event-log) | ForgeFolio integration | post-M8 | Orthogonal to Phase 2 entry. |
| [OQ-028](./decisions/OPEN_QUESTIONS.md#oq-028--which-agentic-memory-framework--tooling-for-l0l1) | Agentic memory framework (L0/L1) | before L0/L1 impl | **Due now** — Phase 2 entry *is* the post-G4 trigger. |
| [OQ-029](./decisions/OPEN_QUESTIONS.md#oq-029--when-to-implement-l0l1) | Timing of L0/L1 | at/before G4 | **Due now** — same trigger; reaffirm or commit. |
| [OQ-032](./decisions/OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure) | Leverage-leg redesign (the trilemma) | Phase 2 entry | **Load-bearing — the central session-3 decision.** |
| [OQ-033](./decisions/OPEN_QUESTIONS.md#oq-033--phase-2-vix-strategy-ux1--ux6-vix-futures-term-structure-data-sourcing) | UX1/UX6 VIX-futures data sourcing | Phase 2 entry | Load-bearing *if* R-LEV-001 is adopted. |
| [OQ-034](./decisions/OPEN_QUESTIONS.md#oq-034--phase-2-vix-strategy-uk-retail-tradability-of-the-tqqq--vxx--ief-universe) | Incoming universe UK-retail tradability (VXX) | Phase 2 entry | Load-bearing *if* R-LEV-001 is adopted. |
| [OQ-035](./decisions/OPEN_QUESTIONS.md#oq-035--phase-2-order-type--tif-surface-moo--opg-for-market-on-open-execution) | MOO/OPG order-type + TIF surface | Phase 2 entry | Scope decision; impl may be M4. |

- **READY** — every OPEN OQ has a target date + options / proposed
  default; append-only discipline preserved.
- **GAPS** — OQ-032 + OQ-033/034/035 are unresolved and *coupled*
  (they all turn on which Phase-2 strategy is chosen); OQ-028/029
  need at least a reaffirmed default.
- **BLOCKED** — OQ-032/033/034 are operator decisions for session 3.
- **Phase-2 entry question.** Of the eight, which must be resolved
  *in session 3* before the Phase-2 plan can be drafted
  (OQ-032 certainly; OQ-033/034/035 if R-LEV-001 is the target)
  versus carried into Phase 2 as scheduled work (OQ-012, OQ-023)?

---

## Verdict

**For drafting the Phase 2 (M4 .. M8) plan in session 3**:
**READY at milestone-headline granularity, conditional** on the
six cross-cutting questions becoming session 3's agenda. The
substrate is internally consistent post-M3-close; no PROPOSED
ADRs; no STABLE artefact has gone STALE; KB-2 / KB-3 are STABLE
v1.0 (Phase-1 surface — note they re-open to STALE the moment
Phase 2 introduces VIX futures / a new account type, per their own
scope caveat).

**For drafting Phase 2 at detailed deliverable granularity**:
**NOT READY until session 3 resolves the strategy question.**
Almost every M4+ deliverable's shape depends on the OQ-032 /
OQ-034 outcome:

- **Route B (retail) is the active path** (operator not currently
  Professional-eligible; route A deferred). So if Phase 2 **adopts
  R-LEV-001**, M4+ must: source EODHD VIX-futures data (OQ-033);
  build a UK-retail UCITS universe — a 1× Nasdaq-100 UCITS (+ the
  OQ-032 margin path to recover ~3×), IBTM, and a **mid-term vol
  UCITS** replacing VXX (OQ-034); add MOO/OPG order types (OQ-035);
  and stand up the full RC catalogue for a 46 %-vol book;
- the **OQ-032 retail lever** is itself a session-3 sub-decision —
  margin-on-1×-Nasdaq-UCITS (preserve ~3×; needs Cash → Margin +
  no-PMA validation + financing parity, KB-6 §4) vs de-lever to 1×
  vs restructure;
- if Phase 2 **redesigns A3** instead of adopting R-LEV-001, the
  universe and parity envelope shift but the same retail-lever
  question applies.

**The single highest-leverage operator-side prerequisite is now the
Cash → Margin account conversion** — it gates the
leverage-preserving margin-on-1×-UCITS sub-path (the paper account
`DUP886336` is Cash + GBP-base) and has real lead time; surface it
before session 3. (Route A / Professional Client is deferred until
the operator is eligible; it remains the cleaner path and is kept
documented for revisiting.)

The plan-drafting session can sketch M4 .. M8 to milestone-headline
level (as Phase 1 did at the equivalent point), but detailed M4
deliverables should wait until the strategy question is answered.

## New OQs raised by this audit

Appended to [KB-11](./decisions/OPEN_QUESTIONS.md) (v0.5 → v0.6),
all targeting **Phase 2 entry (M3 → M4 boundary / session 3)**:

- **OQ-033** — Phase-2 VIX strategy: UX1 / UX6 VIX-futures
  term-structure data **from EODHD** (open part: whether EODHD's
  coverage + history suffice; IB CFE futures subscription as the
  fallback). No sfera / static-parquet handoff.
- **OQ-034** — Phase-2 VIX strategy: universe & instrument design
  — route A (Professional Client → US originals tradeable) vs
  route B (retail → UCITS substitutes); the **VXX leg replaced by
  a mid-term 3-/6-month vol product** either way (design choice).
  Cross-links OQ-032 + KB-9 §5.5.
- **OQ-035** — Phase-2 order-type & TIF surface: MOO / OPG (+
  opening-auction TIF) for Market-On-Open execution (INV-2 / INV-3
  MISSING).

The **Cash → Margin account-type** decision (and the deferred
**Professional-Client** route) are *not* raised as separate OQs —
both are already homed inside OQ-032 (SSOT;
[CONTEXT_PROTOCOL §2.1](../CONTEXT_PROTOCOL.md)) as its Option 1 and
Option 2 respectively. They are surfaced in this audit as the
load-bearing Phase-2-entry operator decisions, not duplicate
questions.

## Recommended next steps

1. ✓ **Save this audit refresh** (this file, v0.2) + the three new
   OQs in KB-11.
2. **Update [`CONTEXT_INVENTORY.md`](../CONTEXT_INVENTORY.md)** §10
   (mark the readiness-audit refresh complete; set session 3 —
   Phase-2 plan-drafting — as front-of-queue) + the banner + the
   KB-11 row (v0.6, 8 OPEN).
3. **Replace [`NEXT_PROMPT.md`](../NEXT_PROMPT.md) v1.5 → v1.6** —
   kickoff for the **Phase-2 plan-drafting session** (session 3):
   operator resolves OQ-032 + OQ-033/034/035 (and reaffirms
   OQ-028/029) with the R-LEV-001 notebook as input; agent then
   drafts the Phase-2 plan in `TASK_REGISTRY.md`.
4. **(Operator-side, before session 3)** on the active retail
   path, the **Cash → Margin** account conversion — it gates the
   leverage-preserving margin-on-1×-UCITS sub-path and has lead
   time. (Professional classification deferred until eligible.)
5. **Re-audit at Phase 2 entry / first M4 freeze** — confirm what
   was true on 2026-06-06 vs what changed.

> **Freeze ceremony note.** The §6.4 M3 freeze is **already done**
> — `docs/_freezes/M3-CONTEXT_INVENTORY.md` exists and the
> `M3-close` git tag is placed (commit `00c9116` / `1758a96`). No
> freeze action remains for this session.

## Cross-References

- [PHASE_1_READINESS](./PHASE_1_READINESS.md) — sibling artefact;
  same eight-dimension shape.
- [RETRO-M3](./retros/M3_retrospective.md) — the load-bearing
  input that informed each dimension's Δ.
- [RETRO-M2-IB](./retros/M2-IB_retrospective.md) — informed v0.1.
- [TASK_REGISTRY](../TASK_REGISTRY.md) — Phase 1 plan + the M4+
  sketch this audit feeds into session 3.
- [CONTEXT_PROTOCOL §8.3.2](../CONTEXT_PROTOCOL.md) — the
  three-session phase-boundary protocol that frames this audit.
- [KB-11 v0.6](./decisions/OPEN_QUESTIONS.md) — open-questions
  catalogue (OQ-032 + OQ-033/034/035).
- [OQ-032](./decisions/OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure) —
  the leverage trilemma; the central Phase-2 decision.
- [ADRs 050–052](./decisions/DECISIONS.md) — the M3 ADR ladder
  (unit-of-quote / tick-grid / OQ-031-Option-1).

## Changelog

- **v0.1 (2026-05-06)** — initial audit at the `M2-IB.6-close`
  gate, *before M3 ran*. Eight dimensions evaluated against the
  M2-IB.6 wire outcomes; five cross-cutting questions raised as
  the agenda for the (then-upcoming) M3 plan-drafting session. No
  new ADRs / OQs raised.
- **v0.2 (2026-06-06)** — **refresh against the real M3 outcomes**
  (G4 PASSED). v0.1's five questions retired (answered by M3;
  table added). Eight dimensions re-audited with a **Δ since v0.1**
  note each, folding in the leverage trilemma (OQ-032), the M3.4
  equity-bug fix, the M3.5 reconnect gap (KB-7 FM-1), the ADR-052
  structural QQL3 non-fill, and the ADR-050/051 unit-of-quote +
  tick-grid fixes. The incoming Phase-2 strategy candidate
  (R-LEV-001 VIX term-structure rotation) folded in; **three new
  OQs raised** (OQ-033 VIX-futures data / OQ-034 universe
  tradability / OQ-035 MOO-OPG order types), all targeting Phase 2
  entry. Six new cross-cutting questions = session 3's agenda.
  **Operator review (2026-06-06)** reframed the leverage question:
  the trilemma is a *retail-Cash* phenomenon. Two routes were
  weighed — **(A) MiFID II Professional Client** (PRIIPs is
  retail-only → trade the US originals; leverage via the 3× ETP) vs
  **(B) retail substitutes** (margin-on-1×-UCITS + a UCITS
  universe) — and the operator confirmed they will **stay retail
  near-term** (not currently elective-professional-eligible), so
  **route B is the active path** and route A is deferred (revisit
  on eligibility). The live OQ-032 sub-decision is then the retail
  leverage lever (margin-on-1×-Nasdaq-UCITS vs de-lever vs
  restructure); **Cash → Margin** is the top operator prerequisite.
  VXX → a mid-term 3-/6-month vol product (design choice);
  VIX-futures data from EODHD (no sfera / parquet). OQ-028/029
  (L0/L1) noted as lowest-stakes (default: reaffirm deferral).
