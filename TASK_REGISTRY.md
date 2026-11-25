---
id: TASK_REGISTRY
title: Task Registry — Phase 1 Plan
status: DRAFT
owner: Oleg primary, Claude assist
last_reviewed: 2026-06-05
version: 0.15
sources:
  - REQUIREMENTS.md §14
  - KB-5 §7
  - ADR-013
  - PHASE_1_READINESS.md
  - PHASE_2_READINESS.md
  - RETRO-M2-IB
depends_on:
  - REQUIREMENTS
  - KB-5
  - PHASE_1_READINESS
  - PHASE_2_READINESS
  - KB-11 (OQ-031 OPEN, OQ-024..OQ-027 RESOLVED-BY-ADR)
referenced_by:
  - CONTEXT_INVENTORY §1 layer 4
---

# TASK_REGISTRY — Phase 1 Plan

## Purpose

Layer-4 Plan artefact (per [CONTEXT_INVENTORY §1](./CONTEXT_INVENTORY.md#1-representation-hierarchy)). Specifies milestones, deliverables, gates, exit criteria, dependencies, and substrate-artefact requirements for **Phase 1 (M0 → M3)** — the path to first IB Paper strategy run.

## Scope

**In scope (this version):** detailed plan for M0, M1, M2, M3.

**Sketched only:** M4+ (Phase 2 entry); detail awaits M3 close.

**Out of scope:** execution itself.

## Phase 1 Strategy

**2026-05-02 amendment**: Per [ADR-043](./docs/decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2), Phase 1 strategy switched from A2 (`tkan_v4_momentum_timing` on `CAC.PA`) to **A3 — `triple_lev_sma_filter_dsl`** (TQQQ / TMF / IEF). Operator-chosen as the first live-trading candidate after M2-IB.4a fully wire-validated the IB write-side end-to-end against IB Paper for single-instrument flow. ADR-021 (CAC ETF proxy as Phase 1) is now SUPERSEDED-BY-ADR-043; the CAC.PA Instrument substrate (DD-7 §3 / §3.1 + ADR-041 Yahoo-suffix translation + the M2-IB.4a-happy-cacpa wire validation) stays durable but no longer holds the Phase 1 strategy designation.

The original ADR-013 selection (`tkan_v4_momentum_timing` 1× variant) is **DEFERRED-NO-TARGET**; the A2 code stays in repo (`blive.runtime.paper_pipeline`, `SingleAssetRunner` dispatch via ADR-030, tests) and revives whenever an A2-style timing strategy returns to scope.

**2026-04-28 amendment**: M2 history:

- **M2-IG path** (operator-driven IG demo bridge while IB Paper was unavailable) — **CLOSED at architectural surface 2026-04-28**. Sub-milestones .1 substrate / .2 cross-cutting infra / .3 read side / .4 minimum-viable submit shipped (7 tags placed; 359 tests; ADR-030/033/034..039 ACCEPTED). Sub-milestone .5 strategy run + production Lightstreamer wrapper DEFERRED (operator pivoted to M2-IB resumption when the IB Paper account became available). See [RETRO-M2-IG](./docs/retros/M2-IG_retrospective.md). The IG-specific code (5 modules + Lightstreamer abstraction + KB-16/17 + DD-8) is preserved in repo for future bridge revival; no scheduled revival.
- **M2-IB path** (canonical Phase 1) — **ACTIVE 2026-04-28**. IB Paper account commissioned 2026-04-28; enabled 2026-04-29. Resumes from the [`M2-substrate-IB.checkpoint`](./docs/decisions/DECISIONS.md) commit. Architecturally scaffolded by the M2-IG cross-cutting work (broker registry, shared rate limiter, shared credentials, `Instrument.tradability` field) — IB read+write modules mirror IG's file structure 1:1 per RETRO-M2-IG §"Recommendations".

Phase 1 specifics (canonical M2-IB.6 path per [ADR-043](./docs/decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2); CAC.PA / A2 path superseded; M2-IG bridge variant ARCHIVED):

| Specifier | M2-IB.6 path (ACTIVE) | M2-IB.5 / CAC.PA path (SUPERSEDED — substrate durable) | Source |
|-----------|------------------------|---------------------------------------------------------|--------|
| Strategy | `triple_lev_sma_filter_dsl` (A3 archetype) | `tkan_v4_momentum_timing` 1× (A2 archetype, DEFERRED-NO-TARGET) | [ADR-043](./docs/decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2) |
| Tradable instruments | TQQQ + TMF + IEF (US ETFs on NASDAQ / NYSE) | `CAC.PA` (Lyxor CAC 40 UCITS ETF, XPAR — wire-validated `M2-IB.4a-happy-cacpa`) | ADR-043 / ADR-021 (SUPERSEDED) |
| Trend signals | QQQ closes (TQQQ filter) + TLT closes (TMF filter); SMA-200 with 5% hysteresis re-entry | TKAN `pred_cache.pkl` ML predictions | ADR-043 / ADR-022 (TKAN, deferred) |
| Universe size | 3 instruments (multi-instrument pipeline per [ADR-044](./docs/decisions/DECISIONS.md#adr-044--multi-instrument-pipeline-support-companion-to-adr-043)) | 1 instrument (single-instrument pipeline per `run_paper_pipeline` / `run_ib_pipeline`) | ADR-044 |
| btest dispatch | `LongShortPortfolio` → `compute_target_weights_for_date()` per [ADR-045](./docs/decisions/DECISIONS.md#adr-045--longshortportfolio-btest-dispatch-extends-adr-030) | `TimingPortfolio` → `SingleAssetRunner` per [ADR-030](./docs/decisions/DECISIONS.md#adr-030--per-archetype-btest-interpreter-dispatch-amends-adr-010) | ADR-045 / ADR-030 |
| Tradability | `spot` (ETF shares; [ADR-027](./docs/decisions/DECISIONS.md#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero) integer-share rounding) | `spot` (ETF shares) | [ADR-037](./docs/decisions/DECISIONS.md#adr-037--instrumenttradability-field-spot--cfd--spread_bet) |
| Routing | SMART with primary-exchange hint per [ADR-046](./docs/decisions/DECISIONS.md#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032) (XNAS → SMART/NASDAQ; XNYS → SMART/NYSE) | Direct-routed to SBF (with API → Precautions bypass) | ADR-046 / ADR-032 |
| NAV slice | 5–10% of total account, hard cap 10% (unchanged) | same | [ADR-020](./docs/decisions/DECISIONS.md#adr-020--phase-1-nav-slice-510-of-total-cap-10) |
| Rebalance | Daily (T+1 open via `signal_delay_bars=1`) — DSL form. v1-style bimonthly is a future operational refinement (operator-noted "smart rebalance"). | Daily close | strategy spec |
| Parity envelope | TBD per [OQ-012](./docs/decisions/OPEN_QUESTIONS.md#oq-012--parity-tolerance-bands-are-8-numbers-right) — leveraged-ETF financing parity per [KB-6 §4](./docs/kb/cost_margin_dictionary.md) becomes load-bearing earlier than under A2 | ±1 bps target (deferred with A2) | ADR-043 |
| Credentials | `~/.blive/secrets/ib.env` (unchanged) | same | [ADR-035](./docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets) |
| Operator-side prereqs | EODHD subscription (active), no IB market-data subscription needed (US ETF historical via EODHD per [ADR-017](./docs/decisions/DECISIONS.md#adr-017--live-data-hybrid-eodhd--ib-streaming-per-instrument-routing) hybrid routing); IB Paper "Read-Only API" unchecked + "Bypass Order Precautions for API Orders" ticked (per `M2-IB.4a-happy-cacpa`) | SBF historical-data subscription was needed for CAC.PA; **no longer needed** (A3 uses US ETFs which IB Paper provides without paid tier for delayed daily) | ADR-043 follow-ups |

---

## Milestone Plan

### M0 — Skeleton & Domain Types

**Goal:** repository structure exists; domain types defined; ports declared; minimal paper broker round-trips an order through the full FSM.

**Deliverables:**

1. **Repo scaffolding** — `pyproject.toml` (Python 3.11, `uv` package manager), `src/blive/`, `tests/`, build shortcuts.
2. **Pinned dependencies** — `btest >=X.Y,<X.Y+1` (TBD on first build), `ib_async >=2.1,<2.2` per [ADR-002](./docs/decisions/DECISIONS.md#adr-002--adopt-ib_async-v21-as-wire-level-ib-driver).
3. **DD-1 domain objects** (`docs/dd/domain_objects.md`, **MISSING → STABLE**) — `Order`, `Fill`, `Position`, `Bar`, `Trade`, `AccountSnapshot`, `Instrument`, `OrderEvent`. Pure dataclasses; frozen where applicable; no business logic.
4. **INV-13 order FSM transitions** (`docs/inv/order_state_transitions.md`, **MISSING → STABLE**) — `INITIALIZED → SUBMIT_PENDING → SUBMITTED → ACCEPTED → (PARTIALLY_FILLED) → FILLED | CANCELED | REJECTED | EXPIRED` with explicit allowed sources, triggers, side-effects per transition.
5. **INV-5 domain events** (`docs/inv/domain_events.md`, **MISSING → DRAFT**) — every event type, payload, emission rule.
6. **INV-6 ports/adapters** (`docs/inv/ports_adapters.md`, **MISSING → DRAFT**) — `BrokerPort`, `MarketDataPort`, `ClockPort`, `PersistencePort`, `EventBusPort`, `AlertPort` as Python `Protocol` classes with concrete signatures from [REQUIREMENTS §7.2](./REQUIREMENTS.md).
7. **PaperBroker adapter** (`src/blive/adapters/paper/`) — in-process matcher honouring the order FSM; configurable simulated latency / fills.
8. **InMemoryPersistence adapter** — append-only event log in memory (development use; SQLite arrives at M4).
9. **Test scaffolding** — pytest config; mock implementations of each port; golden FSM-transition tests.
10. **Import-linter rule** — `blive.domain` cannot import `blive.adapters.*`; enforced via CI or pre-commit hook per [ADR-004](./docs/decisions/DECISIONS.md#adr-004--hexagonal-portsadapters-with-import-linter-enforcement).

**Substrate transitions:** DD-1 STABLE; INV-13 STABLE; INV-5 DRAFT; INV-6 DRAFT.

**Exit criteria (G1 gate):**

- `uv run pytest` green.
- Unit test creates an `Order`, traverses the full FSM, asserts every emitted event has the expected payload.
- PaperBroker round-trip test: submit a market order; receive a `Fill`; observe `Position` updates correctly.
- Import-linter passes against a deliberately violating commit (negative test).

**Estimated effort:** ~1 working session.

**Dependencies:** none (entry milestone).

---

### M1 — btest Strategy Import & Paper Round-Trip

**Goal:** `tkan_v4_momentum_timing` 1× runs in blive's paper mode end-to-end and matches btest's equity curve to within rounding tolerance.

**Deliverables:**

1. **btest dependency** installed and pinned; CI smoke-imports check ensures `from quantdsl_backtest.dsl.strategy import Strategy` and friends work.
2. **Strategy ingest module** (`blive.strategy.loader`) — given a Python module producing a btest `Strategy`, register it with the blive runtime.
3. **FactorEngine / SignalEngine / PortfolioEngine reuse** — imported from btest, wired into the blive runtime per [ADR-010](./docs/decisions/DECISIONS.md#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import).
4. **Sizer (M1 minimal)** (`blive.sizing`) — convert `target_weights: pd.Series[instrument → float]` into concrete `Order` objects per [REQUIREMENTS §5.13](./REQUIREMENTS.md). Single-instrument case suffices for Phase 1; multi-instrument path is Phase 2 work.
5. **RiskEngine (M1 minimal subset)** (`blive.risk`) — implement RC-08 stale data, RC-09 market hours, RC-13 kill-switch from [INV-4](./docs/inv/risk_checks.md). Other RCs land at M4.
6. **Paper-mode end-to-end pipeline:**
   - Load `tkan_v4_momentum_timing` strategy spec.
   - Replay deterministic historical CAC.PA bars (offline, fixture-backed).
   - At each rebalance: factor → signal → portfolio → sizer → risk → paper broker.
   - Record fills, positions, equity curve.
7. **DD-3 config schemas** (`docs/dd/config_schemas.md`, **MISSING → DRAFT**) — strategy YAML schema with field-level validation.

**Substrate transitions:** DD-3 DRAFT; INV-5 DRAFT → STABLE; INV-6 DRAFT → STABLE.

**Exit criteria (G2 gate):**

- `tkan_v4_momentum_timing` 1× runs in blive paper mode for ≥ 252 days of historical CAC.PA data.
- End-of-period equity curve matches btest's reference run **within ±1 bps** (divergence should come only from share-rounding in the sizer; the engines are identical by import).
- Round-trip test: signal → fill → position update → equity reflects the trade including commission per [KB-6 §1](./docs/kb/cost_margin_dictionary.md#1-commission).
- A negative test: deliberately stale data triggers RC-08 block; engine refuses to size; alert event fires.

**Estimated effort:** ~1–2 sessions.

**Dependencies:** M0 complete; G1 gate passed.

---

### M2-IB — IB Adapter (Read + Write Side) & First Live (Paper) Strategy Run — **ACTIVE 2026-04-28**

**Status:** ACTIVE — IB Paper account commissioned 2026-04-28; enabled 2026-04-29. Substrate at [`M2-substrate-IB.checkpoint`](./docs/decisions/DECISIONS.md). Cross-cutting infra (broker registry, shared rate limiter, shared credentials, `Instrument.tradability` field) shipped via the M2-IG bridge work and reuses unchanged. Architecturally scaffolded — implementation now mirrors the M2-IG file structure 1:1 per [RETRO-M2-IG §"Recommendations"](./docs/retros/M2-IG_retrospective.md#recommendations-for-next_promptmd-v04-m2-ib-resumption).

**Goal:** blive runs `tkan_v4_momentum_timing` 1× against `CAC.PA` ETF on IB Paper for ≥ 5 trading days, with end-of-period equity matching btest's reference within ±1 bps (G2-IB) and the operational stack (Docker, IBC, rate limiter, credentials, broker registry) operational.

**Sub-milestones:**

- **M2-IB.1 — Substrate verification.** Confirm the substrate at `M2-substrate-IB.checkpoint` is internally consistent post-M2-IG (most rows are; KB-8 grew §8 IG events; INV-6 grew IG rows + cross-cutting `blive.adapters.shared.*` catalogue). No code in this sub-milestone.
- **M2-IB.2 — IBClient + IBCredentials.** New `blive.adapters.ib.client` wrapping `ib_async.IB` (TCP socket + callback model — different transport from IGClient's REST). connect / disconnect / submit / cancel / event subscription. Rate-limited via `blive.adapters.shared.rate_limiter` with [KB-3 §9](./docs/kb/ib_pacing_spec.md#9-summary-adapter-budget-defaults) IB defaults (20 msg/s global; 5/s per-strategy). New `blive.adapters.ib.credentials` (schema is simpler than IG — no API key, no password; just host/port/clientId/account_id per `secrets/ib.env.example` from ADR-035).
- **M2-IB.3 — IBInstrumentResolver + IBBroker read + IBMarketData.** Mirror M2-IG.3 file structure. IBInstrumentResolver: `Instrument` ↔ IB `Contract` via `qualifyContractsAsync` per [DD-7 §4](./docs/dd/instrument_dictionary.md). IBBroker read: positions / account_snapshot / open_orders / events. IBMarketData: subscribe_bars via `ib_async.reqMktData` / `reqHistoricalData` (no Lightstreamer abstraction — IB has its own stream model; the `MarketDataPort.subscribe_bars` shape stays identical from the consumer's perspective). Wire `create_ib_broker` + `create_ib_market_data` into `broker_registry`. **ADR-031 + ADR-032 flip PROPOSED → ACCEPTED** on first IB exercise. **DD-7 STABLE flip** on first successful Contract resolution. **KB-2 + KB-3 STABLE flip** when M2-IB.3 has exercised the §1-§9 surfaces against IB Paper.
- **M2-IB.4 — IBBroker write side + reconciliation.** submit / cancel / replace via `ib_async` order placement. FSM event emission driven by `ib_async`'s `orderStatusEvent` / `execDetailsEvent` / `commissionReportEvent` callbacks (event-driven, unlike IG's confirms-poll). Reconciliation on startup: `reqAllOpenOrders` + `reqPositions` per [REQUIREMENTS §5.7](./REQUIREMENTS.md#57-reconciliation). **INV-14** (IB error codes) MISSING → DRAFT as observed-rejects accumulate. Optionally consolidate with the original M3 plan; see "M2-IB.4 vs M3" note below.
- **M2-IB.5 — Strategy run + RETRO-M2-IB.** Pipeline (refactor `paper_pipeline.py` to be broker-agnostic via `broker_registry`, OR new `ib_pipeline.py` analogue of the deferred M2-IG.5 plan). Run `tkan_v4_momentum_timing` 1× against IB Paper for ≥ 5 trading days. G3-IB gate criteria validated. Write `RETRO-M2-IB.md` per [CONTEXT_PROTOCOL §8.3.1](./CONTEXT_PROTOCOL.md).

**M2-IB.4 vs M3 note**: the original M3 milestone (per TASK_REGISTRY v0.1.x) was "IB Adapter (Write Side) & First Live (Paper) Strategy". With the M2-IG bridge having shipped MARKET-submit at M2-IG.4 + the multi-broker registry pattern in place, the cleanest plan is to consolidate write side into M2-IB.4 and let M2-IB.5 be the strategy run. M3 in the v0.3 sketch becomes Phase 2 entry / second strategy slot rather than "IB write side". Re-evaluate at M2-IB.3 close.

**Goal (read-side, restated from earlier scope):** blive connects to IB Paper, reads positions / account values / market data; the operational stack (Docker, IBC, rate limiter) is in place.

**Deliverables:**

1. **IB Paper account verified** (operator action) — credentials available; `clientId` chosen; documented in a private `secrets/` location not under version control.
2. **IB Gateway via Docker** (e.g. `gnzsnz/ib-gateway-docker`) operational — auto-restart on failure; pinned offline TWS installer per [KB-3 §5](./docs/kb/ib_pacing_spec.md#5-daily-and-weekly-operational-events); IBC configured.
3. **EODHD subscription verified** — CAC index daily history reachable via `eodhd://` test fetch.
4. **`IBBroker` adapter — read methods** (`adapters/ib/broker.py`) — `connect()`, `disconnect()`, `positions()`, `account_snapshot()`, `open_orders()`, `events()`. All outbound calls pass through a token-bucket rate limiter (default 20 msg/sec global per [KB-3 §1](./docs/kb/ib_pacing_spec.md#1-the-50-msgsec-client-throttle)).
5. **`IBMarketData` adapter — read methods** (`adapters/ib/market_data.py`) — `subscribe_bars()`, `historical_bars()`. Historical pacing per [KB-3 §2](./docs/kb/ib_pacing_spec.md#2-historical-data-pacing).
6. **`EODHDDataSource`** registered in btest's data source registry (`adapters/eodhd/`) — `eodhd://...` URL scheme resolves to delayed/historical fetch.
7. **`scripts/refresh_artefact.py`** (per [OQ-027](./docs/decisions/OPEN_QUESTIONS.md#oq-027--tkan-artefact-prod-location-and-retraining-ownership)) — copy + checksum + record TKAN artefact freshness.
8. **PaperBroker → real-IB-Paper read-mirror harness** — blive runs with PaperBroker for execution but reads positions via IBBroker; the two views match.
9. **Reconnect logic** — disconnect / reconnect cycles tested by stopping/starting the IB Gateway container.

**Substrate transitions:** KB-2, KB-3 STABLE confirmed; INV-14 (IB error codes) MISSING → DRAFT; KB-8 (operational events) MISSING → DRAFT.

**Exit criteria (G3 gate):**

- blive connects to IB Paper Gateway within 5 s of process start.
- `positions()` returns the same set TWS UI shows (manual eyeball check).
- Subscribe to CAC.PA bars; receive ≥ 100 ticks within RTH.
- Throttle test: simulate burst of 60 calls/sec; outbound rate stays ≤ 20 msg/sec.
- Disconnect IB Gateway mid-session; blive detects within 30 s; reconnects when Gateway returns.
- `refresh_artefact.py` round-trip: copy a fresh `pred_cache.pkl` from btest output; observe checksum recorded; observe RC-12 freshness check passes.

**Estimated effort:** ~2–3 sessions, dominated by Docker / IBC setup time and IB Paper account commissioning. **Operator-side prerequisites must be verified before M2 starts.**

**Dependencies:** M1 complete; G2 gate passed; OQ-024..OQ-027 confirmed.

---

### M2-IG — IG Demo Bridge — **ARCHIVED 2026-04-28** (architectural-surface close; G3-IG NOT_REACHED)

**Status:** **CLOSED at architectural surface 2026-04-28** per [RETRO-M2-IG](./docs/retros/M2-IG_retrospective.md). The G3-IG gate criteria were NOT REACHED — this was an operator-driven close after the IB Paper account became available, not a gate failure. The M2-IG sub-milestones .1 (substrate) / .2 (cross-cutting infra) / .3 (read side) / .4 (minimum-viable submit) shipped at architectural surface (7 tags placed: `M2-IG.1-batch1`, `M2-IG.1-batch2`, `M2-IG.2-complete`, `M2-IG.3-broker`, `M2-IG.3-readside-complete`, `M2-IG.4-market-submit`); **never exercised against IG demo**. M2-IG.5 (strategy run + 5-day demo) and the production Lightstreamer wrapper are explicitly **DEFERRED with no scheduled revival**.

The IG-specific code (modules under `blive/adapters/ig/`, KB-16, KB-17, DD-8, ADR-036/038/039) is preserved as durable reference. If the bridge is ever revived, the work is reusable. The cross-cutting work — broker registry, shared rate limiter, shared credentials, `Instrument.tradability` field — applies directly to M2-IB resumption (this was the bridge's primary architectural dividend, captured in RETRO-M2-IG §"What the IG bridge bought us").

**Original goal (not achieved):** blive runs `tkan_v4_momentum_timing` 1× against CAC 40 CFD on IG demo for ≥ 5 trading days.

**Why M2-IG was bigger than M2-IB scope-wise**: M2-IG covered read + write + strategy run as a single unit because the bridge's primary purpose was end-to-end validation of the abstraction. The M2-IB resumption splits that: read side (M2-IB.3) + write side (M2-IB.4) + strategy run (M2-IB.5).

**Sub-milestones:**

- **M2-IG.1 — Substrate phase.** Cross-cutting ADRs (ADR-034 multi-broker registry, ADR-035 secrets) shipped 2026-04-27 batch 1. IG-specific ADRs (ADR-036 IG driver, ADR-037 `Instrument.tradability`, ADR-038 IG rate-limit defaults, ADR-039 Phase 1 strategy under bridge) + KB-16 (IG capability matrix), KB-17 (IG pacing spec), DD-8 (IG instrument dictionary), plus DD-3/DD-1/INV-6/KB-8 amendments — batch 2.
- **M2-IG.2 — Cross-cutting infra.** `blive.adapters.shared.rate_limiter` (token bucket per [ADR-031](./docs/decisions/DECISIONS.md#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters), per-broker config), `blive.adapters.shared.credentials` (env-var loader per ADR-035), `blive.runtime.broker_registry` (factory dispatch per ADR-034). `secrets/ig.env.example` committed; `.gitignore` rule for `secrets/*.env`. Updated import-linter contract for broker-registry isolation.
- **M2-IG.3 — IG read-side adapter.** `blive.adapters.ig.broker.IGBroker` (read methods); `blive.adapters.ig.market_data.IGMarketData` (Lightstreamer + REST historical); `blive.adapters.ig.instrument_resolver` (Instrument↔epic); `blive.adapters.ig.credentials` (IG schema). 3-step REST auth flow.
- **M2-IG.4 — IG write-side adapter.** `IGBroker.submit / cancel / replace` against `/positions/otc` + `/workingorders/otc`; FSM driven by IG's order-status callbacks (Lightstreamer trade subscription); reconciliation on startup.
- **M2-IG.5 — Strategy run + retro.** Lift `paper_pipeline.py` to IG (broker registry pluggable). Run `tkan_v4_momentum_timing` 1× against the CAC 40 CFD epic on IG demo for ≥ 5 trading days. Verify directional alignment + envelope per ADR-039. Write [`docs/retros/M2-IG_retrospective.md`](./docs/retros/M2-IG_retrospective.md) per [CONTEXT_PROTOCOL §8.3.1](./CONTEXT_PROTOCOL.md). G3-IG gate report.

**Substrate transitions at M2-IG close:**

- ADR-030..033 status reviewed: broker-agnostic ones (ADR-030, ADR-033) flip PROPOSED → ACCEPTED; IB-specific ones (ADR-031, ADR-032) stay PROPOSED until M2-IB resumes.
- ADR-034 (multi-broker registry), ADR-035 (secrets), ADR-036..039 (IG-specific) flip PROPOSED → ACCEPTED.
- DD-7 stays IB-specific DRAFT (parked); DD-8 (IG instrument dictionary) DRAFT → STABLE on first successful epic resolution against IG demo.
- KB-16, KB-17 DRAFT; STABLE confirmed at M2-IG close via the IG read-side exercise.
- INV-14 (IB error codes) stays MISSING; equivalent IG error-code inventory authored as the M2-IG.3 work observes IG rejects.
- INV-5 widens with `AccountUpdate` (M2-IG.3) and `ArtefactFreshnessWarning` (M2-IG.3) — both already catalogued in [INV-5 §1](./docs/inv/domain_events.md), now implemented.

**Exit criteria (G3-IG gate):**

- blive connects to IG demo within 5 s of process start.
- `positions()` returns the same set IG web UI shows (manual eyeball check).
- Subscribe to CAC 40 CFD prices via Lightstreamer; receive ≥ 100 ticks within market hours.
- Throttle test: simulate burst of 100 calls/min; outbound rate stays ≤ 60 calls/min (per ADR-038).
- IG session-token expiry test (6 h on demo): observe automatic re-authentication; engine continues running.
- `refresh_artefact.py` round-trip works against the IG-bridge strategy run (broker-agnostic — same script as M2-IB).
- `tkan_v4_momentum_timing` 1× runs end-to-end on IG demo for **≥ 5 trading days without manual intervention**.
- ≥ 5 round-trip orders observed end-to-end against IG demo; FSM transitions logged.
- Strategy equity curve directionally aligned with btest replay; envelope per ADR-039 honoured.

**Operator-side prerequisites for M2-IG:**

- IG demo account commissioned ✓ (operator confirmed 2026-04-27 with API key, username, password, account id; paper-only test account; rotation discipline per ADR-035 understood).
- Deployment target — Linux VM vs Windows host. **Still OPEN**; less critical than for M2-IB since IG has no daily-restart equivalent and runs entirely over HTTPS (no TWS / IBC dependency). May be deferred to M2-IG.5 deployment.

**Estimated effort:** ~5–6 sessions across M2-IG.1 to M2-IG.5.

**Dependencies:** M1 complete; G2 gate PARTIAL accepted (synthetic-fixture parity green at M1 close).

---

### M2-IB.6 — A3 strategy paper-test on IB Paper (`triple_lev_sma_filter_dsl`) — **CLOSED 2026-05-06**

**Status:** CLOSED at the M2-IB.6.2c LSE-RTH validation. First IB-paper FILL on M2-IB.6 landed on `IBTM` (1 fill, 19 shares × £128.5) at 09:33 BST. ADR-048 flipped PROPOSED → ACCEPTED (LSE-ETF SMART discriminator wire-validated end-to-end). ADR-049 (`OrderType.ADAPTIVE_MKT` + empirical PMA-cap finding) ACCEPTED same-session. The `OrderType.ADAPTIVE_MKT` infrastructure landed and was tested; the IBALGO-bypasses-2161 hypothesis (per IB's own warning text) was empirically refuted across a 4-run wire matrix on QQL3 (raw MKT 10s + 60s waits, ADAPTIVE_MKT, LMT @ $50). The PMA cap on UK retail leveraged ETPs is structural — captured in [INV-14 v0.7](./docs/inv/ib_error_codes.md), [OQ-031](./docs/decisions/OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account), and the M2-IB retro. Operator decided at close to address OQ-031 in **M3** rather than block M2-IB.6 on it — the architectural surface is fully validated, the operational fill-rate question lives downstream.

**Goal:** blive runs `triple_lev_sma_filter_dsl` (A3) end-to-end against IB Paper across the **current Phase 1 universe** (tradables: `QQL3` / `IBTL` / `IBTM`; signal-only: `QQQ` / `TLT` from EODHD), exercising the multi-instrument FSM (FILLED + PARTIAL_FILL paths), with the A3 LongShortPortfolio btest dispatch lit up for the first time. Outcome is operationally clean (no rejections, no breaches; FILLED count matches expected regime-flip count).

**Sub-milestones:**

- ~~**M2-IB.6-substrate**~~ ✓ Complete 2026-05-02. ADRs 043 / 044 / 045 / 046 ACCEPTED + KB-5 §7 / INV-1 / DD-7 §3 amendments.
- ~~**M2-IB.6.1 — multi-instrument pipeline + 5-ticker EODHD refresh + LongShortPortfolio dispatch.**~~ ✓ Complete across 2026-05-02 → 2026-05-04. `run_m2ib6_ib_paper.py`, the 5-ticker refresh flow, LongShortPortfolio dispatch, and resolver support all landed. Two empirical findings then tightened the scope: [ADR-047](./docs/decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043) swapped the tradable universe to PRIIPs-compliant UK-listed analogues, and ADR-048 PROPOSED captured the LSE-ETF routing discriminator (`XLON + ETF → SMART/LSEETF`) after bare `LSE` surfaced IB error 200.
- ~~**M2-IB.6.2a — US-RTH PRIIPs validation probe.**~~ ✓ Complete 2026-05-04. `scripts/probe_tqqq_us_rth.py` rerun during US RTH returned the full 201 / KID text, validating ADR-047 empirically and proving the blocker is regulatory rather than market-time artefact. The broker-side `ib.errorEvent` stash fix shipped at head `abebc5a`.
- ~~**M2-IB.6.2b — LSE-RTH filled validation.**~~ ✓ Complete 2026-05-06 (Wed) at 09:33 BST. First IB-paper FILL landed on `IBTM` (1 fill, 19 shares × £128.5) via the ADR-048 SMART/LSEETF routing — no error 200 regression, no PRIIPs surfaces under the substituted universe. `QQL3` placeOrders all reached SUBMITTED but tripped IB warning **2161** (Price Management Algo regulatory disruptive-orders cap), surfacing a structural fill-quality concern on the leveraged equity leg. `IBTL` had no eligibility-driven placeOrders in the smoke window.
- ~~**M2-IB.6.2c — IB warning 2161 PMA-cap investigation.**~~ ✓ Complete 2026-05-06. Four-run wire matrix on QQL3 (raw MKT 10s + 60s waits → ADAPTIVE_MKT → LMT @ $50) empirically confirmed the cap binds STRUCTURALLY on UK retail accounts regardless of order type. Added `OrderType.ADAPTIVE_MKT` (IBALGO Adaptive variant) — ACCEPTED as ADR-049, kept as catalogue infrastructure for non-cap-bound venues / future strategies even though it does not bypass the cap on UK retail. INV-14 v0.7 documents the validation matrix; OQ-031 raised for pre-cutover resolution.
- ~~**M2-IB.6-close**~~ ✓ Complete 2026-05-06. ADR-048 + ADR-049 flipped PROPOSED → ACCEPTED in a single batch; DD-7 §3 amended (XLON split by `asset_class`); `RETRO-M2-IB.md` written + frozen; successor `NEXT_PROMPT.md` v0.7 → v0.8 targeting Phase 2 readiness audit per [CONTEXT_PROTOCOL §8.3.2](./CONTEXT_PROTOCOL.md). Tag `M2-IB.6-close` pushed.

**Deliverables:**

1. ~~**ADRs 043 / 044 / 045 / 046 ACCEPTED**~~ ✓ Complete. Substrate amendments to KB-5 §7, INV-1, DD-7 §3. **(M2-IB.6-substrate)**
2. ~~**Multi-instrument `run_ib_pipeline` support**~~ ✓ Complete. `IBRunResult` widened to per-instrument shape; synthetic multi-instrument tests landed. **(M2-IB.6.1)**
3. ~~**EODHD 5-ticker refresh**~~ ✓ Complete. Refresh flow now produces the current 5-file + wide-signal bundle. Tradable tickers were later revised from `TQQQ` / `TMF` / `IEF` to `QQL3` / `IBTL` / `IBTM` per ADR-047; signal-only `QQQ` / `TLT` remain unchanged. **(M2-IB.6.1)**
4. ~~**LongShortPortfolio btest dispatch wired**~~ ✓ Complete. Pipeline detects `LongShortPortfolio` and routes through `compute_target_weights_for_date()`. **(M2-IB.6.1)**
5. ~~**`IBInstrumentResolver` SMART convention codified**~~ ✓ Complete. US-equity SMART routing (ADR-046) committed; LSE-ETF SMART routing (`XLON + ETF → SMART/primaryExchange=LSEETF`) committed at `c34267d` and ADR-048 ACCEPTED at M2-IB.6 close. **(M2-IB.6.1 / .6.2)**
6. ~~**`scripts/run_m2ib6_ib_paper.py`**~~ ✓ Complete. Driver landed; per-symbol `order_type_by_symbol` override added at .6.2c. **(M2-IB.6.1 / .6.2)**
7. ~~**LSE-RTH wire run**~~ ✓ Complete 2026-05-06. First IB-paper FILL on M2-IB.6 (IBTM, 19 × £128.5). QQL3 surfaced structural PMA-cap finding → catalogued + raised OQ-031 + raised ADR-049. **(M2-IB.6.2b/c)**
8. ~~**`RETRO-M2-IB.md`**~~ ✓ Complete 2026-05-06. Frozen retrospective covering M2-IB.1 → M2-IB.6 ladder, including the PRIIPs / PMA-cap / LSEETF substrate findings. **(M2-IB.6-close)**
9. ~~**Successor `NEXT_PROMPT.md`**~~ ✓ Complete 2026-05-06. Replaced v0.7 → v0.8 targeting Phase 2 readiness audit (separate session per CONTEXT_PROTOCOL §8.3.2). **(M2-IB.6-close)**

**Substrate transitions:** ADR-021 ACCEPTED → SUPERSEDED-BY-ADR-043. ADRs 043 / 044 / 045 / 046 / 047 / 048 / 049 ACCEPTED. INV-1 v0.1 → v0.3 (A2 / A3 phase columns swapped, then universe column updated to PRIIPs-compliant LSE-listed analogues per ADR-047). KB-9 v0.1 → v0.2 (PRIIPs / KID §5.5 added). INV-14 v0.5 → v0.7 (broker-side reason-extraction taxonomy for `Inactive` / PRIIPs rejections at v0.6; warning 2161 PMA-cap catalogued with the four-run validation matrix at v0.7). DD-7 v1.1 → v1.3 (XLON row split by `asset_class` per ADR-048; LSE-ETF SMART discriminator). KB-10 v0.16 → v0.19 (ADRs 047 / 048 / 049 added across three commits). OPEN_QUESTIONS v0.3 → v0.4 (OQ-031 raised). KB-2 / KB-3 STABLE flip stays pending for M3 close as a follow-up.

**Exit criteria (G3-IB-A3 gate — supersedes G3-IB):**

1. blive connects to IB Paper Gateway within 5s (already validated; should not regress).
2. SMART-routed orders for `QQL3` / `IBTL` / `IBTM` reach ACCEPTED on the wire with the ADR-048 shape (`SMART` + `primaryExchange="LSEETF"`), with no regression to error 200 or the earlier direct-routing precaution path.
3. At least one BUY-then-SELL round trip per regime flip exercises FILLED — the previously-unexercised wire path. Target: ≥ 2 round trips total across the run window.
4. Multi-instrument target_weights_series correctly drives per-instrument orders; no cross-instrument confusion.
5. RiskEngine clean — zero breaches across the run.
6. INV-14 grows with any newly observed LSEETF / UK-retail codes if they surface (the current expectation is that the existing catalogue already covers the likely paths: 200 / 201 / 399).
7. `RETRO-M2-IB.md` written per [`docs/retros/_template.md`](./docs/retros/_template.md).

**Estimated remaining effort:** none — milestone closed.

**Dependencies:** M2-IB.4a-happy-cacpa complete (✓); M2-IB.5 architectural-surface validated (✓); ADR-047 empirically validated (✓, 2026-05-04); broker `ib.errorEvent` fix at `abebc5a` (✓); LSE-RTH wire run at `09829f3` (✓ — first IB-paper FILL); ADR-048 + ADR-049 ACCEPTED at close (✓).

---

### M3 — Phase 1 Deployment Decision — DRAFT

**Status:** DRAFT — entered post-`M2-IB.6-close` (2026-05-06). Plan-drafted in the [CONTEXT_PROTOCOL §8.3.2](./CONTEXT_PROTOCOL.md) third session of the M2 → Phase 2 transition. **Re-scoped from the legacy "M3 — IB Adapter (Write Side)" framing**, which was consolidated into M2-IB.4 / M2-IB.6 already.

**Goal:** Resolve [OQ-031](./docs/decisions/OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account) on observed paper-mode fill-rate evidence rather than principle, fix the EODHD-vs-IB unit-of-quote reconciliation that contaminates the empirical signal, exercise the mixed-currency P&L surface live, extend [INV-14](./docs/inv/ib_error_codes.md) + author KB-7 / INV-8 / INV-9 / KB-15 stub-DRAFTs from observed M3 behaviour, and flip KB-2 / KB-3 to STABLE. Exit posture is Phase 2 entry: a deployment-mode chosen for live cutover, a parity envelope re-derivable from the substituted universe, and Phase-2-prerequisite stub artefacts in place at the level the §8.3.2 G4 gate requires.

**Five plan-drafting calls (2026-05-06)** — recorded inline so the plan's *why* survives:

1. **OQ-031 sequencing → inform-then-resolve.** M3 runs the empirical window first; OQ-031 resolves at M3.3 based on observed fill-rate, *then* becomes the precondition for live cutover at G4. Falsifiable-from-entry per [RETRO-M2-IB §"Recommendations for the discipline"](./docs/retros/M2-IB_retrospective.md) #2.
2. **Empirical fill-rate window → 10 trading days, calendar-bound.** RETRO upper bound; covers ≥ 1 likely regime change; M3 has a definite end-date. Quality check: regime-flat windows annotate the OQ-031 decision rather than wait unbounded. **→ corrected by plan-call #6 (2026-06-05): the "calendar days" unit assumed daemon semantics; the driver is a replay tool, so this was re-scoped to bounded deterministic capture.**
3. **EODHD-vs-IB unit-of-quote → pull forward to M3 (narrow scope).** The 10× sizing bug confounds M3.2's empirical data; OQ-031's decision rests on cap-binding behaviour which depends on order size relative to depth. Narrow scope: unit-of-quote / reverse-split reconciliation only — full M7 parity diagnostic stays in M7.
4. **Strategy-slot scope → A3-only through M3.** M3 is reframed as Phase 1 deployment-decision milestone, not strategy-comparison. A1 / A1a stay as Phase 2 / M4 entrants per Sketched M4+.
5. **Phase 2 substrate prerequisites → M3 ships stub-DRAFTs only of what M3 itself produces.** KB-7 (chaos-drill catalogue from M3.5 only), INV-8 (M3.2 fill-rate / cap-binding / regime-flip metrics only), INV-9 (M3.2 kill-switch alerts only), KB-15 (M3.1 unit-of-quote section only). DD-4 stays MISSING (M4 territory). RC-01..RC-07 + RC-11 implementation stays M4. RC-10 (price sanity) lands in M3.1 as the code-side capture of #3.

**Plan-call #6 (2026-06-05 / M3.2 re-scope — bounded deterministic capture).** Operator call after M3.2's results-capture code landed. The "10 calendar trading days" unit (call #2) was mis-specified: `scripts/run_m2ib6_ib_paper.py` is a **historical-replay** driver, **not** the M5 live daemon (the daemon is explicitly out of M3.2 scope). Two consequences the calendar-bound framing missed: (a) **regime variety comes from the replay window** (`--max-bars` over the signal's history), so it is *deterministic and offline-verifiable* (`--dry-run`) — not something to wait 10 calendar days for (empirically `--max-bars 60` already spans 2 equity-leg flips); (b) **QQL3's fill-rate under the 2161 PMA cap is already established as structural** (≈ 0) by the M2-IB.6.2c 4-run matrix + the M3.1b validation, so 10 days of live runs would mostly re-confirm a known result, and would be partly moot if M3.3 picks OQ-031 Option 3 (drop the leveraged leg). **Decision:** M3.2 closes on a *bounded* set of capture rows — ≥ 1 RTH run over a `--max-bars` window spanning a regime flip, showing QQL3 fill-rate ≈ 0 + IBTL / IBTM fills > 0 — rather than a 10-calendar-day campaign. This makes M3.2 closeable in 1–2 RTH sessions and lets M3.3 framing proceed in parallel. Not an ADR (a plan refinement, consistent with calls #1–#5); recorded inline. G4 exit-criterion #3 amended to match.

**Sub-milestones:**

- **M3.1 — EODHD-vs-IB unit-of-quote reconciliation.** ✓ **Implementation landed 2026-05-06; ADR-050 PROPOSED, awaiting wire-validation flip.** Operator chose **Hybrid B-now / A-later** with the future A-route (live IB MD reference) **bounded to free IB MD tiers only** (paid LSEETF subscription out of scope indefinitely). Investigation: `scripts/probe_qql3_unit_of_quote.py` ran 2026-05-06 against EODHD; refuted H1 (close == adjusted_close ratio 1.0) + H2 (CurrencyCode = USD); operative cause is EODHD-side recent reverse-split lag. Implementation: `src/blive/adapters/eodhd/conventions.py` (per-IB-symbol catalogue; QQL3 → MANUAL_SCALE divisor=10 against IB live reference); `run_ib_multi_pipeline._price_lookup` + `_ib_order_from_desired` route through the catalogue; `mark_prices` is now IB-equivalent. RC-10 (price sanity, ±50% threshold for leveraged-ETP volatility) lands in `blive.risk.checks` per [INV-4 v0.2](./docs/inv/risk_checks.md). Substrate: ADR-050 PROPOSED added (DECISIONS v0.19 → v0.20); KB-15 `parity_methodology` MISSING → DRAFT v0.1 (stub-DRAFT, unit-of-quote / reverse-split section only — full M7 envelope deferred); INV-4 v0.1 → v0.2 (RC-10 promoted from DRAFT-only to implemented; threshold ±20% → ±50%); INV-14 v0.7 → v0.8 (error 110 promoted from v0.7 side-finding to catalogue row); DD-7 v1.4 footnote on the EODHD-vs-IB convention layer (Instrument stays vendor-neutral; conversion at pipeline boundary). Tests: 519 → 541 (8 conventions + 8 RC-10 + 1 pipeline integration). Operator-deferred: central-config sub-milestone (current dict-literal scales; YAML-driven catalogue forward-listed in [Sketched M4+](#sketched-m4-post-phase-1) for promotion when surface ≥3-5 entries). Pending exit: wire-validation smoke (`scripts/run_m2ib6_ib_paper.py --max-bars 5` during LSE RTH); on success ADR-050 PROPOSED → ACCEPTED in a header-only edit per the M2-IB pattern. **Update 2026-06-05: the wire run confirmed the sizing/magnitude fix but surfaced a second error-110 cause (tick size) — see M3.1b; the ADR-050 flip is now joint with ADR-051.**

- **M3.1b — IB order-price tick-grid normalization (ADR-051).** ✓ **Implemented 2026-06-05; ADR-051 PROPOSED; all gates green.** The 2026-06-05 wire-validation run (`--order-type LMT --max-bars 5`, LSE RTH) **confirmed M3.1's unit-of-quote fix on the wire** (QQL3 sized 65 sh @ ~$39 vs the pre-fix 6 @ ~$381) but surfaced a *second, independent* cause of IB error 110: **tick-size non-conformance** (QQL3's LSEETF minimum price variation is 0.10; the pipeline rounded limits to `quantize(0.01)`, so 38.52 / 42.83 / 44.15 were rejected while 39.60 / 41.50 passed). Fix per [ADR-051](./docs/decisions/DECISIONS.md#adr-051--normalize-ib-order-prices-to-the-contract-tick-grid-at-submit-time): snap priced fields to the contract grid at the `IBBroker.submit` chokepoint — pure `blive.adapters.shared.price_grid.snap_price` + an IB market-rule source/cache (`blive.adapters.ib.price_rules.IBPriceRuleService`; `reqContractDetailsAsync` / `reqMarketRuleAsync` with `minTick` fallback; per-`Instrument` cache + `clear_cache`); the pipeline's `quantize(0.01)` removed. Magnitude (ADR-050, sizing-time) vs grid (ADR-051, submit-time) are distinct layers **by design**; size/lot conformance noted as the same-seam forward-extension (not built — YAGNI). Substrate this batch: ADR-051 PROPOSED (DECISIONS v0.20 → v0.21); INV-14 v0.8 → v0.9 (error 110 two sub-causes); DD-7 v1.3/v1.4 → v1.5 (tick-grid metadata footnote + frontmatter correction); CONTEXT_INVENTORY v0.14 → v0.15. Tests 541 → 568 (13 `price_grid` + 7 `price_rules` + 5 `broker_tick_grid`); mypy `src` / black / isort / lint-imports all green (+ 2 incidental pre-existing `ig/instrument_resolver.py` mypy fixes from env-drift). **✓ Exit met 2026-06-05: ADR-050 + ADR-051 flipped PROPOSED → ACCEPTED jointly** on the clean LSE-RTH `--order-type LMT --max-bars 5` run — QQL3 snapped to its 0.10 grid on the live wire and placed with **zero IB error 110** (6 submitted, 0 rejected, IBTM filled; the 5 QQL3 cancels are the structural 2161 PMA-cap / resting-LMT behaviour per OQ-031, not a tick issue). **M3.1 + M3.1b CLOSED; next active path: M3.2 — 10 LSE-RTH-day empirical window.** Operational notes: SAC-blocked `uv run` worked around by invoking the venv Python directly; IB paper account funded with USD via a GBP→USD FX conversion (cleared the prior insufficient-funds blocker on the USD-denominated QQL3 leg).

- **M3.2 — Empirical paper-mode window (bounded deterministic capture; re-scoped 2026-06-05 from "10 calendar trading days" — see plan-call #6 below).** Run `scripts/run_m2ib6_ib_paper.py` against the QQL3 / IBTL / IBTM universe, with EODHD signal refresh + LongShortPortfolio dispatch + ADR-048 SMART/LSEETF routing + per-symbol `order_type_by_symbol` override unchanged. Capture per run: per-instrument fill-rate, regime-flip count (equity-leg long/flat transitions over the replay window), warning-2161 cap-binding events, RiskEngine breach count, FSM-trace coverage (SUBMITTED → ACCEPTED → FILLED / CANCELED / REJECTED ratio). Substrate: INV-8 `metrics` MISSING → DRAFT v0.1 (M3.2 metrics catalogued — full Prometheus stack at M7); INV-9 `alerts` MISSING → DRAFT v0.1 (M3.2 alerts catalogued — full alerting at M7). Exit: data file ready for M3.3 decision. **Status 2026-06-05 — results-capture code + INV-8/INV-9 DRAFT v0.1 landed.** The per-run results sink ([`src/blive/runtime/m3_2_record.py`](./src/blive/runtime/m3_2_record.py) → one JSON row per run under `~/.blive/data/m3_2_window/runs.jsonl`) is wired into [`scripts/run_m2ib6_ib_paper.py`](./scripts/run_m2ib6_ib_paper.py) (`--record-path` / `--no-record` / `--note`); the capture surface is additive (no FSM-behaviour change): `IBMultiRunResult` gained `accepted_count` / `submitted_by_symbol` / `observed_error_codes` (+ `cap_binding_2161_count`), `_drain_order_lifecycle` reports `reached_accepted`, `IBBroker.observed_error_codes` tallies order-related codes (the warning-2161 PMA-cap signal), and `blive.runtime.signals.equity_leg_regime_flips` computes the regime-flip metric. Tests 568 → 590; mypy `src` / black / isort / lint-imports all green; no new ADRs / OQs (the sink shape is a refinement per [NEXT_PROMPT](./NEXT_PROMPT.md)). The driver also gained `--dry-run` (offline regime-coverage preview, no IB) so the replay window can be sized deterministically. **Re-scoped 2026-06-05 (operator call) — bounded deterministic capture (plan-call #6 below).** The original "10 calendar trading days" unit was mis-specified: the driver is a *historical-replay* tool, not the M5 live daemon, so regime variety comes from the **replay window** (`--max-bars`) deterministically — not from waiting for calendar flips — and QQL3's fill-rate is already shown structural (≈ 0) by M2-IB.6.2c / M3.1b. M3.2 now closes on a small, definite set of capture rows. **Remaining (operator-driven):** (1) pick a `--max-bars` window spanning ≥ 1 equity-leg regime flip — offline-verifiable via `--dry-run` (empirically `--max-bars 60` → 2 flips over 2026-02-11 → 05-08; `--max-bars 5` → 0, regime-flat); (2) during LSE RTH run the capture (`--order-type LMT --max-bars 60`; lower `--event-wait-seconds` to keep the session bounded), appending the row to `~/.blive/data/m3_2_window/runs.jsonl`; optionally add a regime-flat datapoint with `--note`. **Close criterion:** `runs.jsonl` holds ≥ 1 run spanning a regime flip, with QQL3 fill-rate ≈ 0 (structural cap confirmed) + IBTL / IBTM fills > 0. **✓ MET 2026-06-05 — M3.2 data deliverable complete.** Two flip-spanning LSE-RTH paper captures landed in `~/.blive/data/m3_2_window/runs.jsonl`: `max-bars 40` (2 flips; 28 submitted = QQL3 25 / IBTM 3; 3 filled, all IBTM) and `max-bars 60` (2 flips; 47 submitted = QQL3 44 / IBTM 3; 3 filled, all IBTM). **Aggregate: QQL3 0 / 69 fills (0%), IBTM 6 / 6 (100%); 2161 cap-binding count 0; zero rejects, zero breaches, no error 110.** Empirical OQ-031 signal: the leveraged equity leg does not fill (now on correctly-sized, on-grid orders), the Treasury leg fills cleanly — and notably, under ADAPTIVE_MKT the *visible* 2161 cap did not fire (`mktCapPrice` 0.0); the non-fill is the load-bearing fact regardless of mechanism (contrast the raw-MKT M2-IB.6.2c runs where 2161 fired). `scripts/flatten_ib_paper.py` added to reset the paper account between campaigns (the replay driver accumulates Treasury fills from its fresh-per-run local view; used 2026-06-05 to flatten IBTM 230 → 0). **M3.3 (OQ-031 resolution) consumes this dataset.**

- **M3.3 — OQ-031 resolution.** Operator-led decision over the four OQ-031 options based on M3.2 evidence. New ADR (next free index after 049) records the chosen Option, with supersedes / amends chain as applicable. OQ-031 flips OPEN → RESOLVED-BY-ADR-NNN. Branch handling: Option 3 (substitute non-leveraged equity leg) amends [ADR-043](./docs/decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2) + universe re-validation half-session; Options 1 / 2 / 4 keep the strategy as-is, the chosen option is the deployment-mode commitment for G4. **✓ RESOLVED 2026-06-05 (M3.3) — Option 1.** Operator chose Option 1 (accept the PMA-bound leveraged-leg non-fill as a Phase-1 deployment characteristic; no code change — live behaviour Treasury-leg-dominated) on the M3.2 evidence (QQL3 0/69 fills = 0% vs IBTM 6/6 = 100%; 2161 cap-binding 0; zero rejects / breaches / error-110 across two flip-spanning LSE-RTH runs). Recorded as [ADR-052](./docs/decisions/DECISIONS.md#adr-052--phase-1-accepts-the-pma-bound-leveraged-leg-non-fill-oq-031-option-1); OQ-031 OPEN → RESOLVED-BY-ADR-052. The leveraged-leg redesign is **deferred to Phase 2 as OQ-032** (full design space incl. the leverage-preserving margin-on-a-1×-UCITS path the four OQ-031 options had omitted; the honest scope is a *trilemma* — PRIIPs blocks US leveraged ETPs, PMA blocks UK ones, Cash blocks margin-leverage). [ADR-043](./docs/decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2) + [ADR-047](./docs/decisions/DECISIONS.md#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043) gain a `refined-by: ADR-052` frontmatter backref (QQL3 leg now provisional). Because Option 1 is no-code-change, the Option-3 universe-re-validation half-session is **not** spent at M3.3 — it moves to Phase 2 / OQ-032.

- **M3.4 — Mixed-currency P&L reconciliation.** Account-snapshot smoke during an M3.2 capture run with both legs at non-zero positions: QQL3 (USD) + IBTL / IBTM (GBP-hedged). Verify MaintMargin / GrossPositionValue / NetLiquidation reconcile correctly across the currency pair (M2-IB exercised the fields synthetically; M3 confirms the live shape per [RETRO-M2-IB §"Recommendations"](./docs/retros/M2-IB_retrospective.md) #4). The 30s diff-suppress AccountUpdate emission timer (per [ADR-033](./docs/decisions/DECISIONS.md#adr-033--accountupdate-emission-timer-30s-diff-suppress)) is the observation surface. Substrate: DD-2 v0.2 → v0.3 (mixed-currency footnote, if needed); KB-6 v0.1 → v0.2 (currency-pair section, if needed). **✓ DONE 2026-06-05 (streamlined-clean).** Run live (`scripts/probe_ib_read.py` + new `scripts/probe_ib_account_ccy.py` raw-row diagnostic) against IB Paper `DUP886336` (GBP base + USD cash from the FX). Per the streamlined-clean posture, reconciled the **existing** mixed state (USD cash + GBP-hedged sleeve) — no QQL3 position needed (per OQ-031/ADR-052 the leveraged leg can't fill). **Found + fixed a real read-side bug:** `AccountSnapshot.equity` read `NetLiquidationByCurrency[base_currency]` (the GBP *sleeve*, £902,839) not the consolidated `BASE` total (£1,003,886), silently dropping the ~£101k USD sleeve — invisible until the FX split the account (single-currency at M2-IB → sleeve == total). Fix: `IBBroker._build_account_snapshot` reads the `BASE` row primary (base-ccy fallback); `_infer_base_currency` hardened to the unit-`ExchangeRate` signal; + a mixed-currency regression test; DD-1 §2.8 v0.2 → v0.3 footnote. Re-ran live: equity now £1,003,855 (full total). **Bug-fix, no ADR** (DD-1 already specified equity = total NAV; the code didn't match — a reverse-propagation fix-to-spec, not a design change). Tests 590 → 591; all gates green. DD-2 / KB-6 left untouched (the finding's SSOT is DD-1's AccountSnapshot, not a cost/margin-parity fact). **G4 exit-criterion #4 ✓ MET.**

- **M3.5 — INV-14 catalogue extension + chaos drills.** Forward-listed IB codes from [KB-3 §8](./docs/kb/ib_pacing_spec.md#8-error-code-mapping-at-pacing-boundary) (100 / 322 / 354 / 366 / 1100..1102 / 1300) promoted as they surface during the M3.2 capture run(s) or any subsequent operator session; INV-14 v0.7 → v0.8+ as the catalogue grows. Chaos drills: observe the daily 23:45 ET TWS restart as a **standalone M3.5 operator occasion** (decoupled from the former 10-day window by plan-call #6 — the bounded M3.2 capture no longer spans multiple days) per [ADR-040](./docs/decisions/DECISIONS.md#adr-040--phase-1-deployment-target-windows-host-with-native-ib-gateway) (operator-managed manual relogin); blive's reconciliation handles the disconnect/reconnect transient unchanged per [REQUIREMENTS §5.7](./REQUIREMENTS.md#57-reconciliation). Capture observed failure modes in KB-7 `failure_modes` MISSING → DRAFT v0.1 (chaos-drill catalogue from M3.5 observed drills only — full M4 catalogue defers to M4). **✓ DONE 2026-06-05 (streamlined-clean).** Ran a **controlled** Gateway stop/start drill (`scripts/probe_ib_reconnect.py`; operator stopped + restarted the live Gateway) instead of waiting for the 23:45 ET restart. **Observed:** the broker does **not** auto-detect an unexpected drop — `IBBroker.is_connected` (cached) stayed stale-`True` while the real socket (`ib.isConnected()`) went `False` (no `disconnectedEvent` handler); recovery needs `disconnect()+connect()` (connect() no-ops on the stale flag); the restart surfaced **IB error 10141** (paper-trading disclaimer must be re-accepted) + a transient `clientId 1 already in use` before the retry connected; on reconnect **positions reconciled** with the pre-drop baseline. The recovery *path* + reconciliation work via an external driver; native detect / auto-reconnect / continuous reconciliation = **M5** ([REQUIREMENTS §5.7](./REQUIREMENTS.md#57-reconciliation)). Substrate: **KB-7 `failure_modes` MISSING → DRAFT v0.1** (FM-1 catalogued); **INV-14 v0.9 → v0.10** (10141 promoted; 1100/1101/1102 stay forward-listed — no typed connectivity handler yet); new chaos-test fixture `scripts/probe_ib_reconnect.py`. **G4 exit-criteria #5 (chaos drill) + #6 (Phase 2 stubs) ✓ MET.** Tests unchanged at 591 (the drill is a manual fixture, not a unit test).

- **M3.6 — KB-2 / KB-3 STABLE flip.** Write-side §3 / §4 / §6 / §7 surface in [KB-2](./docs/kb/ib_capability_matrix.md) / [KB-3](./docs/kb/ib_pacing_spec.md) now exercised through M2-IB.6's 2161 / PMA-cap edge cases + M3.2's capture run(s). Minor table refinements remain (per [RETRO-M2-IB §"Substrate transitions"](./docs/retros/M2-IB_retrospective.md) deferred-flip note). KB-2 v0.1.1 → v1.0 STABLE; KB-3 v0.1.1 → v1.0 STABLE. **✓ DONE 2026-06-05.** Both KBs reviewed (no TODO / blocker markers; the ADR-031 rate limiter + the Phase-1 IB surface are now behaviour-verified across M2-IB / M3) and flipped **DRAFT v0.1.1 → STABLE v1.0**, scoped to the Phase-1 equity/ETF surface (Phase-2 futures / vol per OQ-032 re-opens → STALE). Refinements folded in: stale `(MISSING)` refs fixed (KB-2 → DD-7 STABLE; KB-3 → INV-14 v0.10); KB-2 §6 the 2161/Adaptive-non-bypass wire finding; ADR-040 native-Windows-Gateway note (both); KB-3 §5 cross-linked to the M3.5 reconnect drill (KB-7 FM-1). **G4 exit-criterion #7 ✓ MET.**

- **M3-close.** Write `docs/retros/M3_retrospective.md` per [`docs/retros/_template.md`](docs/retros/_template.md). Report G4 gate status. Replace `NEXT_PROMPT.md` (v1.x targeting M3.x → next version targeting first M4 / Phase 2 sub-milestone). **✓ DONE 2026-06-05.** [RETRO-M3](./docs/retros/M3_retrospective.md) written + frozen (STABLE v1.0). **G4 reported PASSED** (all 10 exit criteria). `NEXT_PROMPT.md` replaced v1.4 → **v1.5 targeting the Phase-2 readiness-audit session** (per [§8.3.2](./CONTEXT_PROTOCOL.md) — session 2 of the M3 → M4 phase boundary; plan-drafting with OQ-032 + the VIX/TQQQ/VXX notebook is session 3, not the close). **Phase 1 complete.**

**Deliverables:**

1. **EODHD-vs-IB sizing reconciliation** — QQL3 10× discrepancy fixed in code; RC-10 (price sanity) implemented per INV-4. (M3.1)
2. **M3.2 capture data file** (`~/.blive/data/m3_2_window/runs.jsonl`) — per-run per-instrument fill-rate, regime-flip count, 2161 cap-binding count, breach count, FSM-trace coverage; bounded deterministic capture (≥ 1 flip-spanning RTH run, regime variety from the replay window via `--dry-run`), reproducible via the M3.2 driver. (M3.2) — code ✓ landed; ≥ 1 capture row is the remaining operator step. (M3.2)
3. **OQ-031 resolution ADR** — chosen Option recorded with supersedes / amends chain. (M3.3)
4. **Live mixed-currency P&L observation** — MaintMargin / GrossPositionValue / NetLiquidation reconciled across QQL3 (USD) + IBTL / IBTM (GBP-hedged). (M3.4)
5. **INV-14 catalogue extension** — forward-listed codes promoted as observed during the M3.2 window. (M3.5)
6. **KB-7 stub-DRAFT** — chaos-drill failure-mode catalogue from observed M3.5 drills (TWS restart, disconnect/reconnect; full M4 catalogue defers). (M3.5)
7. **INV-8 stub-DRAFT** — fill-rate / cap-binding / regime-flip metrics catalogue (full Prometheus surface at M7). (M3.2)
8. **INV-9 stub-DRAFT** — kill-switch alerts catalogue (full alerting at M7). (M3.2)
9. **KB-15 stub-DRAFT** — unit-of-quote / reverse-split parity-methodology section (full M7 surface defers). (M3.1)
10. **KB-2 / KB-3 STABLE flip** — write-side surface fully exercised. (M3.6)
11. **RETRO-M3** — frozen on first write per [ADR-024](./docs/decisions/DECISIONS.md#adr-024--add-session-retrospective-artefact-type). (M3-close)
12. **Successor `NEXT_PROMPT.md`** — version bump targeting first M4 / Phase 2 sub-milestone. (M3-close)

**Substrate transitions:**

- **OQ-031**: ✓ OPEN → RESOLVED-BY-ADR-052 at M3.3 (2026-06-05; Option 1 — accept the leveraged-leg non-fill).
- **OQ-032**: ✓ raised at M3.3 — Phase 2 A3 leveraged-leg redesign (the deferred redesign; full design space incl. the leverage-preserving margin-on-a-1×-UCITS path).
- **ADR-052**: ✓ ACCEPTED, recording the OQ-031 resolution (Option 1). `refined-by: ADR-052` backref added to ADR-043 + ADR-047 frontmatter (QQL3 leg provisional).
- **KB-2** v0.1.1 DRAFT → v1.0 STABLE (M3.6).
- **KB-3** v0.1.1 DRAFT → v1.0 STABLE (M3.6).
- **KB-7** ✓ MISSING → DRAFT v0.1 (M3.5 chaos-drill catalogue; FM-1 IB Gateway drop / daily restart, 2026-06-05).
- **KB-15** MISSING → DRAFT v0.1 (M3.1 unit-of-quote section).
- **INV-4** v0.1 DRAFT → v0.2 DRAFT (RC-10 row promoted to implemented).
- **INV-8** MISSING → DRAFT v0.1 (M3.2 metrics catalogue). ✓ 2026-06-05.
- **INV-9** MISSING → DRAFT v0.1 (M3.2 alerts catalogue). ✓ 2026-06-05.
- **INV-14** ✓ v0.7 → v0.10 (M3.1 error 110 two sub-causes; M3.5 error 10141 paper-trading disclaimer + the 1100/1101/1102-stay-forward-listed note).
- **DD-2** v0.2 → v0.3 if M3.4 reveals new mixed-currency surface.
- **KB-6** v0.1 → v0.2 if M3.4 reveals new currency-pair section needed.
- **RETRO-M3** new → STABLE v1.0 (M3-close, frozen on first write).

**Exit criteria (G4 gate — rewritten for the deployment-decision framing):**

1. **OQ-031 RESOLVED.** Chosen deployment-mode option (1 / 2 / 3 / 4) recorded as a new ADR with supersedes / amends chain, grounded in the M3.2 empirical data file. Decision is auditable: data → option chosen → why. **✓ MET 2026-06-05** — ADR-052 (Option 1: accept the PMA-bound leveraged-leg non-fill; no code change), auditable data → option → why; OQ-031 → RESOLVED-BY-ADR-052; leveraged-leg redesign deferred to Phase 2 (OQ-032).
2. **EODHD-vs-IB sizing reconciled.** QQL3 sizing produces correct USD-equivalent dollar exposure (within 1%); RC-10 (price sanity) implemented per INV-4 and exercised in production code.
3. **Bounded deterministic M3.2 capture** (per plan-call #6, re-scoped 2026-06-05 from "10 LSE-RTH trading days"): `~/.blive/data/m3_2_window/runs.jsonl` holds ≥ 1 RTH capture run over a `--max-bars` window spanning ≥ 1 equity-leg regime flip (offline-verifiable via `--dry-run`), at the substituted universe (`QQL3` / `IBTL` / `IBTM`), showing per-instrument fill-rate with QQL3 ≈ 0 (structural 2161 cap confirmed) + IBTL / IBTM fills > 0. A regime-flat window is annotated via `--note` rather than waited out (Q2 quality check).
4. **Mixed-currency P&L reconciled.** Live observation of USD exposure (USD cash and/or a USD position) alongside the GBP-hedged IBTL / IBTM sleeve; MaintMargin / GrossPositionValue / NetLiquidation reconcile across the currency pair. **✓ MET 2026-06-05** — amended from the original "QQL3 (USD) position" wording (per OQ-031/ADR-052 the QQL3 leg can't fill, so the USD side is observed via USD cash from the FX); the live reconciliation surfaced + fixed the `equity`-reads-base-sleeve bug (now £1,003,855 BASE total, was £902,839 GBP sleeve).
5. **Chaos drills survived.** ≥ 1 daily 23:45 ET TWS restart observed with disconnect/reconnect handled and reconciliation correct on resume. (Decoupled from M3.2 by the plan-call #6 re-scope — formerly "observed during the 10-day M3.2 window"; now a standalone M3.5 operator occasion, since the bounded M3.2 capture no longer spans multiple days.) **✓ MET 2026-06-05** — a controlled Gateway stop/start drill (`scripts/probe_ib_reconnect.py`) substituted for the 23:45 ET restart (streamlined-clean): drop observed, recovery via `disconnect()+connect()` succeeded, positions reconciled. The broker's lack of *native* auto-detect / auto-reconnect is documented in [KB-7 FM-1](./docs/kb/failure_modes.md) as the M5 gap (REQUIREMENTS §5.7); the restart surfaced IB 10141 (paper-trading disclaimer) → INV-14 v0.10.
6. **Phase 2 substrate stubs in place.** KB-7, KB-15, INV-8, INV-9 each at DRAFT v0.1 (M3-window content only — full M4/M7 catalogue defers). **✓ MET 2026-06-05** — KB-15 DRAFT v0.1 (M3.1), INV-8 + INV-9 DRAFT v0.1 (M3.2), KB-7 DRAFT v0.1 (M3.5) all in place.
7. **KB-2 / KB-3 STABLE.** Both flipped from DRAFT v0.1.1 → v1.0 STABLE.
8. **No M2-IB regressions.** G3-IB-A3 still passes; SMART/LSEETF routing still clean; FSM coverage still wire-validated.
9. **RETRO-M3 written + frozen** per ADR-024.
10. **Test suite green.** mypy --strict / black / isort / lint-imports / pytest all green at M3-close commit.

**Estimated effort:** ~5–7 sessions across M3.1 → M3-close (revised down by the plan-call #6 re-scope). Breakdown: M3.1 reconciliation ✓ (1–2 sessions; EODHD-vs-IB + RC-10), M3.2 ✓ code + INV-8/INV-9 stubs landed (this session) + **1–2 operator RTH capture sessions** (bounded deterministic capture, not a 10-day campaign — `--max-bars` window spanning a regime flip), M3.3 OQ-031 resolution (1 session, operator-led; +0.5 if Option 3 chosen), M3.4 mixed-currency (folds into an M3.2 RTH capture; no separate session), M3.5 INV-14 + chaos drills (now a standalone operator occasion — TWS-restart drill decoupled from the former 10-day window; KB-7 stub at M3.5), M3.6 KB-2 / KB-3 flip (substrate-only; ~1 session), M3-close (~1 session, RETRO + NEXT_PROMPT bump).

**Dependencies:** M2-IB.6 closed (✓ at `M2-IB.6-close` 2026-05-06); Phase 2 readiness audit closed (✓ at commit `c5fb1b4`); operator availability for M3.2 window monitoring + M3.3 resolution + M3.4 mixed-currency entry timing.

---

## Sketched M4+ (post-Phase-1)

The detailed plan stops at M3. M4+ are sketched here only to set expectations and to identify the artefact ladder Phase 2 will depend on. **Refreshed 2026-05-06 at the M3 plan-drafting session** per [PHASE_2_READINESS Q5](./docs/PHASE_2_READINESS.md): M3 ships stub-DRAFTs only; full content lands in native milestones below.

- **M4** — RiskEngine full (**RC-01..RC-07 + RC-11**; RC-10 already from M3.1; RC-08/09/12/13 already from M1); SQLite persistence ([DD-4 `storage_schemas`](./docs/dd/storage_schemas.md) MISSING → DRAFT, `PersistencePort` switches from in-memory to SQLite-backed per [ADR-006](./docs/decisions/DECISIONS.md#adr-006--sqlite-for-persistence-in-v1)); structured logging.
  - **Refresh delta vs v0.4:** RC-10 carved out (lands at M3.1 instead). Rest unchanged — Q5's M3 stubs do not pull M4 work forward.
  - **Forward-note (M3.1 → 2026-05-06):** **vendor-convention catalogue centralisation** — promote `src/blive/adapters/eodhd/conventions.py` dict-literal to a YAML-driven catalogue under `~/.blive/config/` (paralleling [ADR-035](./docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets) secrets pattern) IF the catalogue grows ≥3-5 entries OR operator-side editing pressure builds. M3.1 ships one entry (QQL3); the dict-literal scales gracefully through M3.2's empirical window. Not scheduled at M3.1 entry per the operator decision; lands here when the trigger fires.
- **M5** — Reconciliation continuous loop; daily TWS-restart handling first-class (extends M3.5's stub); `RUNBOOK.md` drafted; [KB-7 `failure_modes`](./docs/kb/failure_modes.md) extended from M3.5's stub-DRAFT to full catalogue.
  - **Refresh delta vs v0.4:** Phase 2 readiness audit removed from M5 (executed early at the §8.3.2 phase boundary 2026-05-06). KB-7 framing shifts from "MISSING → DRAFT" to "extends M3's stub".
- **M6** — Web UI (3 pages) per [ADR-011](./docs/decisions/DECISIONS.md#adr-011--3-page-minimal-web-ui-mobile-and-oauth-deferred); REST endpoints; SSE log stream.
  - **Refresh delta vs v0.4:** unchanged.
- **M7** — Full parity diagnostic (extends M3.1's narrow unit-of-quote reconciliation to full envelope re-derivation against the substituted universe); full Prometheus + Grafana observability ([INV-8 `metrics`](./docs/inv/metrics.md) + [INV-9 `alerts`](./docs/inv/alerts.md) extended from M3.2's stubs); [KB-15 `parity_methodology`](./docs/kb/parity_methodology.md) extended from M3.1's stub.
  - **Refresh delta vs v0.4:** M3.1 pre-empted a small slice (unit-of-quote section only); M7 still owns the full parity envelope re-derivation against `QQL3` / `IBTL` / `IBTM` (regime profile shifts since 1× US-Treasury legs replace 3× per ADR-047; backtest CAGR / Sharpe / MDD do not carry forward). INV-8 / INV-9 / KB-15 framings shift from "MISSING → DRAFT" to "extends M3's stub".
- **M8** — Hardening: TLS, audit-log hash chain, backup automation, ops runbook fully realised. Real-money cutover gate.
  - **Refresh delta vs v0.4:** unchanged.

Phase 2 begins at the entry to M4 with strategy `triple_lev_sma_filter_dsl` carried forward from the now-active Phase 1 A3 path (current live-paper tradables per ADR-047: `QQL3` / `IBTL` / `IBTM`), in whichever deployment-mode shape OQ-031 resolves to at M3.3. Phase 2 detailed plan is **not** drafted at this session — it awaits M3-close; M3 → M4 is itself the Phase 1 → Phase 2 boundary, likely warranting another §8.3.2-style transition informed by M3's empirical artefacts (OQ-031 resolution, observed parity envelope, chaos-drill failure modes, mixed-currency P&L shape).

---

## Quality Gates

A quality gate is a checkpoint at the boundary between milestones. The gate must pass before the next milestone begins.

| Gate | What it checks | Owner |
|------|----------------|-------|
| **G0** (M0 entry) | ADR-001..023 stable (✓ ADR-020..023 added 2026-04-26) | **PASSED 2026-04-26** |
| **G1** (M0 → M1) | DD-1, INV-13 STABLE; PaperBroker round-trip green; import-linter passing | **PASSED 2026-04-26** (see [RETRO-M0](./docs/retros/M0_retrospective.md)) |
| **G2** (M1 → M2) | btest equity-match within ±1 bps; M1 deliverables complete; operator-side prereqs verified | **PARTIAL 2026-04-27** (see [RETRO-M1](./docs/retros/M1_retrospective.md)) — pipeline machinery + 175 tests green; real-data ±1 bps run deferred to operator EODHD CAC.PA + TKAN artefact run |
| **G3-IB-A3** (M2-IB.6 → Phase-2-readiness entry) | IB Gateway connect within 5s; ADR-047 PRIIPs premise empirically validated; resolver shape for the UK-listed universe reaches ACCEPTED cleanly; next available LSE-RTH run yields non-zero FILLED count with zero rejects / zero breaches; RETRO-M2-IB written | Oleg — **ACTIVE / PARTIAL 2026-05-06** (PRIIPs probe + broker fix ✓; LSE-RTH fill validation still pending) |
| **G3-IG** (M2-IG → M2-IG.5 close) | IG demo read+write working; Lightstreamer + REST throttle green; session-token auto-refresh tested; `tkan_v4_momentum_timing` 1× runs ≥ 5 trading days on IG demo with directional alignment | Oleg — **NOT_REACHED 2026-04-28** (operator-driven bridge close before strategy run; not a gate failure — see [RETRO-M2-IG](./docs/retros/M2-IG_retrospective.md)) |
| **G4** (M3 → M4 / Phase 2 entry) | All 10 M3 exit criteria met (OQ-031 RESOLVED + EODHD-vs-IB sizing reconciled + bounded M3.2 capture ≥ 1 flip-spanning run + mixed-currency P&L reconciled + chaos drills survived + Phase 2 stub artefacts in place + KB-2/KB-3 STABLE + no M2-IB regressions + RETRO-M3 written + test suite green); deployment-mode commitment for live cutover is reviewable | Oleg — **PASSED 2026-06-05** (all 10 exit criteria met; OQ-031 RESOLVED via ADR-052 + EODHD-vs-IB sizing + bounded M3.2 capture + mixed-currency P&L [+ equity-bug fix] + chaos drill + Phase-2 stubs + KB-2/KB-3 STABLE + no regressions + RETRO-M3 + 591 green; see [RETRO-M3](./docs/retros/M3_retrospective.md)) |

---

## Risk register (Phase 1)

Risks specific to Phase 1 (broader risks live in [REQUIREMENTS](./REQUIREMENTS.md) and [INV-4](./docs/inv/risk_checks.md)):

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| ~~IB Paper account reopen takes longer than expected~~ ✓ Resolved 2026-04-28 (account commissioned; enabled 2026-04-29) | — | — | — |
| ~~IG demo session token expires unexpectedly mid-run~~ ✓ Archived with M2-IG bridge close | — | — | — |
| ~~CAC 40 CFD financing-cost variability blows past parity envelope~~ ✓ Archived with M2-IG bridge close | — | — | — |
| ~~`lightstreamer-client-lib` callback-driven API maturity~~ ✓ Archived; abstraction layer captured the contract; production wrapper deferred | — | — | — |
| ~~IG demo CAC 40 CFD epic differs from `IX.D.CAC40.CASH.IP` guess~~ ✓ Archived with M2-IG bridge close | — | — | — |
| Docker / IBC setup fragile on Windows host | Medium | M2-IB.2 friction | Plan Linux-host fallback; document discoveries in [KB-8](./docs/kb/operational_events.md) §1-§3 (IB-side) |
| btest version drift breaks blive imports during M2-IB | Medium | rebuild | Pin btest commit; CI smoke-imports check (M0 deliverable) catches early; coordination policy in [ADR-010](./docs/decisions/DECISIONS.md#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import) |
| TKAN artefact retrained mid-Phase-1 produces non-stationary signal | Low | strategy underperforms | Acceptable on paper; revisit at G3-IB / G4 |
| Parity envelope between CAC.PA price-return and CACT total-return wider than expected | High | documentation only | Document; do not block M2-IB.5; feed into M7 parity diagnostic design |
| `ib_async`'s callback model bridges to asyncio cleanly | Low | M2-IB.2 friction | `ib_async` is asyncio-native (per [ADR-002](./docs/decisions/DECISIONS.md#adr-002--adopt-ib_async-v21-as-wire-level-ib-driver)); thinner adapter than the IG Lightstreamer wrapper would have needed |
| IB daily TWS restart at 23:45 ET disrupts the ≥ 5-day strategy run | Medium | M2-IB.5 friction | First-class operational event per [KB-3 §5](./docs/kb/ib_pacing_spec.md#5-daily-and-weekly-operational-events) + [KB-8 §1](./docs/kb/operational_events.md); engine pauses + reconciles + resumes per [REQUIREMENTS §5.7](./REQUIREMENTS.md#57-reconciliation) |
| EODHD CAC index coverage insufficient | Low (verified) | M2 redo | **Verified 2026-04-27** (M1-close lane). EODHD probe ran with operator-supplied key: `CAC.PA` daily EOD (2024-12 sample) returns full OHLC + adjusted_close + volume — primary tradable per [ADR-021](./docs/decisions/DECISIONS.md#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) covered. `CAC.PA` real-time quote returns delayed-tier data (sufficient for Phase-1 EOD strategy). Open small follow-up for M2: the CAC 40 *index* ticker is not `CAC.INDX` (404 from EODHD); when wiring `EODHDDataSource`, try `PX1.INDX` / `^FCHI`. Index feed is nice-to-have for parity-residual decomposition, not a G2 blocker. |
| Docker / IBC setup fragile on Windows host | Medium | M2 friction | Plan Linux-host fallback; document discoveries in KB-8 |
| btest version drift breaks blive imports during Phase 1 | Medium | rebuild | Pin btest minor; CI smoke-imports check (M0 deliverable); coordination policy in [ADR-010](./docs/decisions/DECISIONS.md#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import) |
| TKAN artefact retrained mid-Phase-1 produces non-stationary signal | Low | strategy underperforms | Acceptable on paper; revisit at G4 |
| Parity envelope between CAC.PA price-return and CACT total-return wider than expected | High | documentation only | Document; do not block M3; feed into M7 parity diagnostic design |

### Phase 2 entry risks (added 2026-05-06 at M3 plan-drafting)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **M3.2 paper-mode window observes zero regime flips on QQL3** | Medium | OQ-031 decision lacks regime-variety evidence | Q2 quality check at plan-drafting: M3-close annotates regime-flat windows; OQ-031 resolution explicitly notes data limitation; option to extend window if operator wishes |
| **EODHD unit-of-quote reconciliation in M3.1 reveals deeper data-quality issues across the 5-ticker bundle** | Low | M3.1 scope balloons | M3.1 narrow scope: QQL3 only at first; broader audit deferred to M7 parity-envelope work |
| **Live IB market-data subscription cost or eligibility for sizing reference** | Low | M3.1 implementation route choice | M3.1 carries two routes: (a) live IB market data, (b) EODHD-convention conversion at sizing time — operator chooses based on cost / friction |
| **OQ-031 Option 3 (substitute non-leveraged equity leg) chosen at M3.3** | Medium | M3 timeline extends; M3.4 / M3.5 re-validate | Plan reserves a half-session for Option-3 amendment ADR + universe re-validation if chosen |
| **Forward-listed IB error codes (322 dup orderId, 354, 366, etc.) surface during M3.2 window** | Medium | M3.5 INV-14 catalogue extension absorbs them | Expected; no separate mitigation beyond the planned catalogue work |
| **Chaos drill (TWS daily 23:45 ET restart) reveals reconciliation gap** | Low | M5 work pulled forward into M3 | If gap surfaces, Q5's "stay in native milestone" bias revisited at M3-close; otherwise M5 reconciliation work stays at M5 |

---

## Open dependencies on operator action

Items still requiring Oleg's input or action:

1. ~~Confirm or override OQ-024..OQ-027 defaults.~~ ✓ Done 2026-04-26 (ADR-020..023).
2. ~~**Verify IG demo account credentials**.~~ ✓ Done 2026-04-27 (M2-IG.1). Now archived with the M2-IG bridge close.
3. ~~**Verify IB Paper account access**.~~ ✓ Done 2026-04-28: account commissioned, enabled 2026-04-29.
4. ~~**Place IB connection params at `~/.blive/secrets/ib.env`**~~ ✓ Done before the 2026-05-01 handshake; the live wire path through M2-IB.3 → M2-IB.6 proves `IB_PAPER_ACCOUNT_ID` is populated correctly.
5. ~~**Decide deployment target** (Linux VM vs Windows host).~~ ✓ Resolved 2026-04-28 by [ADR-040](./docs/decisions/DECISIONS.md#adr-040--phase-1-deployment-target-windows-host-with-native-ib-gateway): Phase 1 = Windows host with native IB Gateway (no Docker / IBC); Linux VM + Docker + IBC deferred to M8 production cutover. Daily 23:45 ET TWS-restart handled by operator-managed manual relogin during the M2-IB.5 ≥5-day run; blive's reconciliation handles the disconnect/reconnect transient unchanged.
6. ~~**First IB Gateway handshake**~~ ✓ Done 2026-05-01. `scripts/probe_ib_handshake.py` ran clean against the operator's paper Gateway: connected in 0.53s (≪ G3-IB 5s target); `is_connected=True`; rate limiter consumed + refilled correctly; clean `disconnect`. Account id stayed `[REDACTED]` in output per ADR-035 secret-field discipline. The wire is alive.
7. **Next available LSE-RTH operator window** — OPEN. The remaining milestone blocker is operational timing, not substrate authoring: run `scripts/run_m2ib6_ib_paper.py` during the next London cash session with IB Gateway live and the existing 5-ticker EODHD fixtures in place.

---

## Cross-References

- [REQUIREMENTS.md §14](./REQUIREMENTS.md) — milestones M0..M8.
- [PHASE_1_READINESS.md](./docs/PHASE_1_READINESS.md) — readiness audit gating this plan.
- [ADR-013](./docs/decisions/DECISIONS.md#adr-013--v1-scope-etf-and-index-strategies-only) — v1 scope.
- [KB-5 §7](./docs/kb/strategy_taxonomy.md#7-nav-slice--priorities) — phased priority.
- [KB-11](./docs/decisions/OPEN_QUESTIONS.md) — OQ-023..OQ-027.
- [INV-4](./docs/inv/risk_checks.md) — risk checks RC-01..RC-13.
- [CONTEXT_INVENTORY.md §1](./CONTEXT_INVENTORY.md#1-representation-hierarchy) — this file is layer 4.
- [CONTEXT_PROTOCOL.md §3](./CONTEXT_PROTOCOL.md) — edit discipline that governs updates here.

---

## Changelog

- **v0.1 (2026-04-26)** — initial draft. M0..M3 detailed; M4+ sketched. Five quality gates defined. Risk register seeded. Conditional on OQ-024..OQ-027 default confirmation.
- **v0.1.1 (2026-04-26)** — operator confirmed OQ-024..OQ-027. Phase 1 specifics table promoted from "proposed" to confirmed values, citing ADR-020..023 instead of OQs. **G0 gate passed.** Remaining operator dependencies are now operational prereqs for G2 (IB Paper account, EODHD coverage, deployment target).
- **v0.1.2 (2026-04-26)** — **M0 closed; G1 gate PASSED**. All ten M0 deliverables landed (scaffolding, DD-1 STABLE, INV-13 STABLE, INV-6 DRAFT, INV-5 DRAFT, domain layer, paper / in-memory / clock adapters, tests, import-linter contract + negative test, CONTEXT_INVENTORY sync). 113 tests green; mypy strict clean; both contracts KEPT. See [RETRO-M0](./docs/retros/M0_retrospective.md). Next milestone is M1 — see [NEXT_PROMPT.md](./NEXT_PROMPT.md) v0.2.
- **v0.1.3 (2026-04-27)** — **M1 closed; G2 gate PARTIAL.** All seven M1 deliverables landed (smoke-import, strategy loader, btest engine wiring via `SingleAssetRunner` per OQ-030, Sizer with ADR-027 rounding, RiskEngine M1-subset RC-08/09/12/13, paper-mode pipeline, DD-3 DRAFT). Plus PaperMarketData / LogAlert / PaperBroker.replace / RiskBreach domain-event relocation. ADR-027..029 ACCEPTED; OQ-030 raised; INV-5/INV-6 promoted to STABLE. 175 tests green; mypy strict clean; both contracts KEPT. See [RETRO-M1](./docs/retros/M1_retrospective.md). G2 ±1 bps real-data parity run is operator-deferred (needs EODHD CAC.PA fixture + TKAN artefact + momentum factor). M2 begins after G2 closure — see [NEXT_PROMPT.md](./NEXT_PROMPT.md) v0.3.
- **v0.2 (2026-04-27)** — **M2 split into M2-IB (PARKED) and M2-IG (ACTIVE)** per option (S) of operator-driven IG-demo-bridge pivot. Substrate authored: cross-cutting [ADR-034](./docs/decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004) (multi-broker registry pattern; extends ADR-004) and [ADR-035](./docs/decisions/DECISIONS.md#adr-035--secrets-handling-discipline-blivesecrets) (secrets handling discipline; ~/.blive/secrets/{broker}.env + redaction list) — both PROPOSED; first-batch IG-bridge substrate. Phase 1 specifics table grew an "M2-IG bridge path" column (CAC 40 CFD on IG demo; ADR-021 PAUSED for the bridge). Quality Gates table split G3 → G3-IB (DEFERRED) + G3-IG (ACTIVE). Risk register grew IG-specific rows. Open dependencies cleaned up for IG bridge. M2-IG sub-milestones .1 (substrate) / .2 (cross-cutting infra) / .3 (read side) / .4 (write side) / .5 (strategy run + retro) defined.
- **v0.3 (2026-04-28)** — **M2-IG bridge CLOSED at architectural surface; M2-IB UNPARKED to ACTIVE.** Operator pivot: IB Paper account commissioned 2026-04-28 (enabled 2026-04-29). [RETRO-M2-IG](./docs/retros/M2-IG_retrospective.md) STABLE-on-first-write captures the bridge close: ~2 sessions delivered M2-IG.1 substrate + M2-IG.2 cross-cutting infra + M2-IG.3 read side + M2-IG.4 minimum-viable submit (7 tags placed; 359 tests). M2-IG.5 strategy run + production Lightstreamer wrapper DEFERRED with no scheduled revival. M2-IB resumption defined with sub-milestones M2-IB.1 (substrate verification) / .2 (IBClient + IBCredentials) / .3 (IBInstrumentResolver + read side + IBMarketData) / .4 (write side + reconciliation) / .5 (strategy run on IB Paper + RETRO-M2-IB). M2-IG section relabelled ARCHIVED (G3-IG NOT_REACHED, operator-driven close not gate failure). Phase 1 specifics table reverts to ADR-021 ETF path as canonical; ADR-039 CFD variant stays ACCEPTED but bridge-paused. Quality Gates: G3-IB ACTIVE; G3-IG NOT_REACHED. Risk register: IG-specific rows archived; IB-specific rows reasserted. Open dependencies updated: IG operator-side items closed; IB connection params + deployment target + first IB Gateway handshake opened. NEXT_PROMPT.md v0.4 drafted to target M2-IB.
- **v0.4 (2026-05-02)** — **Phase 1 strategy switch per [ADR-043](./docs/decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2): A3 (`triple_lev_sma_filter_dsl` on TQQQ/TMF/IEF) replaces A2 (`tkan_v4_momentum_timing` on CAC.PA).** ADR-021 SUPERSEDED-BY-ADR-043. M2-IB.5 closed at architectural surface 2026-05-02 (CLOSED-EARLY-BY-OPERATOR; the 60-bar replay validated the single-instrument pipeline + IB write-side wire across the M2-IB.4a-* tag chain — durable substrate, but no longer the strategy-run target). New milestone **M2-IB.6** opens with sub-milestones .6-substrate (this commit batch) / .6.1 (multi-instrument pipeline + 5-ticker EODHD refresh + LongShortPortfolio btest dispatch + IB SMART resolver convention) / .6.2 (IB Paper end-to-end run during US RTH for FILLED validation) / .6-close (RETRO-M2-IB + NEXT_PROMPT.md v0.6 targeting Phase 2 readiness audit per CONTEXT_PROTOCOL §8.3.2 phase-boundary protocol). Phase 1 specifics table rewritten to reflect the A3 path (5-ticker universe, SMART routing, LongShortPortfolio dispatch, EODHD-only data per ADR-017 hybrid routing — no IB market-data subscription needed for US ETFs at delayed-daily tier). G3-IB superseded by G3-IB-A3 (criteria amended for multi-instrument FSM + FILLED validation). New ADRs (companion): ADR-044 multi-instrument pipeline, ADR-045 LongShortPortfolio dispatch, ADR-046 IB SMART for US equities — all ACCEPTED in the next commit. A2 (`tkan_v4_momentum_timing`) marked DEFERRED-NO-TARGET; code stays in repo. KB-5 §7 phased priority reordered. INV-1 v0.1 → v0.2.
- **v0.7 (2026-05-06 / M3.1 implementation landing)** — M3.1 sub-milestone implementation landed in this commit (held PROPOSED for the wire-validation flip per the M2-IB pattern). M3.1 sub-milestone description grew the inline ✓ deliverable record + ADR-050 PROPOSED reference + the operator's Hybrid B-now / A-later free-MD-only choice + the central-config deferred decision. Sketched M4+ M4 row gained a forward-note for "vendor-convention catalogue centralisation" — promote `blive.adapters.eodhd.conventions` dict-literal to YAML when surface ≥3-5 entries. No new ADRs accepted (ADR-050 PROPOSED only); no new OQs raised. Substrate transitions: ADR-050 PROPOSED added (DECISIONS v0.19 → v0.20); KB-15 MISSING → DRAFT v0.1; INV-4 v0.1 → v0.2; INV-14 v0.7 → v0.8; DD-7 v1.4 footnote. Tests: 519 → 541. Pending: wire-validation smoke during LSE RTH; ADR-050 flips to ACCEPTED on success.
- **v0.6 (2026-05-06)** — **M3 plan-drafted at the [CONTEXT_PROTOCOL §8.3.2](./CONTEXT_PROTOCOL.md) phase-boundary third session.** Replaces the legacy "M3 — IB Adapter (Write Side) & First Live (Paper) Strategy" section (which closed inside M2-IB.4 / M2-IB.6 already) with the **deployment-decision M3** plan — sub-milestones M3.1 (EODHD-vs-IB unit-of-quote reconciliation + RC-10) / M3.2 (10-day empirical paper-mode window) / M3.3 (OQ-031 resolution as new ADR) / M3.4 (mixed-currency P&L reconciliation) / M3.5 (INV-14 extension + chaos drills + KB-7 stub) / M3.6 (KB-2 / KB-3 STABLE flip) / M3-close. Five plan-drafting calls recorded inline (Q1 inform-then-resolve / Q2 10-day calendar-bound window / Q3 EODHD-vs-IB pull forward to M3 / Q4 A3-only / Q5 stub-DRAFT only what M3 produces). Sketched M4+ refreshed: M4 picks up RC-01..RC-07 + RC-11 (RC-10 carved out to M3.1); M5 loses Phase 2 readiness audit (already executed at the §8.3.2 boundary); M5 KB-7 / M7 INV-8 / INV-9 / KB-15 framings shift from "MISSING → DRAFT" to "extends M3's stub". G4 gate exit criteria rewritten around the 10 deployment-decision exit criteria (was: M2-IB.5 strategy-run criteria + PHASE_2_READINESS drafted; now: OQ-031 RESOLVED + EODHD-vs-IB sizing reconciled + 10-day window + mixed-currency + chaos drills + Phase 2 stubs + KB-2/3 STABLE + no regressions + RETRO-M3 + tests green). Risk register grows six Phase-2-entry rows (regime-flat window risk, EODHD broader data-quality risk, IB live-data-subscription risk, OQ-031 Option-3-amends risk, INV-14 catalogue-growth risk, chaos-drill reconciliation-gap risk). No new ADRs; no new OQs. Substrate-only session. Successor [NEXT_PROMPT.md](./NEXT_PROMPT.md) replaced v0.9 → v1.0 targeting M3.1.
- **v0.5 (2026-05-06)** — Reconciled TASK_REGISTRY to the actual post-`abebc5a` repo state. M2-IB.6-substrate and M2-IB.6.1 marked complete; M2-IB.6.2 split conceptually into the now-complete US-RTH PRIIPs validation probe (ADR-047 empirically validated, broker `ib.errorEvent` stash fix landed, INV-14 v0.6) and the still-pending next-available LSE-RTH filled run for `QQL3` / `IBTL` / `IBTM`. ADR-048 recorded as intentionally PROPOSED-in-working-tree pending fill validation. Quality-gate and open-dependency sections updated so the only live blocker is the LSE-RTH operational window, after which M2-IB.6-close can write RETRO-M2-IB and hand off to either Phase 2 readiness or follow-up diagnosis.
- **v0.8 (2026-06-05 / M3.1b close)** — M3.1b (ADR-051 tick-grid normalization) implemented; ADR-050 + ADR-051 flipped PROPOSED → ACCEPTED jointly on the clean LSE-RTH `--order-type LMT --max-bars 5` wire run (zero IB error 110). M3.1 sub-milestone description grew the inline ✓ close record + the M3.1b sub-milestone bullet. (Frontmatter bumped 0.7 → 0.8; recorded here for changelog continuity.)
- **v0.9 (2026-06-05 / M3.2 results-capture)** — M3.2's **code deliverables + INV-8/INV-9 stub-DRAFTs landed** (the 10-LSE-RTH-day window run itself stays operator-driven; M3.2 remains OPEN until the dataset is complete). Shipped: the per-run results sink `src/blive/runtime/m3_2_record.py` (`RunRecord` builder + JSONL appender → `~/.blive/data/m3_2_window/runs.jsonl`) wired into `scripts/run_m2ib6_ib_paper.py`; additive capture surface on `IBMultiRunResult` (`accepted_count` / `submitted_by_symbol` / `observed_error_codes` + `cap_binding_2161_count`), `_drain_order_lifecycle` (`reached_accepted`), `IBBroker.observed_error_codes` (order-related error/warning tally — the warning-2161 PMA-cap signal), and `blive.runtime.signals.equity_leg_regime_flips`. Substrate: INV-8 `metrics` + INV-9 `alerts` MISSING → DRAFT v0.1 (M3.2-only stubs); CONTEXT_INVENTORY v0.16 → v0.18 (banner + INV-8/INV-9 rows + Code/Tests rows v1.8 → v1.9 + §10; the v0.18 increment also carries the plan-call #6 re-scope, see v0.10 below). Tests 568 → 590 (+11 results-sink, +7 regime-flip, +3 pipeline-capture, +1 broker-tally); mypy `src` / black / isort / lint-imports all green. No new ADRs / OQs (the sink shape is a refinement per NEXT_PROMPT v1.1). Next: operator runs the M3.2 window → M3.3 (OQ-031 resolution) consumes the dataset.
- **v0.10 (2026-06-05 / M3.2 re-scope — bounded deterministic capture)** — operator call after the M3.2 code landed: **M3.2's exit re-scoped from "10 LSE-RTH calendar trading days" → a bounded set of capture rows** (plan-call #6, recorded inline). Rationale: the driver is a *historical-replay* tool (not the M5 daemon), so regime variety is **deterministic from the replay window** (`--max-bars`), offline-verifiable — empirically `--max-bars 60` spans 2 equity-leg flips, `--max-bars 5` spans 0 — and QQL3's structural ≈0 fill-rate under the 2161 cap is already established (M2-IB.6.2c / M3.1b), so 10 calendar days would mostly re-confirm a known result. Close criterion: ≥1 RTH run over a flip-spanning window with QQL3 ≈0 fills + IBTL/IBTM fills >0. G4 exit-criterion #3 amended; #5 (chaos drill) decoupled from the former 10-day window to a standalone M3.5 occasion; M3 effort estimate revised ~6–8 → ~5–7 sessions. Driver gained `--dry-run` (offline regime-coverage preview, no IB; the data-load now precedes the IB connect). Not an ADR (a plan refinement consistent with calls #1–#5). No code-logic/test changes vs v0.9 (the `--dry-run` path is driver-only, exercised offline against the local EODHD parquets).
- **v0.11 (2026-06-05 / M3.2 capture-complete)** — **M3.2's bounded-capture criterion MET** on the live IB-Paper + EODHD wire (LSE RTH 2026-06-05). After a `--max-bars 5` smoke validated the chain end-to-end (real IBTM fill, sink row written), two flip-spanning captures landed in `~/.blive/data/m3_2_window/runs.jsonl`: `max-bars 40` (2 flips, QQL3 25/0, IBTM 3/3) + `max-bars 60` (2 flips, QQL3 44/0, IBTM 3/3). **Aggregate QQL3 0/69 (0%) vs IBTM 6/6 (100%); 2161=0; zero rejects/breaches/error-110** — the empirical OQ-031 signal, with the finding that ADAPTIVE_MKT does not trip the *visible* 2161 cap yet QQL3 still does not fill. New `scripts/flatten_ib_paper.py` (raw-`ib_async` paper-account reset, scoped to QQL3/IBTL/IBTM, distinct clientId, `--dry-run`) added + used to flatten the accumulated IBTM (230 → 0). M3.2 sub-milestone marked capture-complete; M3.2 data deliverable done. No new ADRs / OQs (capture + flatten are operational; OQ-031's *resolution* is M3.3 and gets its own ADR). Successor [NEXT_PROMPT.md](./NEXT_PROMPT.md) replaced v1.2 → v1.3 targeting **M3.3 (OQ-031 resolution)** with the captured evidence + the 4 options baked in. Substrate: CONTEXT_INVENTORY v0.18 → v0.19; tests unchanged at 590 (flatten is a script, outside the mypy-`src`/pytest gate; black/isort clean).
- **v0.12 (2026-06-05 / M3.3 OQ-031 resolution)** — **OQ-031 RESOLVED with Option 1** (operator-led) on the M3.2 capture: Phase 1 accepts the PMA-bound leveraged-leg non-fill (QQL3 0/69 fills = 0% vs IBTM 6/6 = 100%; 2161 cap-binding 0; zero rejects/breaches/error-110) as a deployment characteristic — **no code change**, live behaviour Treasury-leg-dominated. Recorded as [ADR-052](./docs/decisions/DECISIONS.md#adr-052--phase-1-accepts-the-pma-bound-leveraged-leg-non-fill-oq-031-option-1); OQ-031 OPEN → RESOLVED-BY-ADR-052; G4 exit-criterion #1 ✓ MET. The leveraged-leg redesign deferred to Phase 2 as **OQ-032** (full design space incl. the leverage-preserving margin-on-a-1×-UCITS path the four OQ-031 options omitted — the *trilemma*: PRIIPs blocks US leveraged ETPs, PMA blocks UK ones, Cash blocks margin-leverage). `refined-by: ADR-052` backref added to ADR-043 + ADR-047 (QQL3 leg provisional). M3.3 sub-milestone marked resolved; **M3.4 (mixed-currency P&L reconciliation) is next**. Substrate: DECISIONS v0.22 → v0.23; OPEN_QUESTIONS v0.4 → v0.5; CONTEXT_INVENTORY v0.19 → v0.20; NEXT_PROMPT v1.3 → v1.4. No code change; tests unchanged at 590.
- **v0.13 (2026-06-05 / M3.4 mixed-currency P&L — found + fixed equity bug)** — M3.4 run live against IB Paper `DUP886336` under the streamlined-clean posture (operator-chosen). Reconciling the existing mixed state (USD cash + GBP-hedged sleeve) surfaced a real read-side defect: `AccountSnapshot.equity` read `NetLiquidationByCurrency[base_currency]` (GBP sleeve £902,839) instead of the consolidated `BASE` total (£1,003,886), dropping the ~£101k USD sleeve — invisible until the GBP→USD FX split the account. **Fixed** (`IBBroker._build_account_snapshot` BASE-primary; `_infer_base_currency` hardened to the unit-`ExchangeRate` signal) + mixed-currency regression test + new `scripts/probe_ib_account_ccy.py` raw-row diagnostic; DD-1 §2.8 v0.2 → v0.3 footnote. Re-confirmed live (equity £1,003,855). Bug-fix, **no ADR** (DD-1 already specified equity = total NAV). G4 exit-criterion #4 ✓ MET (wording amended "QQL3 position" → "USD exposure" per OQ-031/ADR-052). Tests 590 → 591; mypy/black/isort/lint-imports green. Pre-existing IG/shared black/isort drift cleared in a separate hygiene commit (`5166e20`; formatters pinned). **M3.5 (controlled Gateway stop/start drill + KB-7 stub) next.**
- **v0.14 (2026-06-05 / M3.5 chaos drill + KB-7 stub)** — Ran a controlled IB Gateway stop/start drill (`scripts/probe_ib_reconnect.py`; operator stopped + restarted the live paper Gateway) as the streamlined-clean substitute for the 23:45 ET restart. **Observed:** no native disconnect detection (`IBBroker.is_connected` stale-`True` while the socket drops — no `disconnectedEvent` handler); recovery via `disconnect()+connect()` works; the restart surfaced **IB error 10141** (paper-trading disclaimer) + a transient `clientId 1 already in use`; positions reconciled on reconnect. Native detect/auto-reconnect/continuous-reconciliation = M5 (REQUIREMENTS §5.7). Substrate: **KB-7 `failure_modes` MISSING → DRAFT v0.1** (FM-1); **INV-14 v0.9 → v0.10** (10141 promoted); new fixture `scripts/probe_ib_reconnect.py`. **G4 exit-criteria #5 (chaos) + #6 (Phase 2 stubs KB-7/KB-15/INV-8/INV-9 all DRAFT) ✓ MET.** Tests unchanged at 591 (manual fixture). **Remaining for M3 close: M3.6 (KB-2/KB-3 STABLE flip) → M3-close (RETRO-M3 + G4 report).**
- **v0.15 (2026-06-05 / M3 CLOSED — G4 PASSED)** — **M3.6** flipped KB-2 / KB-3 DRAFT v0.1.1 → STABLE v1.0 (Phase-1-surface scoped; stale DD-7/INV-14 refs fixed; 2161/Adaptive + ADR-040 + KB-7-reconnect findings folded in). **M3-close**: [RETRO-M3](./docs/retros/M3_retrospective.md) written + frozen (STABLE v1.0); **G4 gate PASSED** (all 10 exit criteria); NEXT_PROMPT v1.4 → v1.5 targeting the Phase-2 readiness-audit session (per §8.3.2 — session 2 of the M3→M4 boundary). **Phase 1 (M0 → M3) complete.** The leverage trilemma (OQ-032) + the VIX/TQQQ/VXX notebook are inputs to the Phase-2 plan-drafting session (session 3), not the close. Tests 591; all gates green (formatters pinned). The M3 arc: ADR-050/051 (unit-of-quote + tick-grid) → bounded M3.2 capture → ADR-052 (OQ-031 Option 1) + OQ-032 → M3.4 equity-sleeve fix → M3.5 chaos drill + KB-7 → M3.6 KB-2/KB-3 STABLE.
