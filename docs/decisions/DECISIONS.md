---
id: KB-10
title: Architectural Decision Records (ADRs)
status: DRAFT
owner: Claude record, Oleg approve
last_reviewed: 2026-06-05
version: 0.24
sources: []
depends_on:
  - KB-11   # OPEN_QUESTIONS — many ADRs resolve OQs
referenced_by:
  - REQUIREMENTS.md (rationale claims now traced to specific ADRs)
  - KB-5 strategy_taxonomy (Phase priority cites ADR-013)
  - KB-11 OPEN_QUESTIONS (resolution chains)
  - CONTEXT_PROTOCOL.md §5 (governs format)
---

# KB-10 — Architectural Decision Records

> **Format:** one big file for now (per [CONTEXT_INVENTORY §7](../../CONTEXT_INVENTORY.md#7-file-layout)) — split to `docs/decisions/adr/ADR-NNN-slug.md` when count exceeds usability or commit conflicts get painful.
>
> **Convention** ([CONTEXT_PROTOCOL §5](../../CONTEXT_PROTOCOL.md#5-decision--question-discipline)):
> - Each ADR is append-only. Reverse a decision via a new ADR with `supersedes: ADR-NNN`.
> - Status: `PROPOSED` · `ACCEPTED` · `SUPERSEDED-BY-ADR-MMM` · `DEPRECATED`.
> - Stable id `ADR-NNN`; numbering monotonic.

---

## Index

| Id | Title | Status | Date | Resolves |
|----|-------|--------|------|----------|
| [ADR-001](#adr-001--adopt-project-name-blive) | Adopt project name `blive` | ACCEPTED | 2026-04-26 | — |
| [ADR-002](#adr-002--adopt-ib_async-v21-as-wire-level-ib-driver) | Adopt `ib_async` v2.1+ as wire-level IB driver | ACCEPTED | 2026-04-26 | — |
| [ADR-003](#adr-003--borrow-nautilustrader-architecture-do-not-depend) | Borrow NautilusTrader architecture, do not depend | ACCEPTED | 2026-04-26 | — |
| [ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement) | Hexagonal ports/adapters with import-linter enforcement | ACCEPTED | 2026-04-26 | — |
| [ADR-005](#adr-005--single-process-single-asyncio-loop-kernel-for-v1) | Single-process, single-asyncio-loop kernel for v1 | ACCEPTED | 2026-04-26 | — |
| [ADR-006](#adr-006--sqlite-for-persistence-in-v1) | SQLite for persistence in v1 | ACCEPTED | 2026-04-26 | — |
| [ADR-007](#adr-007--in-process-event-bus-for-v1) | In-process event bus for v1 | ACCEPTED | 2026-04-26 | — |
| [ADR-008](#adr-008--riskengine-no-bypass-enforced-architecturally) | RiskEngine no-bypass enforced architecturally | ACCEPTED | 2026-04-26 | — |
| [ADR-009](#adr-009--crash-only-design) | Crash-only design | ACCEPTED | 2026-04-26 | — |
| [ADR-010](#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import) | Reuse btest's Factor / Signal / Portfolio engines by import | ACCEPTED | 2026-04-26 | — |
| [ADR-011](#adr-011--3-page-minimal-web-ui-mobile-and-oauth-deferred) | 3-page minimal web UI; mobile and OAuth deferred | ACCEPTED | 2026-04-26 | — |
| [ADR-012](#adr-012--parity-diagnostic-mandatory-daily-degraded-mode-if-broken) | Parity diagnostic mandatory daily; degraded mode if broken | ACCEPTED | 2026-04-26 | — |
| [ADR-013](#adr-013--v1-scope-etf-and-index-strategies-only) | v1 scope: ETF and index strategies only | ACCEPTED | 2026-04-26 | OQ-013 |
| [ADR-014](#adr-014--data-sources-via-clean-api-abstraction) | Data sources via clean API abstraction | ACCEPTED | 2026-04-26 | OQ-014 |
| [ADR-015](#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1) | ML training: live-trained eventually, static artefacts in v1 | ACCEPTED | 2026-04-26 | OQ-015, OQ-018 |
| [ADR-016](#adr-016--leverage-support-both-margin-financed-and-leveraged-etf-instruments) | Leverage: support both margin-financed and leveraged-ETF instruments | ACCEPTED | 2026-04-26 | OQ-016 |
| [ADR-017](#adr-017--live-data-hybrid-eodhd--ib-streaming-per-instrument-routing) | Live data: hybrid EODHD + IB streaming, per-instrument routing | ACCEPTED | 2026-04-26 | OQ-019 |
| [ADR-018](#adr-018--uk-equity-strategies-deferred-to-post-m8) | UK equity strategies deferred to post-M8 | ACCEPTED | 2026-04-26 | OQ-021 |
| [ADR-019](#adr-019--a3-archetype-generalises-to-other-leveraged-etf-pairs) | A3 archetype generalises to other leveraged-ETF pairs | ACCEPTED | 2026-04-26 | OQ-022 |
| [ADR-020](#adr-020--phase-1-nav-slice-510-of-total-cap-10) | Phase 1 NAV slice: 5–10% of total, cap 10% | ACCEPTED | 2026-04-26 | OQ-024 |
| [ADR-021](#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) | CAC ETF proxy: `CAC.PA` (Lyxor CAC 40 UCITS ETF) | SUPERSEDED-BY-ADR-043 | 2026-04-26 | OQ-025 |
| [ADR-022](#adr-022--tkan-artefact-freshness-window-30d-hard-21d-warning) | TKAN artefact freshness window: 30d hard, 21d warning | ACCEPTED | 2026-04-26 | OQ-026 |
| [ADR-023](#adr-023--tkan-artefact-path-and-refresh-ownership) | TKAN artefact path and refresh ownership | ACCEPTED | 2026-04-26 | OQ-027 |
| [ADR-024](#adr-024--add-session-retrospective-artefact-type) | Add session-retrospective artefact type | ACCEPTED | 2026-04-26 | — |
| [ADR-025](#adr-025--amend-context_protocol-83-with-milestone-close-and-phase-boundary-rules) | Amend CONTEXT_PROTOCOL §8.3 with milestone-close and phase-boundary rules | ACCEPTED | 2026-04-26 | — |
| [ADR-026](#adr-026--adopt-agentic-execution-layer-reduce-human-action-surface) | Adopt agentic-execution layer; reduce human action surface | ACCEPTED | 2026-04-26 | — |
| [ADR-027](#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero) | Sizer rounding policy: integer shares, truncate toward zero | ACCEPTED | 2026-04-27 | — |
| [ADR-028](#adr-028--strategy-config-shape-python-build_strategy--blive-yaml-overrides) | Strategy config shape: Python `build_strategy()` + blive YAML overrides | ACCEPTED | 2026-04-27 | — |
| [ADR-029](#adr-029--papermarketdata-as-marketdataport-adapter-fixture-backed-parquet) | `PaperMarketData` as `MarketDataPort` adapter, fixture-backed parquet | ACCEPTED | 2026-04-27 | — |
| [ADR-030](#adr-030--per-archetype-btest-interpreter-dispatch-amends-adr-010) | Per-archetype btest interpreter dispatch (amends ADR-010) | ACCEPTED | 2026-04-27 | OQ-030 |
| [ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) | Token-bucket rate limiter shape for IB adapters | PROPOSED | 2026-04-27 | — |
| [ADR-032](#adr-032--instrument-resolution-policy-blive-instrument--ib-contract) | Instrument resolution policy (`blive.Instrument` ↔ IB `Contract` / `ConID`) | PROPOSED | 2026-04-27 | — |
| [ADR-033](#adr-033--accountupdate-event-shape-and-sampling-cadence) | `AccountUpdate` event shape and sampling cadence | ACCEPTED | 2026-04-27 | — |
| [ADR-034](#adr-034--multi-broker-registry-pattern-extends-adr-004) | Multi-broker registry pattern (extends ADR-004) | ACCEPTED | 2026-04-27 | — |
| [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets) | Secrets handling discipline (`~/.blive/secrets/`) | ACCEPTED | 2026-04-27 | — |
| [ADR-036](#adr-036--ig-wire-level-driver-roll-our-own-httpx--asyncio-lightstreamer) | IG wire-level driver: roll-our-own httpx + asyncio Lightstreamer | ACCEPTED | 2026-04-27 | — |
| [ADR-037](#adr-037--instrumenttradability-field-spot--cfd--spread_bet) | `Instrument.tradability` field (spot / cfd / spread_bet) | ACCEPTED | 2026-04-27 | — |
| [ADR-038](#adr-038--ig-rate-limit-defaults-parameterise-adr-031) | IG rate-limit defaults (parameterise ADR-031) | ACCEPTED | 2026-04-27 | — |
| [ADR-039](#adr-039--phase-1-strategy-under-ig-bridge-cac-40-cfd) | Phase 1 strategy under IG bridge: CAC 40 CFD | ACCEPTED | 2026-04-27 | — |
| [ADR-042](#adr-042--session-bootstrap-files-agent-agnostic-pattern-for-l0-warm-up-entry-point) | Session-bootstrap files: agent-agnostic pattern for L0 warm-up entry point | ACCEPTED | 2026-05-02 | — |
| [ADR-043](#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2) | Phase 1 strategy switch: `triple_lev_sma_filter_dsl` (A3) replaces `tkan_v4_momentum_timing` (A2) | ACCEPTED | 2026-05-02 | — |
| [ADR-044](#adr-044--multi-instrument-pipeline-support-companion-to-adr-043) | Multi-instrument pipeline support (companion to ADR-043) | ACCEPTED | 2026-05-02 | — |
| [ADR-045](#adr-045--longshortportfolio-btest-dispatch-extends-adr-030) | LongShortPortfolio btest dispatch (extends ADR-030) | ACCEPTED | 2026-05-02 | — |
| [ADR-046](#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032) | IB resolver SMART routing for US equities (refines ADR-032) | ACCEPTED | 2026-05-02 | — |
| [ADR-047](#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043) | PRIIPs-compliant universe for Phase 1 A3 strategy (refines ADR-043) | ACCEPTED | 2026-05-03 | — |
| [ADR-048](#adr-048--lse-etf-smart-routing-discriminator-refines-adr-046) | LSE-ETF SMART routing discriminator (refines ADR-046) | ACCEPTED | 2026-05-03 | — |
| [ADR-049](#adr-049--ordertypeadaptive_mkt-for-ibalgo-adaptive-routing-empirical-pma-cap-finding) | `OrderType.ADAPTIVE_MKT` for IBALGO Adaptive routing + empirical PMA-cap finding | ACCEPTED | 2026-05-06 | — |
| [ADR-050](#adr-050--eodhd-vs-ib-unit-of-quote-conversion-at-sizing-time-hybrid-b-now--a-later-free-md-only) | EODHD-vs-IB unit-of-quote conversion at sizing time (Hybrid: B-now / A-later free-MD-only) | ACCEPTED | 2026-05-06 | — |
| [ADR-051](#adr-051--normalize-ib-order-prices-to-the-contract-tick-grid-at-submit-time) | Normalize IB order prices to the contract tick grid at submit time | ACCEPTED | 2026-06-05 | — |
| [ADR-052](#adr-052--phase-1-accepts-the-pma-bound-leveraged-leg-non-fill-oq-031-option-1) | Phase 1 accepts the PMA-bound leveraged-leg non-fill (OQ-031 Option 1) | ACCEPTED | 2026-06-05 | OQ-031 |
| [ADR-053](#adr-053--upgrade-to-python-312) | Upgrade to Python 3.12 | ACCEPTED | 2026-06-05 | — |

---

## ADR-001 — Adopt project name `blive`

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
A new project alongside `btest`, `harp`, `pt-liqadj` needs a name. The name must (1) communicate that this is the live counterpart to `btest`, (2) sit cleanly in directory listings next to siblings, (3) avoid major Python-tooling collisions, (4) be cheap to type and grep.

### Decision
Project is named **`blive`** — the `b-` prefix family pairs with `btest`, lowercase compact form matches the existing aesthetic (`btest`, `harp`), the `live` token states the operational intent.

### Alternatives Considered
1. **`helm`** — evocative ("at the helm of live trading"), but Kubernetes Helm collision pollutes search. Rejected.
2. **`pilot`** — clean metaphor, but Istio Pilot collision. Rejected.
3. **`rudder`** — clean, no major collision, but less obviously paired with `btest`. Weaker option.

### Consequences
- **Positive**: pairs visually with `btest`; trivial to find in shells; no major collision.
- **Negative**: minor collision with a Bilibili-livestream Python lib (`blive`, unrelated domain — low practical risk).
- **Follow-ups**: project root `C:\Users\olegr\PycharmProjects\blive\` created.

### Cross-References
- [REQUIREMENTS §18 naming note](../../REQUIREMENTS.md)

---

## ADR-002 — Adopt `ib_async` v2.1+ as wire-level IB driver

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
Interactive Brokers offers two API surfaces — TWS API (TCP socket, callback-driven `EWrapper`/`EClient`) and IBKR Web API (CPAPI, REST + WebSocket). The native Python `ibapi` is verbose and threading-awkward; the community `ib_async` (formerly `ib_insync`) is the de-facto modern wrapper. Maintenance transitioned to `ib-api-reloaded` after Ewald de Wit's death (March 2024).

### Decision
Use **`ib_async` v2.1+** (BSD-2) as the wire-level driver, instantiated only inside the `IBBroker` adapter. Pin `>=2.1,<2.2`. **Never imported above the adapter layer** ([ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement)).

### Alternatives Considered
1. **Native `ibapi`** — too low-level; reinvents what `ib_async` already does cleanly.
2. **IBKR Web API (CPAPI)** — 10 req/s, 6-min idle session death, IBKR Pro only; operationally worse than TWS for serious execution.
3. **Vendor-fork `ib_async`** — premature; depend on upstream first, fork only on stall.

### Consequences
- **Positive**: thin async wrapper, real maintenance cadence, modern asyncio + eventkit; minimal boilerplate.
- **Negative**: dependency on a community library that has already had one maintenance discontinuity; risk it stalls again.
- **Follow-ups**: monitor upstream release cadence; revisit OQ-004 if a stall recurs (vendor-fork plan).

### Cross-References
- [REQUIREMENTS §9.1](../../REQUIREMENTS.md), [REQUIREMENTS §10](../../REQUIREMENTS.md) (gotchas), KB-4 (MISSING).

---

## ADR-003 — Borrow NautilusTrader architecture, do not depend

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
NautilusTrader is the most architecturally aligned production framework: deterministic single-thread asyncio kernel, MessageBus, ExecutionEngine, RiskEngine, Cache, DataClient/ExecutionClient adapters, two-phase reconciliation. But it ships its own `Strategy` abstraction that would compete with `btest`'s DSL — the very thing `blive` is built around. It's also LGPL-3 with a Rust core that adds build complexity.

### Decision
Read NautilusTrader's [concept docs](https://nautilustrader.io/docs/latest/concepts/architecture/) **as our spec**; reimplement the patterns in Python code we own. Treat their reference implementation as a quality bar, not a dependency.

### Alternatives Considered
1. **Adopt NautilusTrader wholesale** — `Strategy` competes with `btest` DSL; LGPL-3 friction in legal review; Rust + Cython build adds a dimension to ops; not Python-native enough for our other goals.
2. **Ignore NautilusTrader** — would re-derive the wheel, slower and lower-quality.

### Consequences
- **Positive**: own all abstractions; pure Python; no LGPL/Rust dependencies; free to evolve.
- **Negative**: implementation effort is non-trivial; risk of subtle deviation from a battle-tested design (e.g. reconciliation has nuances easy to miss).
- **Follow-ups**: KB-4 frameworks_survey to document what specifically to harvest; RiskEngine + ExecutionEngine + Cache + reconciliation are the priority targets.

### Cross-References
- [REQUIREMENTS §9.2](../../REQUIREMENTS.md), KB-4 (MISSING).

---

## ADR-004 — Hexagonal ports/adapters with import-linter enforcement

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
We need clean separation between domain (Strategy, Sizer, RiskEngine, ExecutionEngine) and infrastructure (broker, market data, persistence, event bus, alerts) so multi-broker is feasible, tests don't depend on IB, and the domain stays portable as adapters evolve.

### Decision
**Hexagonal architecture (Ports & Adapters)**:
- Domain depends only on Ports: `BrokerPort`, `MarketDataPort`, `ClockPort`, `PersistencePort`, `EventBusPort`, `AlertPort`.
- Adapters implement Ports.
- **Enforced by import-linter**: a CI rule forbids any import from `blive.adapters.*` (or third-party broker libraries like `ib_async`) inside `blive.domain.*`. Violations fail CI.

### Alternatives Considered
1. **Layered MVC** — too coarse; doesn't capture the asymmetry between domain and venue adapter.
2. **Service-oriented (gRPC microservices)** — overkill for v1 single-host.
3. **Convention-only (no linter)** — relies on memory; will rot.

### Consequences
- **Positive**: testable; swappable; clean to add Alpaca/Tradier later; refactor risk lowered.
- **Negative**: more abstraction surface initially; more types to maintain; a hard onboarding step for newcomers.
- **Follow-ups**: import-linter config in `pyproject.toml` from M0; CI rule from M0; ADR-008 RiskEngine no-bypass uses the same enforcement.

### Cross-References
- [REQUIREMENTS §4 principle 1, §7.1, §7.2](../../REQUIREMENTS.md).

---

## ADR-005 — Single-process, single-asyncio-loop kernel for v1

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
The engine handles concurrent market-data subscriptions, order events, risk checks, and a web UI. Concurrency model choices: single asyncio loop, multi-thread, multi-process. Each has trade-offs in determinism, debugability, throughput.

### Decision
**Single Python process running a single asyncio event loop in the domain layer.** Adapters may use threads internally (e.g. `ib_async`'s reader thread) but must hand off via async queues so domain code observes a deterministic event stream.

### Alternatives Considered
1. **Multi-process per strategy** — operational complexity for v1; defer per OQ-005.
2. **Threading throughout** — race conditions, debugging hell, GIL still a bottleneck.
3. **Multi-loop** — coordination complexity; the deterministic-replay benefit of a single loop is lost.

### Consequences
- **Positive**: deterministic event ordering ⇒ backtest-live parity tractable; simpler debugging; one GIL is fine for our event volume (≤ 50 instruments, < 1000 events/s sustained).
- **Negative**: ceiling on throughput; CPU-heavy strategies may pin a core.
- **Follow-ups**: revisit OQ-005 if any strategy demands > 50% of a core or has incompatible Python deps.

### Cross-References
- [REQUIREMENTS §4 principle 5, §7.1](../../REQUIREMENTS.md), [OQ-005](OPEN_QUESTIONS.md#oq-005--strategy-isolation-one-process-per-strategy-or-one-process-for-all).

---

## ADR-006 — SQLite for persistence in v1

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
The crash-only design (ADR-009) requires a durable event log + periodic snapshots + state queries. Database choice trades off operational complexity vs. concurrency vs. analytical reporting.

### Decision
**SQLite for v1.** Single file, easy backup, well-understood, plenty fast at our event rate. Migration path to Postgres documented but not built.

### Alternatives Considered
1. **Postgres** — concurrent writers, network access, more ops; overkill until HA is needed.
2. **DuckDB** — analytics-friendly columnar; less battle-tested for OLTP-style append; revisit if reporting workloads dominate.
3. **Append-only files (NDJSON)** — simple but loses indexed queries for the UI.

### Consequences
- **Positive**: zero external service; backup = file copy; well-understood failure modes.
- **Negative**: single-host write only; no HA; large transactions hold a global lock.
- **Follow-ups**: revisit OQ-003 if event throughput > 1000/s sustained or multi-host writes required.

### Cross-References
- [REQUIREMENTS §11](../../REQUIREMENTS.md), [OQ-003](OPEN_QUESTIONS.md#oq-003--persistence-sqlite-vs-postgres-vs-duckdb).

---

## ADR-007 — In-process event bus for v1

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
The kernel needs pub/sub between actors (Strategy emits target_weights → Sizer → RiskEngine → ExecutionEngine; market data → Strategy; broker events → Cache → Strategy). The bus is the spine of the engine.

### Decision
**In-process asyncio queues** for v1. Implement `EventBusPort` with an in-memory implementation. Redis Streams remains an opt-in adapter for HA setups later.

### Alternatives Considered
1. **Redis Streams from M1** — durable across process restart, multi-process-friendly, but introduces an external service dependency for v1.
2. **Kafka** — overkill for our scale.
3. **ZeroMQ** — multi-process complexity for v1.

### Consequences
- **Positive**: simple, low latency, no external service; matches single-process kernel (ADR-005).
- **Negative**: events lost between adapter receipt and persistence append on crash; mitigation is to persist before publishing on the bus.
- **Follow-ups**: revisit OQ-002 if HA / multi-process required.

### Cross-References
- [REQUIREMENTS §7.1, §11](../../REQUIREMENTS.md), [OQ-002](OPEN_QUESTIONS.md#oq-002--event-bus-in-process-vs-redis-streams-from-m1).

---

## ADR-008 — RiskEngine no-bypass enforced architecturally

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
Risk checks must apply to every order, every time. Any pattern with an "emergency override" or "fast path" creates a footgun that will eventually fire; many trading-system disasters have followed precisely that shape.

### Decision
The RiskEngine sits between the Sizer and the ExecutionEngine on the only code path that produces orders. **Strategy code has no import path to the ExecutionEngine.** Architecturally enforced (ADR-004 import-linter rule extended): `blive.domain.strategies.*` and `blive.domain.sizing.*` cannot import `blive.domain.execution.*` directly; `blive.domain.execution.*` accepts only orders coming from `blive.domain.risk.RiskEngine.approve(...)`.

### Alternatives Considered
1. **Decorator pattern** — easier to forget the decorator on a new code path; not enforced.
2. **Permission flag on Order** — easier to set wrong; debugging-friendly is a footgun.
3. **Fast-path "skip risk" override** — never; correctness > microseconds for our scale.

### Consequences
- **Positive**: every order is risk-checked; impossible to forget by accident; CI catches bypass attempts.
- **Negative**: harder to do "raw order" testing; tests that need to bypass must mock the RiskEngine.
- **Follow-ups**: import-linter rule wired by M0; the kill-switch is itself a RiskEngine check (so no special-case bypass even for shutdown).

### Cross-References
- [REQUIREMENTS §4 principle 2, §5.5, §7.1](../../REQUIREMENTS.md).

---

## ADR-009 — Crash-only design

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
The engine must recover from process crashes (OOM, segfault, kill, host reboot) and from clean restarts. Any "soft restart" code path that differs from cold start adds latent bug surface — and such bugs only fire under stress.

### Decision
**Crash-only design.** Every domain event is appended to a durable log before being published on the bus. Restart path = cold-start path:
1. Load latest snapshot.
2. Replay log tail.
3. Reconcile against venue (open orders, positions, account values; venue is authoritative).
4. Enter `paused` state — refuse new submissions.
5. **Require explicit human resume** via UI / REST.

No auto-resume after unclean shutdown.

### Alternatives Considered
1. **Graceful shutdown only** — easy to skip in real crash; doesn't help.
2. **Auto-resume after crash** — dangerous; could re-submit duplicate orders; the same code path that handles crash recovery is then not regularly exercised.

### Consequences
- **Positive**: simple recovery model; one code path; recovery is regularly exercised every restart.
- **Negative**: every restart requires human attention to clear pause state — no truly hands-off restart.
- **Follow-ups**: reconciliation engine M5; pause-state UI affordance M6; chaos tests for kill-mid-trade scenarios.

### Cross-References
- [REQUIREMENTS §4 principle 3, §5.7, §6.2](../../REQUIREMENTS.md).

---

## ADR-010 — Reuse btest's Factor / Signal / Portfolio engines by import

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
Strategies are authored in `btest`'s DSL. `blive` evaluates factors / signals / portfolio targets in live. Two paths: import `btest` as a library, or fork the relevant modules into `blive`. The first preserves backtest-live parity by construction; the second risks drift.

### Decision
**Import `btest` as a library.** `blive` depends on a pinned `btest` version and re-exports `FactorEngine`, `SignalEngine`, `PortfolioEngine` for use in the live kernel. Fork specific modules **only** if upstream changes break us faster than we can absorb.

### Alternatives Considered
1. **Fork the modules into `blive`** — duplication; maintenance burden; near-certain drift.
2. **Reimplement** — would reintroduce drift between backtest and live; the parity contract (ADR-012) would be much harder to keep.

### Consequences
- **Positive**: single source of truth for strategy semantics; backtest-live parity by construction; new btest factors / signals automatically usable in live.
- **Negative**: `btest` must remain installable and stable; coordinated releases needed if breaking changes happen; CI must check `btest` import works.
- **Follow-ups**: btest version pin discipline; CI smoke-imports; revisit OQ-009 if breakage rate too high.

### Cross-References
- [REQUIREMENTS §4 principle 4, §5.1, §8](../../REQUIREMENTS.md), [OQ-009](OPEN_QUESTIONS.md#oq-009--btest-engine-reuse-import-as-library-or-fork-relevant-modules).

---

## ADR-011 — 3-page minimal web UI; mobile and OAuth deferred

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
The control plane must let an operator start/stop strategies, see global state, hit a kill switch, and view logs. A full multi-page app is overscope for v1; CLI-only is operationally awkward.

### Decision
**Three pages** + REST + SSE backend:
1. **Dashboard** — all strategies, global account stats, kill-switch button at top.
2. **Strategy** (per-strategy detail) — equity curve, positions, orders, fills, log tail, parameter overrides form.
3. **System** — connections, reconciliation status, version, alert history, backup status.

Auth: shared bearer token + TLS for v1.

### Alternatives Considered
1. **Full multi-page web app** — overscope; slower to ship; more bugs.
2. **CLI only** — operational friction in real use.
3. **Native mobile app** — out of scope.
4. **OAuth/SSO** — overkill for single-operator; revisit OQ-008.

### Consequences
- **Positive**: small surface; fast to ship; easy to test end-to-end manually.
- **Negative**: limited usability beyond bare essentials; no mobile-friendly view; bearer-token auth is single-secret.
- **Follow-ups**: CLI from M6 (OQ-011); OAuth post-M8 if multi-operator emerges (OQ-008).

### Cross-References
- [REQUIREMENTS §5.8](../../REQUIREMENTS.md), [OQ-008](OPEN_QUESTIONS.md#oq-008--ui-auth-shared-secret-vs-local-only-vs-oauth), [OQ-011](OPEN_QUESTIONS.md#oq-011--cli-alongside-web-ui).

---

## ADR-012 — Parity diagnostic mandatory daily; degraded mode if broken

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg (with Claude)
- **supersedes:** none

### Context
Backtest-live parity is one of the project's load-bearing claims (ADR-010 makes it tractable; this ADR makes it observable). Without measurement, drift is invisible, and the parity contract becomes aspirational instead of provable.

### Decision
- **Daily** parity diagnostic runs automatically: take realised fills + EOD positions + EOD account values, replay through `btest`'s vectorised engine starting from yesterday's positions, report `(realised_pnl, simulated_pnl, residual_bps)` per strategy.
- Aggregate residual outside the envelope (REQUIREMENTS §8 — provisional ±15 bps over 5d) raises a `ParityBreach` alert.
- **Continuous** parity (parallel `btest` replica running in lock-step) added in M7+.
- If the diagnostic itself fails (btest import error, etc.), the engine enters **degraded mode** — does not crash, but signals a `ParityDiagnosticFailed` alert and continues trading. Crashing here would weaponise the diagnostic against availability.

### Alternatives Considered
1. **Weekly parity** — drift accumulates too long.
2. **Continuous-only** — operationally heavier in v1.
3. **Optional parity** — would inevitably get disabled, then rot.

### Consequences
- **Positive**: drift is observable, attributable, alertable; parity contract becomes operational, not aspirational.
- **Negative**: parity diagnostic is now load-bearing infrastructure; chaos-test it in M5+.
- **Follow-ups**: tolerance bands TBD per OQ-012; chaos-test fault for diagnostic failure; M7 continuous parity.

### Cross-References
- [REQUIREMENTS §4 principle 8, §8](../../REQUIREMENTS.md), [OQ-012](OPEN_QUESTIONS.md#oq-012--parity-tolerance-bands-are-8-numbers-right).

---

## ADR-013 — v1 scope: ETF and index strategies only

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** [OQ-013](OPEN_QUESTIONS.md#oq-013--which-strategies-are-funded-for-v1-and-what-nav-slice)

### Context
KB-5 catalogues seven `btest` strategies plus active research, spanning A1 (single-name SP500 cross-sectional), A1a (cross-index L/S), A2 (single-instrument timing), A3 (multi-ETF SMA-filter with safe-haven park). Building all simultaneously overstretches the engine in M0–M8; without a focus decision, scope drifts.

### Decision
**v1 scope is ETF and index strategies only.** Single-name SP500 cross-sectional strategies (`xsec_momentum_long_short_sp500`, `harp_quarterly_momentum`, `tiny_momentum_ls`) are **catalogued but deferred to post-M8**.

Phased priority codified:

| Phase | Milestone | Strategy | Archetype |
|-------|-----------|----------|-----------|
| 1 | M3 (IB Paper) | `tkan_v4_momentum_timing` 1× via tradable ETF proxy (CAC-tracking) | A2 |
| 2 | post-M5 | `triple_lev_sma_filter_dsl` (TQQQ / TMF / IEF) | A3 |
| 3 | post-M7 | `lagging_indecies` via index ETF proxies (SPY, EFA, EWJ, EWG, EWU, IEMG) | A1a |
| 4+ | post-M8 (live) | A2 leveraged variants; A3 generalised pairs (per ADR-019); UK equities (per ADR-018) | mixed |

Design intent: **complexity ramps A2 → A3 → A1a so the engine learns simple flows first**; A1 single-name is the highest-friction archetype and parked behind M8.

### Alternatives Considered
1. **Cover all archetypes from v1** — engine complexity climbs too fast; risk of multiple half-baked archetypes.
2. **Single-archetype v1 (A2 only)** — too narrow; can't validate A3 patterns or multi-venue (A1a).

### Consequences
- **Positive**: focused engine evolution; each phase exercises a new dimension of complexity (single-instrument → paired-leg → multi-currency / multi-calendar).
- **Negative**: A1 single-name use cases parked for >12 months; user appetite may shift.
- **Follow-ups**: NAV slice per phase still TBD (OQ-013 sub-question); revisit phasing if any phase delivers ≪ expected.

### Cross-References
- [KB-5 §3 strategies table](../kb/strategy_taxonomy.md#3-currently-active--in-research-strategies), [KB-5 §7 NAV Slice & Priorities](../kb/strategy_taxonomy.md#7-nav-slice--priorities), [REQUIREMENTS §1, §15](../../REQUIREMENTS.md).

---

## ADR-014 — Data sources via clean API abstraction

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** [OQ-014](OPEN_QUESTIONS.md#oq-014--data-source-switch-from-sfera-bloomberg-to-live-equivalent)

### Context
`btest` strategies use heterogeneous historical sources today: `parquet://equities/sp500_daily`, `sfera://bbgidx/index_prices` (Bloomberg via sfera-db), `yf://`, `fred://`. Live `blive` adds `eodhd://` for warm-up + `ib://` for streaming. Without a clean abstraction, strategy code couples to source — losing portability and testability.

### Decision
**All data sources implement the existing `DataSource` protocol** from `btest/data/sources/registry.py`. Each source is a pluggable adapter. Strategies declare the URL (`parquet://`, `sfera://`, `eodhd://`, `ib://`, `yf://`, `fred://`); the registry resolves to the right adapter. **No source-specific hard-coding above the adapter layer.**

### Alternatives Considered
1. **Migrate everything to EODHD only** — disregards existing strategies; loses Bloomberg-quality index data for A2.
2. **Hard-code per strategy** — violates ADR-004 hexagonal principle; couples strategy code to infrastructure.

### Consequences
- **Positive**: existing `btest` strategies work in `blive` unchanged; new sources are additive; testing uses mock or parquet sources without IB/EODHD network calls.
- **Negative**: must implement adapters per source we use; some sources (sfera-Bloomberg) require enterprise access already arranged in `btest`.
- **Follow-ups**: implement `eodhd://` adapter (M2); implement `ib://` adapter for live streaming (M2); ensure existing `parquet://`, `yf://`, `fred://` adapters import cleanly into `blive`.

### Cross-References
- [REQUIREMENTS §5.2, §7.2](../../REQUIREMENTS.md), [KB-5 §6](../kb/strategy_taxonomy.md#6-data-source-mapping).

---

## ADR-015 — ML training: live-trained eventually, static artefacts in v1

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** [OQ-015](OPEN_QUESTIONS.md#oq-015--ml-model-training-in-process-or-static-artefacts), [OQ-018](OPEN_QUESTIONS.md#oq-015--oq-018--ml-model-training-in-process-or-static-artefacts-artefact-lifecycle)

### Context
A2 strategies (`index_directional`, `tkan_v4_momentum_timing`) use ML models — TKAN networks producing `pred_cache.pkl` artefacts via `TKAN_v4_train.py`. Two architectural questions: (1) does `blive` train the models in-process during live, (2) where do trained artefacts live in prod and when do they stale?

### Decision
- **For v1**: `blive` consumes **static artefacts** produced offline by `btest` (e.g. `pred_cache.pkl`). The artefact loader is in scope; the trainer is not.
- **Architecturally**: assume that ML models will be **live-trained eventually** — the loader interface is designed so the artefact source can be swapped to a live trainer without redesign.
- **Operations**: strategy spec records artefact path, build hash, last-trained timestamp; `RiskEngine` enforces a configurable freshness window with `StaleModelArtefact` alerts when exceeded.

### Alternatives Considered
1. **Include online training in v1** — overscope; ML training is a separate concern with separate failure modes (GPU, hyperparameter sensitivity, training-set drift).
2. **Static artefacts forever** — closes off future evolution; an artefact-only design tends to bake in assumptions hard to undo.

### Consequences
- **Positive**: clean separation between training and inference; v1 stays focused on execution.
- **Negative**: artefact lifecycle is operationally manual in v1 — operator reruns trainer in `btest`, copies artefact, restarts strategy; this is friction.
- **Follow-ups**: artefact freshness window default TBD; M8+ retraining pipeline (online trainer behind the loader interface) is its own project.

### Cross-References
- [KB-5 §2 A2](../kb/strategy_taxonomy.md#a2--single-instrument-market-timing-xs-universe-daily), [REQUIREMENTS §5.12 strategy versioning](../../REQUIREMENTS.md).

---

## ADR-016 — Leverage: support both margin-financed and leveraged-ETF instruments

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** [OQ-016](OPEN_QUESTIONS.md#oq-016--synthetic-leverage-via-margin-or-only-via-leveraged-etf-instruments)

### Context
Strategies achieve leverage two ways: (a) margin-finance the underlying (e.g. hold CACT at 2× by borrowing half via IB margin, paying ESTER spread), or (b) trade a leveraged ETF (e.g. TQQQ for 3× QQQ, where the leverage is internal to the fund and rebalanced daily). Different cost structures, different parity envelopes.

### Decision
**Engine supports both leverage paths.** Per-strategy declaration:

- **Margin-financed leverage**: strategy declares `target_leverage > 1` on an underlying instrument; `blive` borrows via IB margin and tracks `FinancingCost` (e.g. ESTER + spread for European, SOFR + spread for US) against the financed half.
- **Leveraged-ETF instruments**: strategy directly trades a 2×/3× ETF (TQQQ, TMF, SPXL, UPRO, SOXL); financing decay is internal to the ETF and not modelled separately by `blive`. Parity tolerance must absorb the daily-reset slippage characteristic of leveraged ETFs.

### Alternatives Considered
1. **Margin only** — disregards A3 leveraged-ETF strategies; can't run `triple_lev_sma_filter_dsl`.
2. **Leveraged-ETF only** — disregards A2 strategies that prefer underlying + margin (e.g. `tkan_v4_momentum_timing` 2× variant uses ESTER-financed CACT).

### Consequences
- **Positive**: `blive` runs both classes of strategy without translation; user retains choice per strategy.
- **Negative**: Sizer + RiskEngine must understand both leverage mechanisms; cost models differ; parity envelopes differ per leverage path.
- **Follow-ups**: parity calibration per leverage path (OQ-012); document the choice in strategy spec template.

### Cross-References
- [KB-5 §2 (A2 leveraged variants, A3)](../kb/strategy_taxonomy.md#2-archetype-catalogue), [KB-5 §8](../kb/strategy_taxonomy.md#8-live-lift-implications-for-blive-requirements-hooks).

---

## ADR-017 — Live data: hybrid EODHD + IB streaming, per-instrument routing

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** [OQ-019](OPEN_QUESTIONS.md#oq-019--live-data-eodhd-real-time-vs-ib-streaming-vs-hybrid)

### Context
Live market data has two viable sources for `blive`: EODHD All-in-One (real-time / delayed depending on subscription tier; 200+ exchanges; not necessarily lowest latency) and IB streaming (`reqMktData` / `reqTickByTickData`; lowest latency to the venue we trade on; subscription-tier-gated per exchange).

### Decision
**`MarketDataPort` admits multiple concurrent providers; routing is per-instrument** (and possibly per-frequency). Default mapping pending calibration:

- **IB streaming** for instruments traded via IB (lowest latency to the venue we trade on).
- **EODHD real-time / delayed** for instruments not in our IB market-data subscription tier (broader coverage at modest latency cost).
- **EODHD historical** for warm-up of factor lookbacks and backtest replay.

The architecture forbids hard-wiring a single provider above the adapter layer (already a CONTEXT_PROTOCOL §2.2 / ADR-004 consequence).

### Alternatives Considered
1. **IB only** — coverage gaps for instruments we don't subscribe to; outside-RTH data limits.
2. **EODHD only** — adds latency vs. direct IB; might miss intraday events that IB delivers more reliably.

### Consequences
- **Positive**: best-of-both coverage; broader instrument support than either alone; degradation is graceful (fall back to EODHD if IB drops a stream).
- **Negative**: more adapter code; routing config is a new locus where bugs hide; subscription accounting (which exchanges paid on which provider) becomes operational concern.
- **Follow-ups**: per-instrument routing rules TBD; default mapping pending observed performance in M2; subscription-tier mismatch alerts.

### Cross-References
- [REQUIREMENTS §5.2](../../REQUIREMENTS.md), [KB-5 §6](../kb/strategy_taxonomy.md#6-data-source-mapping).

---

## ADR-018 — UK equity strategies deferred to post-M8

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** [OQ-021](OPEN_QUESTIONS.md#oq-021--uk-equity-strategies-in-scope-post-m8)

### Context
Oleg is UK-based; SMIM research includes `equities/smim/UK-LC` (large cap) and `UK-MC` (mid cap) universes. UK live trading is operationally relevant and politically sympathetic. But adding UK in v1 broadens scope before US ETF/index trading is solid.

### Decision
**UK-listed cash equities are in scope later (post-M8) but deferred for v1.** Initial focus is US ETFs/indices and European indices via tradable ETF proxies. Likely entry post-M8: a UK-only A1 cross-sectional from the SMIM research universe (`UK-LC` or `UK-MC`).

### Alternatives Considered
1. **Include UK from M3** — broadens scope before US is solid; multi-venue / multi-currency in M3 is too much new at once.
2. **Drop UK entirely** — closes off relevant home market; mismatch with user's research base.

### Consequences
- **Positive**: scope discipline; US-first stabilises engine before multi-venue live; UK is a known follow-up not a forgotten one.
- **Negative**: UK trades remain manual / btest-only until post-M8; user's home-market alpha sits unrealised for >12 months.
- **Follow-ups**: UK strategy spec deferred to post-M8 planning; KB-13 companion_projects clarifies SMIM relationship.

### Cross-References
- [KB-5 §5 asset classes](../kb/strategy_taxonomy.md#5-asset-class-coverage-current-and-near-future), [KB-5 §7 Phase 4+](../kb/strategy_taxonomy.md#7-nav-slice--priorities), KB-13 (MISSING).

---

## ADR-019 — A3 archetype generalises to other leveraged-ETF pairs

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** [OQ-022](OPEN_QUESTIONS.md#oq-022--generalise-a3-to-other-leveraged-etf-pairs)

### Context
`triple_lev_sma_filter_dsl` is one A3 instance (TQQQ / TMF / IEF). The pattern — risk-on legs with a safe-haven park, SMA-200 trend filter with hysteresis — is reusable across many leveraged-ETF families. If we treat A3 as TQQQ-specific, we close off pattern reuse.

### Decision
**A3 is parameterised by `(risk_on_pair, safe_haven_park, trend_filter, hysteresis)`.** `triple_lev_sma_filter_dsl` is one instance; future instances on the roadmap include SOXL / SQQQ (semis), UPRO / SPXU (broad index), cross-sector (XLK / XLF style). Concrete generalisation work is **deferred to Phase 4+ (post-M8)** per ADR-013, but engine code from M5 must be generic — no TQQQ/TMF/IEF specialisations baked into the engine.

### Alternatives Considered
1. **A3 = only TQQQ/TMF/IEF specific** — closes off pattern reuse; specialisation creep into engine code.
2. **Build a full generalised framework now** — premature; first prove A3 with one instance.

### Consequences
- **Positive**: pattern reuse explicit; future strategies use the same engine paths; no engine specialisation around three tickers.
- **Negative**: engine code must remain generic from day one even when only one instance is in flight (slightly more abstraction than minimum).
- **Follow-ups**: factor out A3 blueprint helpers in M5; concrete generalisation post-M8.

### Cross-References
- [KB-5 §2 A3](../kb/strategy_taxonomy.md#a3--multi-instrument-trend-filter-with-safe-haven-park-s-universe-daily), [KB-5 §7 Phase 4+](../kb/strategy_taxonomy.md#7-nav-slice--priorities).

---

## ADR-020 — Phase 1 NAV slice: 5–10% of total, cap 10%

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** [OQ-024](OPEN_QUESTIONS.md#oq-024--nav-slice-for-the-phase-1-strategy)

### Context
[ADR-013](#adr-013--v1-scope-etf-and-index-strategies-only) selects `tkan_v4_momentum_timing` 1× as the Phase 1 strategy. Phase 1 is a technology-validation phase, not an alpha-capture phase. The NAV slice committed to it should reflect that posture: large enough to observe meaningful behaviour, small enough that the entire phase can fail without breaking the account.

### Decision
Allocate **5–10% of total account NAV** to the Phase 1 strategy, with a **hard cap of 10%**. Combined with RC-07 (single-name notional ≤ 8% of strategy NAV from [INV-4](../inv/risk_checks.md)), this caps any single position at ≤ 0.8% of total NAV.

### Alternatives Considered
1. **Larger slice (20–30%)** — premature; correctness has not been validated in live conditions; an undetected risk-engine bug at this scale could be costly.
2. **Smaller slice (≤ 1%)** — too small to observe meaningful P&L behaviour or to detect risk-engine misbehaviour at scale; calibration would be uninformative.
3. **Variable slice keyed to strategy confidence** — out of v1 scope; an interesting Phase 4+ idea.

### Consequences
- **Positive:** Phase 1 cannot break the account. Risk-engine misbehaviour, if it occurs, has bounded impact.
- **Negative:** observed P&L noise floor is large relative to signal; calibration of risk thresholds and parity envelope will be coarse.
- **Follow-ups:** scale up at Phase 2/3 entry once parity envelope and runtime behaviour are calibrated; revisit at G4 gate.

### Cross-References
- [INV-4 RC-07](../inv/risk_checks.md) — per-name notional cap.
- [TASK_REGISTRY](../../TASK_REGISTRY.md) — Phase 1 plan.

---

## ADR-021 — CAC ETF proxy: `CAC.PA` (Lyxor CAC 40 UCITS ETF)

- **status:** SUPERSEDED-BY-ADR-043 (was ACCEPTED 2026-04-26 → 2026-05-02)
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **superseded by:** [ADR-043](#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2) — Phase 1 strategy switched from A2 (`tkan_v4_momentum_timing` on `CAC.PA`) to A3 (`triple_lev_sma_filter_dsl` on TQQQ/TMF/IEF). The CAC.PA Instrument + Yahoo-suffix translation per ADR-041 + DD-7 §3 / §3.1 substrate stay durable (CAC.PA is wire-validated end-to-end at `M2-IB.4a-happy-cacpa` and may revive as a future strategy / comparison instrument); only the *Phase 1 strategy designation* moves.
- **resolves:** [OQ-025](OPEN_QUESTIONS.md#oq-025--which-cac-etf-proxy-for-the-phase-1-strategy)

### Context
The btest research strategy `tkan_v4_momentum_timing` operates on `CACT` (CAC 40 Total Return index). CAC indices are not directly tradable; Phase 1 requires a tradable ETF proxy. Most CAC ETFs are price-return; the model was trained on CACT (TR), so any price-return proxy introduces a known parity divergence.

### Decision
Use **`CAC.PA` (Lyxor CAC 40 UCITS ETF, distributing share class)** as the tradable proxy on Euronext Paris (XPAR). Price-return tracking; the dividend-tracking gap (≈3–4% annual yield) is absorbed into the Phase 1 parity envelope and explicitly logged.

### Alternatives Considered
1. **`CACX.PA` (Amundi CAC 40 ETF, accumulating share class)** — closer to total-return tracking, but lower liquidity. Worth revisiting if liquidity proves adequate.
2. **iShares CAC 40 ETF** — less liquid than the Lyxor.
3. **Retrain TKAN model on `CAC.PA` price-return history** — would close the parity gap; out of v1 scope per [ADR-015](#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1).
4. **CAC 40 future contract** — out of v1 scope (no futures support yet); would close the price-vs-TR gap differently.

### Consequences
- **Positive:** tradable proxy obtained; Phase 1 can run on a real exchange.
- **Negative:** ≈3–4% annual dividend gap manifests as parity divergence vs. the btest CACT reference; documentation-only at M3, but feeds into M7 parity diagnostic design.
- **Follow-ups:** at M3 close, evaluate whether the divergence is within acceptable parity envelope or whether retraining on CAC.PA history is warranted.

### Cross-References
- [KB-5 §3](../kb/strategy_taxonomy.md) — strategies table.
- [ADR-015](#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1) — training out of v1 scope.

---

## ADR-022 — TKAN artefact freshness window: 30d hard, 21d warning

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** [OQ-026](OPEN_QUESTIONS.md#oq-026--tkan-artefact-freshness-window-default)

### Context
[INV-4 RC-12](../inv/risk_checks.md) requires a `risk.max_model_artefact_age_days` threshold; [ADR-015](#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1) left the default unspecified. The TKAN model drifts as market regime changes; staleness becomes a real risk over weeks. Phase 1 needs a number.

### Decision
- **Hard threshold (RC-12 block):** 30 days. After 30 days, RiskEngine refuses to size new orders for any strategy whose artefact is older.
- **Warning alert:** 21 days. At 21 days, an `ArtefactFreshnessWarning` event fires.

Conservative for a daily-frequency strategy where the model retrains in minutes to hours offline.

### Alternatives Considered
1. **7 days hard** — too aggressive; would cause unnecessary blocks during normal retraining cycles, since the operator may go a week without refreshing.
2. **90 days hard** — too lax; the signal will have drifted substantially in three months in any non-stationary market.
3. **No threshold (warning only)** — violates ADR-015's commitment to staleness alerts as a control.

### Consequences
- **Positive:** operator is forced to refresh at least monthly; warning at week 3 gives a week of slack to act.
- **Negative:** if the operator is unavailable for > 30 days, the strategy halts on its own — a feature, but worth knowing.
- **Follow-ups:** re-tune from observed retraining cadence after first month of live (paper) operation; revisit at G4 gate.

### Cross-References
- [INV-4 RC-12](../inv/risk_checks.md) — model artefact freshness check.
- [ADR-015](#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1) — static artefact policy.

---

## ADR-023 — TKAN artefact path and refresh ownership

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** [OQ-027](OPEN_QUESTIONS.md#oq-027--tkan-artefact-prod-location-and-retraining-ownership)

### Context
[ADR-015](#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1) left artefact storage location and retraining ownership open. Phase 1 needs concrete answers.

### Decision
- **Path scheme:** `~/.blive/artefacts/{strategy_id}/{model_name}/pred_cache.pkl`. Example: `~/.blive/artefacts/tkan_v4_momentum_timing/tkan_v4/pred_cache.pkl`.
- **Hash:** SHA256 of the artefact recorded in the strategy spec snapshot per [REQUIREMENTS §5.12](../../REQUIREMENTS.md).
- **Refresh:** **manual**. Operator runs the retraining script in btest (`research/Index Directional/signals/tkan/versions/v4/TKAN_v4_train.py`) and then `scripts/refresh_artefact.py` (an M2 deliverable) which copies, checksums, and records the new artefact in blive.
- **No auto-train pipeline in v1**, consistent with [ADR-015](#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1).

### Alternatives Considered
1. **Centralised artefact registry (S3 / database)** — premature for v1; single-operator setting does not need it.
2. **Auto-retrain on staleness** — violates [ADR-015](#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1).
3. **Path under `/etc/blive/`** — less convenient for single-user development; better suited to a multi-tenant host (out of v1).

### Consequences
- **Positive:** simple operational model; works for single-operator setting; no infrastructure dependencies.
- **Negative:** multi-host deployment requires syncing the artefact directory — not a Phase 1 concern but flagged for Phase 2+.
- **Follow-ups:** `scripts/refresh_artefact.py` is an M2 deliverable per [TASK_REGISTRY](../../TASK_REGISTRY.md); auto-pipeline is post-M8 if ever.

### Cross-References
- [ADR-015](#adr-015--ml-training-live-trained-eventually-static-artefacts-in-v1) — static artefacts in v1.
- [REQUIREMENTS §5.12](../../REQUIREMENTS.md) — strategy spec versioning.
- [TASK_REGISTRY](../../TASK_REGISTRY.md) M2 — `refresh_artefact.py` deliverable.

---

## ADR-024 — Add session-retrospective artefact type

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** —

### Context
Milestone close benefits from a structured retrospective capturing delivered-vs-plan, surprises, ADRs / OQs raised, substrate transitions, effort, and recommendations for the next milestone. Without a dedicated artefact type, this content is scattered across chat history — non-substrate, ephemeral, lost to the next session. The CONTEXT_INVENTORY §1 hierarchy does not currently have a layer for backward-looking records.

### Decision
Introduce a new artefact category **RETRO**, with id form `RETRO-M{N}`, stored at `docs/retros/M{N}_retrospective.md`. Standard frontmatter; status lifecycle simplified to `DRAFT → STABLE` only (retros are frozen historical records — no `STALE` or `DEPRECATED` transitions). Template at `docs/retros/_template.md`.

A retrospective is written at every milestone close, by the agent at end of the closing implementation session, per the protocol amendment in [ADR-025](#adr-025--amend-context_protocol-83-with-milestone-close-and-phase-boundary-rules).

### Alternatives Considered
1. **Stuff retros into TASK_REGISTRY as appendix sections** — bloats the plan; mixing forward-plan with backward-look is poor cognitive ergonomics; the two have different update cadences.
2. **Treat retros as informal markdown without frontmatter** — drift risk; hard to discover; not boundary-objects in the [Star & Griesemer 1989] sense.
3. **Combine retro + next-prompt into one document** — they have different audiences (operator review vs agent kickoff); keeping them separate keeps each focused.
4. **Skip retros entirely** — loses milestone-level learning; subsequent NEXT_PROMPT updates would have to reconstruct context from chat or memory, exactly what the discipline forbids.

### Consequences
- **Positive:** structured artefact captures milestone-level learning; feeds subsequent NEXT_PROMPT updates; enables cross-milestone trend analysis later.
- **Positive:** retros are STABLE-frozen on completion so they don't decay; can be cited as historical record at any time.
- **Negative:** one more artefact category to maintain; one more row class in CONTEXT_INVENTORY.
- **Follow-ups:** template lands in same commit (`docs/retros/_template.md`); CONTEXT_INVENTORY registers the RETRO category in §0 conventions; ADR-025 amends CONTEXT_PROTOCOL §8.3 to mandate retro-on-milestone-close.

### Cross-References
- [ADR-025](#adr-025--amend-context_protocol-83-with-milestone-close-and-phase-boundary-rules) — protocol amendment that mandates retros.
- [CONTEXT_PROTOCOL §8.3](../../CONTEXT_PROTOCOL.md) — session handoff (extended).
- `docs/retros/_template.md` — frontmatter and section template.

---

## ADR-025 — Amend CONTEXT_PROTOCOL §8.3 with milestone-close and phase-boundary rules

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** —

### Context
The existing CONTEXT_PROTOCOL §8.3 Session Handoff is generic — applies to every session. Two specific scenarios benefit from additional discipline:

- **Milestone close** (the last session of an M_N when its exit criteria are met or it is formally blocked): the agent should write a retrospective (per ADR-024), update `NEXT_PROMPT.md` for M_{N+1} informed by the retrospective, and report the gate status to the operator.
- **Phase boundary** (e.g., M3 → Phase 2 entry at the G4 gate): the closing implementation session of the prior phase should *not* be the session that plans the next phase. The mixing of implementation and next-phase planning in saturated context is a known substrate-drift mode.

Without explicit protocol, both scenarios slip into "we'll just plan the next thing in the same chat", violating the discipline.

### Decision
Amend `CONTEXT_PROTOCOL.md` §8.3 by adding two sub-sections:

- **§8.3.1 Additional steps at milestone close** — write retrospective per [ADR-024](#adr-024--add-session-retrospective-artefact-type); update `NEXT_PROMPT.md` for M_{N+1}; report gate status with explicit checklist.
- **§8.3.2 Phase boundary rule** — at phase boundaries, the closing implementation session ends with §8.3 + §8.3.1 only; next-phase planning requires a separate readiness-audit session and a separate plan-drafting session, with operator review between them.

### Alternatives Considered
1. **Leave as informal guidance** — would drift; the protocol exists precisely to prevent informal drift becoming silent practice change.
2. **Top-level §8.4, §8.5 instead of §8.3 sub-sections** — fragments the handoff coverage; the items belong logically to handoff.
3. **Make every session do retros** — too much ceremony for non-milestone sessions; retros are about milestone-level learning, not per-session friction.
4. **Combine milestone-close and phase-boundary rules into one paragraph** — they apply to different scopes; collapsing loses the distinction.

### Consequences
- **Positive:** explicit rules eliminate the "where does next-phase planning happen?" ambiguity.
- **Positive:** phase-boundary rule prevents the most common form of substrate drift in long projects: planning the next phase from saturated implementation context.
- **Positive:** existing §8.3 list is unchanged — additive amendment, not breaking.
- **Negative:** protocol slightly longer; reader must absorb sub-sections.
- **Follow-ups:** implement the amendment in the same commit as ADR-024; update `CONTEXT_PROTOCOL.md` §9 templates with the RETRO frontmatter shape; register RETRO category in CONTEXT_INVENTORY §0 conventions.

### Cross-References
- [ADR-024](#adr-024--add-session-retrospective-artefact-type) — retro artefact type.
- [CONTEXT_PROTOCOL §8.3](../../CONTEXT_PROTOCOL.md) — the section being amended.
- [TASK_REGISTRY G4](../../TASK_REGISTRY.md) — phase boundary case.

---

## ADR-026 — Adopt agentic-execution layer; reduce human action surface

- **status:** ACCEPTED
- **date:** 2026-04-26
- **decider:** Oleg
- **supersedes:** none
- **resolves:** —

### Context

The discipline as articulated in CONTEXT_PROTOCOL v0.2 places substantial manual burden on the human operator: warm-up reading, edit-protocol enforcement, cross-reference tracking, ADR / OQ writing, retrospective drafting, NEXT_PROMPT updating, status-lifecycle management. The Gemini research plan ([`docs/method/Research_Plan_for_Paper_Iteration_Gemini.md`](../method/Research_Plan_for_Paper_Iteration_Gemini.md)) catalogues the rapid maturation of agentic memory architectures (MemGPT, Agentic Memory / Zettelkasten, Multi-Layer Memory, Sculptor / ARC, graph-native context, Recursive Language Models). Both human practitioners (via the discipline) and AI researchers (via these architectures) have arrived at structurally similar substrate solutions. The discipline's posture should reflect this convergence by repositioning itself as the human-governance schema over agentic execution rather than as a manual alternative to it.

### Decision

Adopt a **human-governance / agent-execution division of labour**. The discipline's *content* is unchanged (six artefact categories, stable IDs, status lifecycle, edit protocol, propagation rules, anti-patterns). What changes is *who performs each step*: progressively more is delegated to substrate-aware tooling and agents, while the human's role refines to high-leverage actions — intent declaration, decision approval, scope governance, voice authority on substrate authoring.

Codify a five-layer adoption stack:

- **L0 — Substrate-aware warm-up agent.** Replaces manual file-list reading in `NEXT_PROMPT.md`.
- **L1 — Continuous integrity watchdog.** Background agent runs scheduled drift / orphan / staleness scans.
- **L2 — In-situ ADR auto-drafting.** Agent detects decisions and drafts ADRs at the moment of decision.
- **L3 — Auto-drafted retros + NEXT_PROMPTs.** At milestone close, agent populates RETRO and successor prompt from observable state.
- **L4 — Graph-native substrate.** Markdown becomes views over a knowledge graph; cross-references become first-class edges.

**Adoption order:** L0 + L1 first (low cost, immediate utility, layer-independent). L2 + L3 after L0/L1 prove reliable. L4 at discipline v2.0; deferred until current substrate's limits force the migration.

**Implementation deferred.** This ADR locks the *direction* and the *posture*; concrete tooling decisions land in [OQ-028](OPEN_QUESTIONS.md#oq-028--which-agentic-memory-framework--tooling-for-l0l1) and [OQ-029](OPEN_QUESTIONS.md#oq-029--when-to-implement-l0l1).

### Alternatives Considered

1. **Status quo — continue manual discipline.** Sustainable for low project complexity but doesn't scale; manual fatigue is the most common cause of substrate drift in practice. Rejected: doesn't future-proof against the maturing agentic-memory landscape.
2. **Replace discipline with autonomous memory only.** Loses human governance / auditability; over-trusts opaque memory systems. Rejected: violates the principle of legible substrate.
3. **Hybrid via ad-hoc scripts.** Drifts; no unified semantics; no guarantee of substrate integrity. Rejected: ends up at the same problem the discipline solves.
4. **Skip layers (jump directly to L4).** Tooling complexity dominates while value remains uncertain; loses the iterative validation that smaller layers provide.

### Consequences

- **Positive:** Human burden drops substantially per milestone (estimated 70–90% reduction once L0+L1 are operational; calibrate after first L0+L1 session).
- **Positive:** Substrate quality goes UP — drift detection runs continuously rather than per-milestone; retros populate from observable state rather than memory; ADRs filed at decision-moment rather than retrospectively.
- **Positive:** Discipline becomes practicable at larger project scales where current manual burden is prohibitive.
- **Positive:** Future-proofs the discipline against the maturing agentic-memory landscape; positions Cognitive Cartography as the governance complement to autonomous memory rather than a manual alternative.
- **Negative:** Introduces dependency on agentic execution; agent unavailability or confabulation become failure modes. Mitigated by L1 watchdog and mandatory human-approval gates on all agent-drafted outputs.
- **Negative:** Tooling dependency; L4 graph-native substrate is a non-trivial migration when adopted.
- **Follow-ups:**
  - `CONTEXT_PROTOCOL.md` §11 (NEW) specifies the division of labour and the layer stack. Existing §11 Self-Critique becomes §12.
  - [`docs/method/Amendments_Log.md`](../method/Amendments_Log.md) (NEW) records the amendment for future paper iteration.
  - [OQ-028](OPEN_QUESTIONS.md#oq-028--which-agentic-memory-framework--tooling-for-l0l1): which framework / tooling stack for L0+L1.
  - [OQ-029](OPEN_QUESTIONS.md#oq-029--when-to-implement-l0l1): timing of L0+L1 implementation.

### Cross-References

- [`CONTEXT_PROTOCOL.md` §11](../../CONTEXT_PROTOCOL.md) — division-of-labour specification.
- [`docs/method/Amendments_Log.md`](../method/Amendments_Log.md) — paper-iteration tracking.
- [`docs/method/Research_Plan_for_Paper_Iteration_Gemini.md`](../method/Research_Plan_for_Paper_Iteration_Gemini.md) — motivating literature.
- [ADR-024](#adr-024--add-session-retrospective-artefact-type) — RETRO type, auto-draftable at L3.
- [ADR-025](#adr-025--amend-context_protocol-83-with-milestone-close-and-phase-boundary-rules) — milestone-close protocol, target for L3 automation.

---

## ADR-027 — Sizer rounding policy: integer shares, truncate toward zero

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** —

### Context

The Sizer ([REQUIREMENTS §5.13](../../REQUIREMENTS.md)) converts `target_weight ∈ [-1, 1]`, `equity`, and `price` into a concrete `Order.quantity` (a `Decimal` per [DD-1 §2.4](../dd/domain_objects.md#24-order)). The arithmetic `(equity * target_weight) / price` in general yields a non-integer. We must commit to a rounding rule before writing code, because:

1. The rule directly affects the M1 G2 parity envelope (±1 bps end-of-period equity match against btest). Rounding is the *only* legitimate source of drift between btest and blive when the engines are imported by reference per [ADR-010](#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import).
2. Different IB account classes support different precisions. Cash accounts can hold fractional shares of *some US-listed instruments only* (excludes ADRs, OTC, leveraged ETFs in some periods, and *all European venues*). Margin accounts are integer-only across the board.
3. The Phase 1 instrument is `CAC.PA` on XPAR ([ADR-021](#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf)) — fractional shares are not available on European venues regardless of account class. So the integer rule is forced for Phase 1; the only question is whether to design for fractional later.

### Decision

For v1 (Phases 1–3), the Sizer **rounds to integer shares using truncation toward zero** (`Decimal.quantize(Decimal("1"), rounding=ROUND_DOWN)` for positive desired quantities; `ROUND_UP` toward zero for negative). Sub-share desired quantities (`abs(desired) < 1`) produce **no order** (the rebalance is a no-op for that instrument).

The Sizer's interface admits an `instrument_precision: Decimal` parameter defaulted to `Decimal("1")` (integer). Future fractional-share support flips the default per asset class via the `Instrument` lookup; the change is additive, not breaking.

**Parity contract.** btest's `event_driven` engine's sizing path must be inspected during M1 implementation; if btest does not already round to integer shares, we file an OQ on the parity-arithmetic question rather than papering over divergence.

### Alternatives Considered

1. **Round to IB fractional precision per account class.** Rejected for v1: precision varies per `(account_class, instrument)` tuple and is not stable; introduces a cross-cutting query into the Sizer that the broker port doesn't currently expose; adds complexity for a Phase-1 instrument that doesn't support it anyway.
2. **Round to nearest (banker's rounding / `ROUND_HALF_EVEN`).** Rejected: half-share boundary cases on small allocations cause asymmetric over-/under-sizing relative to a deterministic truncate-toward-zero rule. ROUND_DOWN is conservative (always under-size, never over).
3. **Allow fractional `Decimal` quantities and let the broker reject.** Rejected: late failure; risk-engine bypass smell; obscures parity test.
4. **Fixed-precision per `Instrument`** (the precision field stored on `Instrument`). Considered, deferred: requires `Instrument` to grow a field, which would be a DD-1 change. Re-raise at M2 when fractional becomes plausible for US ETFs.

### Consequences

- **Positive:** deterministic, conservative, reproducible. Parity test against btest reduces to a known-shape check.
- **Positive:** Sub-share rebalances become no-ops, which is the right default for Phase 1's small NAV slice (5–10%, [ADR-020](#adr-020--phase-1-nav-slice-510-of-total-cap-10)) where rebalance fractions of e.g. 0.4 share happen on small price gaps.
- **Negative:** tracking error vs. target weight on small accounts; mitigated by Phase 1 NAV slice cap (~€50k–€100k notional on a ~€78 share is ≥ 600 shares, so tracking error on 1 share is < 17 bps — well-bounded).
- **Negative:** when the strategy goes to/from flat, a single 1-share leftover position can persist after the "exit" rebalance if the new target rounds to zero but the old position was not zero. M1 implementation must explicitly reset to zero on exit signals (not derive zero by rounding).
- **Follow-ups:** revisit at G2 with observed parity envelope; revisit at M2 entry when fractional shares become plausible for US ETF strategies (Phase 2 A3 — `triple_lev_sma_filter_dsl`).

### Cross-References

- [REQUIREMENTS §5.13](../../REQUIREMENTS.md) — Sizer scope.
- [ADR-010](#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import) — engine reuse; parity assumption.
- [ADR-021](#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) — Phase 1 instrument.
- [DD-1 §2.4](../dd/domain_objects.md#24-order) — `Order.quantity` is `Decimal`.
- [TASK_REGISTRY](../../TASK_REGISTRY.md) M1 G2 — ±1 bps parity criterion.

---

## ADR-028 — Strategy config shape: Python `build_strategy()` + blive YAML overrides

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** —

### Context

[REQUIREMENTS §5.1](../../REQUIREMENTS.md) commits blive to importing an unmodified `btest.Strategy` dataclass. [REQUIREMENTS §5.13](../../REQUIREMENTS.md) commits to strategy discovery via Python modules exposing `build_strategy(config: dict) -> Strategy`. blive adds three sidecar extensions: `execution.live_overrides`, `costs.live_*_provider` hooks, `risk.live_kill_switch`.

DD-3 ([CONTEXT_INVENTORY §4](../../CONTEXT_INVENTORY.md#4-data-dictionaries-dds), MISSING) is the data dictionary for these YAML knobs. Before we author DD-3 we must lock the *shape*: where the canonical strategy spec lives, where blive-only overrides live, how they merge, and how the spec id (`sha256(resolved_yaml + ...)` per [REQUIREMENTS §5.12](../../REQUIREMENTS.md)) is computed.

Three options have been considered:

1. **Single YAML, btest-extended.** Extend btest's existing strategy YAML with new keys; btest must ignore unknown keys. Risk: btest's validators reject unknown keys; blive would have to fork btest's loader.
2. **Single YAML, blive-owned.** Replace btest's loader entirely; build the btest `Strategy` from blive's YAML. Risk: parallel maintenance of every btest DSL field shape; high drift.
3. **Hybrid: Python module produces `Strategy`, blive YAML provides live-only overrides keyed by strategy_id.** The Python module is btest's existing `build_strategy()`. blive's YAML lives next to the module and carries only blive-specific keys (live_overrides, kill_switch, NAV slice, artefact paths, RC threshold overrides).

### Decision

Adopt **Option 3 (hybrid)**.

**Strategy ingest pipeline:**

1. blive YAML at `~/.blive/strategies/{strategy_id}/live.yaml` declares:
   - `strategy_module: str` — dotted-path Python module (e.g. `btest.strategies.tkan_v4_momentum_timing`).
   - `build_strategy_kwargs: dict` — kwargs passed to the module's `build_strategy(**kwargs)` call.
   - `nav_slice: Decimal` — fraction of account NAV allocated; capped at 0.10 per [ADR-020](#adr-020--phase-1-nav-slice-510-of-total-cap-10).
   - `live_overrides: { tif, routing, ib_algo, outside_rth, ... }` — overlays `Strategy.execution.live_overrides`.
   - `live_borrow_provider: { kind, config }` — overlays `Strategy.costs.live_borrow_provider`.
   - `live_financing_provider: { kind, config }` — overlays `Strategy.costs.live_financing_provider`.
   - `live_kill_switch: { max_intraday_drawdown, max_consecutive_rejects, ... }` — per-strategy kill criteria.
   - `artefact_paths: dict[str, str]` — overrides for `ExternalFactor.path` (so prod artefact path differs from research path per [ADR-023](#adr-023--tkan-artefact-path-and-refresh-ownership)).
   - `risk_overrides: dict[str, Decimal]` — per-strategy overrides for [INV-4](../inv/risk_checks.md) thresholds (`max_data_staleness_intraday_sec`, `max_model_artefact_age_days`, etc.).

2. blive's loader (`blive.strategy.loader`) parses YAML via Pydantic v2 models (per CLAUDE.md "all tunables read from YAML config via Pydantic"), imports the module, calls `build_strategy(**build_strategy_kwargs)`, then applies overrides as a structured patch to the resulting `Strategy`.

3. **Spec id computation:** SHA-256 of `(canonical_yaml_bytes, strategy_module_dotted_path, btest_version, blive_version, artefact_sha256_for_each_external_factor)`. Recorded with every domain event per [REQUIREMENTS §5.12](../../REQUIREMENTS.md).

**Override merge rules:**

- Numeric scalars in `live_overrides` / `live_kill_switch` / `risk_overrides` overwrite by key.
- `artefact_paths` overwrites `ExternalFactor.path` by factor name.
- Forbidden overrides per [REQUIREMENTS §5.10](../../REQUIREMENTS.md): type fields, universe definition, factor / signal DAG topology. The override applier raises if a forbidden field appears.

### Alternatives Considered

1. **Single YAML btest-extended** — rejected (above): forks btest's loader.
2. **Single YAML blive-owned** — rejected (above): high drift maintenance.
3. **JSON Patch (RFC 6902) overrides** ([REQUIREMENTS §5.10](../../REQUIREMENTS.md) suggested this for runtime parameter overrides). Considered: structured, validated. Decision: keep JSON Patch as the mechanism for *runtime* parameter overrides (Strategy detail page form). Persistent strategy config uses the structured YAML schema above for ergonomics. Both end up applying patches against the resolved tree; the *grammar* of validation is the same.

### Consequences

- **Positive:** btest stays untouched; blive owns its sidecar config without forking. Strategy discovery is the existing Python-module pattern from REQUIREMENTS §5.13.
- **Positive:** YAML is human-readable for ops; Pydantic validation gives clear errors at startup.
- **Positive:** spec id remains stable across blive versions as long as YAML + module + artefact hashes don't change.
- **Negative:** two locations for "what the strategy is" — the Python module and the YAML. Ops must understand both.
- **Negative:** override application is a custom step; bugs there bypass btest's own validation. M1 unit tests must exercise allowed and forbidden override surfaces.
- **Follow-ups:** DD-3 codifies the field-level schema after this ADR is accepted; M1 implementation produces the Pydantic models; M2 IB adapter reads `live_overrides.routing` / `live_overrides.ib_algo` and feeds them through.

### Cross-References

- [REQUIREMENTS §5.1, §5.10, §5.12, §5.13](../../REQUIREMENTS.md) — strategy ingest, override grammar, spec id, sizer / discovery.
- [DD-3 config_schemas](../dd/config_schemas.md) — MISSING; authored against this ADR at M1.
- [INV-4](../inv/risk_checks.md) — risk threshold override paths.
- [ADR-010](#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import) — btest reuse contract.
- [ADR-023](#adr-023--tkan-artefact-path-and-refresh-ownership) — artefact prod path policy.

---

## ADR-029 — `PaperMarketData` as `MarketDataPort` adapter, fixture-backed parquet

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** —

### Context

The M1 paper-mode end-to-end pipeline ([TASK_REGISTRY](../../TASK_REGISTRY.md) M1 deliverable 6) needs a deterministic CAC.PA bar source. Two shapes are viable:

1. **Ad-hoc fixture loading** — the test or runner reads a parquet file directly and feeds bars into the pipeline.
2. **`PaperMarketData` as a `MarketDataPort` adapter** — `blive.adapters.paper.market_data.PaperMarketData` implements the [INV-6 §1.2](../inv/ports_adapters.md#12-marketdataport) Protocol and reads from a fixture file.

The M0 retro recommendation 2 explicitly preferred (b). [INV-6 §2.2](../inv/ports_adapters.md#22-marketdataport-adapters) already lists `PaperMarketData` at M1 as MISSING. [ADR-014](#adr-014--data-sources-via-clean-api-abstraction) commits to all data sources implementing the existing `DataSource` protocol — `PaperMarketData` is the live-side analogue of btest's `parquet://` source.

### Decision

Implement `blive.adapters.paper.market_data.PaperMarketData` as a `MarketDataPort` adapter. Concrete shape:

- **Source:** parquet file with columns `(open_time_utc, close_time_utc, open, high, low, close, volume)` and optional `vwap`. Path passed to constructor.
- **Frequency:** initial scope is `1d` (Phase 1 = F0). Fixture parquet implies the bar frequency; mismatched `subscribe_bars(freq=...)` raises.
- **Async iterator semantics:** `subscribe_bars(instrument, freq)` yields one `Bar` per row in chronological order, then awaits the next `clock.sleep(...)` tick if the runner is in real-time-paced mode, or yields immediately in tape-replay mode (M1 default).
- **`subscribe_trades`:** raises `NotImplementedError` for v1 (no trade-level fixtures yet; Phase 1 F0 daily strategies don't subscribe to trades).
- **`historical_bars`:** returns the slice of the fixture overlapping `[start, end]`; respects `instrument` lookup.
- **Fixture location:** `tests_slow/fixtures/paper_market_data/{venue}/{symbol}_{freq}.parquet` for committed test fixtures; arbitrary path admitted at runtime via constructor.

The adapter is the M1 substrate-level placeholder slot already declared in [INV-6 §2.2](../inv/ports_adapters.md#22-marketdataport-adapters). It also serves the long-running parity test (M7 continuous parity replay) by providing a deterministic playback engine inside blive's process.

### Alternatives Considered

1. **Ad-hoc fixture loading inside the test or runner.** Rejected per the M0 retro: violates [ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement) (the runner would have to know about parquet); doesn't exercise the `MarketDataPort` contract; M2's `IBMarketData` / `EODHDMarketData` would then have a different code path than M1's tests.
2. **Use btest's `parquet://` source verbatim.** Considered: btest's `DataSource` returns a `DataBundle` of full DataFrames, not a stream of `Bar` objects. The shapes don't align with `MarketDataPort.subscribe_bars` async-iterator contract. Bridge code would be larger than a clean reimplementation.
3. **Generate synthetic bars in-memory.** Considered for unit tests: too low-fidelity for the G2 ±1 bps parity test which needs real CAC.PA price history.

### Consequences

- **Positive:** unifies M1 paper test path with M2/M3 live test path — same `MarketDataPort` contract.
- **Positive:** the parity test is reproducible from a checked-in parquet (or a deterministic fetch script that re-creates it from EODHD when needed).
- **Positive:** the same adapter is the natural foundation for the M7 continuous-parity replica (`btest`-paper alongside live, see [ADR-012](#adr-012--parity-diagnostic-mandatory-daily-degraded-mode-if-broken)).
- **Negative:** writing the adapter is real M1 work (~1 small module + tests). The ad-hoc alternative is cheaper *for M1 only*.
- **Negative:** parquet fixture is repo weight; mitigated by limiting Phase 1 fixture to ≥ 252 trading days (~80 KB compressed for a single instrument).
- **Follow-ups:** the EODHD historical-fetch script that produces the fixture is a Phase-1 utility (`scripts/fetch_paper_fixture.py`); itself an M1 deliverable so the fixture is reproducible.

### Cross-References

- [INV-6 §1.2, §2.2](../inv/ports_adapters.md) — `MarketDataPort` contract; adapter slot.
- [ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement) — hexagonal contract; runner cannot read parquet directly.
- [ADR-014](#adr-014--data-sources-via-clean-api-abstraction) — data sources via clean abstraction.
- [ADR-017](#adr-017--live-data-hybrid-eodhd--ib-streaming-per-instrument-routing) — hybrid live data routing; M2 swaps in `IBMarketData` / `EODHDMarketData`.
- [TASK_REGISTRY](../../TASK_REGISTRY.md) M1 deliverable 6 — paper-mode end-to-end pipeline.
- [`docs/retros/M0_retrospective.md`](../retros/M0_retrospective.md) "Recommendations for NEXT_PROMPT M1" rec 2.

---

## ADR-030 — Per-archetype btest interpreter dispatch (amends ADR-010)

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** [OQ-030](OPEN_QUESTIONS.md#oq-030--which-btest-interpreter-does-blive-call-for-timingportfolio-and-other-non-longshort-archetypes)

### Context

[ADR-010](#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import) commits blive to importing btest's "FactorEngine, SignalEngine, PortfolioEngine" rather than forking. M1 implementation surfaced two facts that ADR-010's prose does not capture:

1. `PortfolioEngine` is a **free function** (`compute_target_weights_for_date()` in `quantdsl_backtest.engine.portfolio_engine`), not a class, and it only handles `LongShortPortfolio`.
2. `TimingPortfolio` strategies — including the Phase 1 `tkan_v4_momentum_timing` 1× — are interpreted by `quantdsl_backtest.runners.single_asset.SingleAssetRunner`, a separate module that bundles factor evaluation, signal evaluation, and position derivation in one batch interpreter. This is **not** the three-engine composition ADR-010 names.

ADR-010's spirit ("reuse btest's strategy semantics, do not fork") is preserved — but its enumeration is incomplete, and the M1 paper pipeline already dispatches by archetype. [OQ-030](OPEN_QUESTIONS.md#oq-030--which-btest-interpreter-does-blive-call-for-timingportfolio-and-other-non-longshort-archetypes) captured this gap with a working default and three resolution options.

### Decision

Adopt **per-archetype dispatch** as the canonical interpretation pattern between blive and btest, codified at the strategy-loader / runtime boundary. The dispatch table for v1:

| `strategy.portfolio` archetype | btest interpreter surface | blive call site |
|---|---|---|
| `LongShortPortfolio` | `FactorEngine` + `SignalEngine` + `compute_target_weights_for_date()` | M2+; not exercised at M1 (no LongShort strategy in Phase 1) |
| `TimingPortfolio` | `quantdsl_backtest.runners.single_asset.SingleAssetRunner.run(price_close=...)` | `blive.runtime.paper_pipeline` (M1); same path in IB-paper / live (M3+) |

Future archetypes (multi-instrument timing, basket rotation, etc.) register a new row when they land. Unrecognised archetypes raise `NotImplementedError` at strategy-load time, naming the archetype and pointing here.

ADR-010 stays ACCEPTED — its spirit holds; this ADR amends only the *enumeration of interpreters* as a complementary record, per [CONTEXT_PROTOCOL §2.5](../../CONTEXT_PROTOCOL.md) (decision log is append-only; we do not edit ADR-010's body).

### Alternatives Considered

1. **Reimplement `TimingPortfolio` inside blive** as a streaming evaluator. Rejected: reintroduces the drift ADR-010 was meant to prevent; ADR-012's parity contract becomes much harder to keep.
2. **Extend btest** to expose a class-shaped `TimingPortfolioEngine`. Rejected for v1: cross-project coordination cost; doesn't match how btest already structures runners; nothing forces a uniform shape across archetypes.
3. **Keep ADR-010 unchanged and treat dispatch as undocumented**. Rejected: leaves M2+ authors guessing; M1 retro already flagged this; phantom-decision anti-pattern ([CONTEXT_PROTOCOL §3.5](../../CONTEXT_PROTOCOL.md)).

### Consequences

- **Positive:** explicit dispatch table; new archetypes have a named home; M2+ adapter authors know where to plug in; ADR-010's spirit preserved.
- **Negative:** the table grows as archetypes land; small upstream-drift risk — mitigated by `tests/contracts/test_btest_imports.py` smoke-import contract.
- **Follow-ups:**
  - **KB-1 §6** prose (btest engines section) is now incomplete; an editorial pass should add one paragraph linking here. Tracked as a CONTEXT_INVENTORY priority-queue item; not a same-commit update because KB-1 lives btest-side and the canonical home is its file.
  - When M2+ exercises `LongShortPortfolio`, add a smoke test analogous to the `SingleAssetRunner` one in `test_btest_imports.py`.
  - `SingleAssetRunner` is batch-only ([RETRO-M1](../retros/M1_retrospective.md) "Recommendations"); when M3 introduces per-bar streaming dispatch, revisit the "blive call site" column.

### Cross-References

- [ADR-010](#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import) — reused-by-import policy (this ADR amends scope, does not supersede).
- [OQ-030](OPEN_QUESTIONS.md#oq-030--which-btest-interpreter-does-blive-call-for-timingportfolio-and-other-non-longshort-archetypes) — resolved by this ADR.
- [KB-1 §6](../kb/btest_dsl_inventory.md) — btest engines section (forward-update follow-up).
- [`blive.runtime.paper_pipeline`](../../src/blive/runtime/paper_pipeline.py) — M1 dispatch site.
- [`tests/contracts/test_btest_imports.py`](../../tests/contracts/test_btest_imports.py) — smoke-import contract.
- [RETRO-M1](../retros/M1_retrospective.md) — "Surprises" raised this question.

---

## ADR-031 — Token-bucket rate limiter shape for IB adapters

- **status:** ACCEPTED
- **date:** 2026-04-27 (PROPOSED) / 2026-04-28 (ACCEPTED at M2-IB.2)
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** —

### Context

[REQUIREMENTS §10 gotcha 1](../../REQUIREMENTS.md#10-ib-specific-gotchas-must-be-first-class-in-adapter) and [KB-3 §1](../kb/ib_pacing_spec.md#1-the-50-msgsec-client-throttle) require the IB adapter to throttle outbound calls below IB's 50 msg/sec hard cap (3 violations terminate the session). [KB-3 §9](../kb/ib_pacing_spec.md#9-summary-adapter-budget-defaults) sets defaults: 20 msg/sec global ceiling; 5 msg/sec per-strategy ceiling (also [INV-4 RC-05/RC-06](../inv/risk_checks.md)). The rate limiter is the **first M2 code module** because it sits beneath both `IBBroker` and `IBMarketData`, and the G3 throttle test ("burst of 60 calls/sec; outbound rate stays ≤ 20 msg/sec") is the gate criterion.

Three algorithm options exist (token bucket, leaky bucket, sliding window) and three accounting choices (global only, per-strategy only, both).

### Decision

- **Algorithm:** **token bucket**, refilled at a constant rate. Two-level: a **global** bucket (default capacity = 20 tokens, refill = 20/s) and **per-strategy** sub-buckets (default capacity = 5 tokens, refill = 5/s). A call requires one token from the strategy bucket *and* one from the global bucket; if either is empty, the caller awaits until both refill.
- **Awaiting semantics:** the limiter's public method is `async def acquire(strategy_id: str) -> None`, blocking until both tokens are available. Caller never sees a rejection from the limiter — back-pressure flows through asyncio. The IB-side error code 100 ("max rate exceeded") is therefore *defence-in-depth*, not the primary throttle.
- **Clock source:** [`ClockPort`](../inv/ports_adapters.md#13-clockport). Tests use [`SimClock`](../../src/blive/adapters/clock/sim.py) to advance time deterministically.
- **Persistence:** in-memory only. Counters reset on process restart, which matches IB's view (the 50 msg/sec window resets on reconnect anyway). No SQLite row.
- **Configurability:** thresholds passed to constructor; defaults from [KB-3 §9](../kb/ib_pacing_spec.md#9-summary-adapter-budget-defaults). Per-strategy override admitted via `RiskOverrides.max_orders_per_sec_strategy` at M4 ([INV-4 RC-05](../inv/risk_checks.md), forward-compat ignored at M2).
- **Module location:** `blive.adapters.ib.rate_limiter` — adapter-side, not domain-side. The domain has no rate-limit concept; this is purely how blive throttles its own outbound traffic to honour IB's contract.
- **Public surface:** `class TokenBucketRateLimiter`, with `acquire(strategy_id)`, `set_global_rate(...)`, `set_strategy_rate(...)`, plus a `metrics()` accessor for observability ([REQUIREMENTS §5.9](../../REQUIREMENTS.md): "IB throttle headroom" Prometheus gauge).

### Alternatives Considered

1. **Leaky bucket.** Equivalent throughput shape, but the two-level composition is awkward — leaky-bucket models smoothing, not budgeting. Token bucket maps cleanly to IB's "messages per second" budget.
2. **Sliding window.** Exact 1-second window; precise but storage-heavy (per-call timestamps); marginal benefit over token bucket at our message volumes.
3. **Global only (no per-strategy).** Rejected: violates [INV-4 RC-05](../inv/risk_checks.md) "≤ 5/sec per strategy" requirement; leaves a single misbehaving strategy able to consume the whole 20-token budget.
4. **Per-strategy only (no global).** Rejected: doesn't directly defend against the 50-msg/sec hard cap if many strategies fire simultaneously.

### Consequences

- **Positive:** simple, well-understood algorithm; deterministic via `ClockPort` for tests; pure-Python; no IB dependency (testable without the wire).
- **Positive:** the G3 throttle test (`burst of 60 calls/sec` → `≤ 20 msg/sec sustained`) becomes a unit test that runs in milliseconds with `SimClock`.
- **Negative:** two-level token bucket has slightly more state than a single counter; mitigated by simple internal structure (`dict[strategy_id, Bucket]`).
- **Negative:** the limiter does not back-pressure data-flow producers (e.g. `subscribe_bars`) — those are read-side IB callbacks, not outbound calls. Read-side flow control (if needed) is a separate concern.
- **Follow-ups:**
  - Prometheus gauge `blive_ib_throttle_headroom` populated from `metrics()` at M7.
  - When IB's hard cap changes (rare, but not unprecedented), bump the global default via [KB-3 §9](../kb/ib_pacing_spec.md#9-summary-adapter-budget-defaults).
  - The `set_strategy_rate(...)` path is the integration point with [DD-3 §7 RiskOverrides](../dd/config_schemas.md#7-riskoverrides) when M4 widens that section.

### Cross-References

- [REQUIREMENTS §10 gotcha 1](../../REQUIREMENTS.md#10-ib-specific-gotchas-must-be-first-class-in-adapter), [§5.5 (rate limits)](../../REQUIREMENTS.md), [§5.9 (observability)](../../REQUIREMENTS.md).
- [KB-3 §1](../kb/ib_pacing_spec.md#1-the-50-msgsec-client-throttle), [§9](../kb/ib_pacing_spec.md#9-summary-adapter-budget-defaults).
- [INV-4 RC-05, RC-06](../inv/risk_checks.md) — order-rate risk checks (full set lands at M4).
- [INV-6 §1.3](../inv/ports_adapters.md#13-clockport) — `ClockPort`.
- [TASK_REGISTRY](../../TASK_REGISTRY.md) M2 deliverable 4 — `IBBroker` adapter (consumer of this limiter).

---

## ADR-032 — Instrument resolution policy: blive Instrument ↔ IB Contract

- **status:** ACCEPTED
- **date:** 2026-04-27 (PROPOSED) / 2026-05-01 (ACCEPTED at M2-IB.3a-resolved)
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** —

### Context

[DD-1 §2.1](../dd/domain_objects.md#21-instrument) defines `Instrument(symbol, venue, currency, asset_class, multiplier)` as the broker-neutral identity. The IB adapter must map this to an `ib_async.Contract` (and, internally, an integer `ConID`). [KB-2 §2](../kb/ib_capability_matrix.md#2-asset-classes) notes "`Contract` resolution is by `ConID` (an integer IB ID); blive's `Instrument` ↔ `Contract` mapping happens in `IBBroker` and is documented in DD-7 (MISSING)." DD-7 is the deferred MISSING artefact this ADR's design feeds into.

Three concerns: the field-level mapping; the ConID lookup mechanism + caching strategy; behaviour when `qualifyContracts()` returns multiple candidates (ambiguous symbology, e.g. `AAPL` on multiple exchanges).

### Decision

- **secType mapping:** `AssetClass.EQUITY` → `STK`; `AssetClass.ETF` → `STK` (IB does not distinguish ETFs from equities at secType); `AssetClass.INDEX` → `IND`; `AssetClass.FX` → `CASH`; `AssetClass.FUTURE` → `FUT`; `AssetClass.OPTION` → `OPT`. Unsupported asset classes raise `InstrumentNotResolvable` at the adapter boundary (don't reach the wire).
- **Field carry-through:** `symbol`, `currency` map directly. `venue` (MIC code, e.g. `XPAR`) maps to `ib_async.Contract.exchange` (e.g. `SBF`); the mapping is via a small static table (`MIC_TO_IB_EXCHANGE`) in the adapter, sourced from [KB-2 §5](../kb/ib_capability_matrix.md#5-routing). For Phase 1 the table only needs `XPAR → SBF`; new venues add rows.
- **ConID resolution:** lazy, on first use per Instrument. Call `ib.qualifyContractsAsync(contract)`; on success, cache `(Instrument → conId)` in memory keyed by full `Instrument` tuple equality.
- **Cache TTL:** process lifetime. `ConID`s are stable for non-corp-action instruments; corp actions (rare) invalidate the lookup, which is detected by IB returning a different conId or by an explicit `clear_cache(instrument)` call wired into M5 reconciliation.
- **Ambiguity:** when `qualifyContractsAsync()` returns >1 candidate (or `>1` after primaryExchange filter), raise `InstrumentAmbiguous(instrument, candidates)` with each candidate's `(conId, primaryExchange, currency)` listed. **Never silently pick one.** The caller must resolve via a more specific `Instrument` (typically by setting `venue` to the primary exchange MIC).
- **Module location:** `blive.adapters.ib.instrument_resolver` — pure adapter concern, not in the domain.
- **DD-7 publication:** this ADR's mapping table + cache contract are the DD-7 v0.1 substrate. DD-7 lands DRAFT in this commit batch; it goes STABLE when the M2 IBBroker exercises the path against IB Paper.

### Alternatives Considered

1. **Eager resolution at Instrument construction.** Rejected: would require IB connection at strategy-load time, violating layer purity ([ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement)) — domain code constructs `Instrument`s.
2. **Cache to disk.** Rejected for v1: ConIDs are cheap to re-resolve (one `qualifyContracts` round trip per instrument per process); persistence adds invalidation surface.
3. **Auto-disambiguate by primary exchange heuristic.** Rejected: the symbology surprises IB sometimes throws (e.g. a fund with the same ticker on two MICs) deserve an explicit error so the operator picks correctly.
4. **Bind `Instrument` directly to `ib_async.Contract`.** Rejected: breaks broker-neutrality; the `Instrument` would no longer round-trip to non-IB adapters (e.g. `EODHDDataSource`).

### Consequences

- **Positive:** clean broker-neutral identity; explicit ambiguity errors surface at the boundary; cache is in-process only (no persistence surface).
- **Negative:** the static MIC↔IB-exchange table is a substrate that drifts if IB renames a routing destination; pinned to KB-2 §5 with date-accessed citations.
- **Negative:** a fresh process re-resolves every instrument once; for Phase 1 (1 instrument) this is one round trip on startup — negligible; for many-instrument strategies the warm-up cost is bounded by [KB-3 §2](../kb/ib_pacing_spec.md#2-historical-data-pacing) historical-data pacing already.
- **Follow-ups:**
  - DD-7 STABLE flip when M2 IBBroker exercises the path successfully against IB Paper.
  - `clear_cache(instrument)` accessor wired into M5 reconciliation when corp-action handling lands.
  - The `MIC_TO_IB_EXCHANGE` table grows with each new venue (Phase 2/3 US equities → `XNAS`/`XNYS`/`ARCA` → `NASDAQ`/`NYSE`/`ARCA`).

### Cross-References

- [DD-1 §2.1](../dd/domain_objects.md#21-instrument) — `Instrument` shape.
- [KB-2 §2, §5](../kb/ib_capability_matrix.md) — IB asset classes + routing.
- [ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement) — broker-neutrality.
- [`docs/dd/instrument_dictionary.md`](../dd/instrument_dictionary.md) — DD-7 (DRAFT, this commit).
- [TASK_REGISTRY](../../TASK_REGISTRY.md) M2 substrate transitions — DD-7 MISSING → DRAFT.

---

## ADR-033 — `AccountUpdate` event shape and sampling cadence

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** —

### Context

[INV-5](../inv/domain_events.md) catalogues `account.update` (M2 row) carrying an `AccountSnapshot` payload, with consumers "persistence (subsampled), UI". [REQUIREMENTS §6.5](../../REQUIREMENTS.md#65-data-retention) implies a 30 s sampling cadence for snapshots. `ib_async`'s `accountValuesEvent` fires on every IB push (potentially many times per second across many fields), so blive needs to define normalisation + cadence so the event bus is not flooded.

Two sub-decisions: (1) **payload** — what fields land in the emitted event; (2) **cadence** — how often blive emits.

### Decision

- **Payload type:** `AccountUpdate(snapshot: AccountSnapshot, time_utc: datetime)`. Reuses the existing [DD-1 §2.8](../dd/domain_objects.md#28-accountsnapshot) `AccountSnapshot` dataclass — no new fields. The wrapper carries a topic-friendly type identity for [INV-5](../inv/domain_events.md) and the `DomainEvent` union.
- **Cadence:** **30-second wall-clock subsample, with diff-suppress.** Internally the IB adapter accumulates the latest values from `accountValuesEvent`; a periodic 30-s task takes a snapshot, compares against the previously emitted one, and emits only when at least one field changed by more than its per-field threshold. Default thresholds:

  | Field | Threshold for emission |
  |---|---|
  | `equity` | ≥ 0.01 currency unit |
  | `cash_by_ccy[ccy]` | ≥ 0.01 currency unit |
  | `buying_power` | ≥ 0.01 currency unit |
  | `gross_exposure`, `net_exposure` | ≥ 0.01 currency unit |
  | `leverage` | ≥ 0.001 (3 d.p.) |
  | `margin_used` | ≥ 0.01 currency unit |

  Below threshold, no event; the next 30-s tick re-evaluates against the latest emission.

- **Persistence:** event-log append per [INV-5 §3](../inv/domain_events.md#3-persistence-ordering-rule) ordering rule (persist before publish). M4 SQLite tables will store full history; M1 in-memory persistence keeps the latest N for the UI (N=2,880 = 24h at 30-s cadence).
- **Subscription model:** the IB adapter calls `ib.reqAccountUpdates(True, accountId)` on connect; the 30-s timer is internal to `IBBroker.account_snapshot()` polling — `account_snapshot()` returns synchronously from cached state, the timer task is what produces emitted events.
- **Module location:** `blive.domain.events.AccountUpdate` (the dataclass — sits with the other domain events) + emission timer in `blive.adapters.ib.broker`.

### Alternatives Considered

1. **Emit every IB push.** Rejected: floods the event bus with tens of events per second of essentially the same state; [REQUIREMENTS §11](../../REQUIREMENTS.md) "event volume bounded by trade frequency, not market data" framing breaks.
2. **Emit on demand (no timer; only when a consumer calls `account_snapshot()`).** Rejected: misses the "periodic 30-s sample" framing of [REQUIREMENTS §6.5](../../REQUIREMENTS.md); UI dashboard wouldn't update without a polling consumer.
3. **Emit on every change, no thresholds.** Rejected: floating-point oscillation in `leverage` / `gross_exposure` would emit no-op events; the diff-suppress is cheap insurance.
4. **Vary the cadence per-field** (e.g. `buying_power` every push, `leverage` every minute). Rejected as premature; one cadence keeps the implementation simple and the diff-suppress thresholds carry the load.

### Consequences

- **Positive:** bounded event-bus load (≤ 1 emit per 30 s per account); UI dashboard refreshes at predictable cadence; no new domain types beyond a slim wrapper.
- **Positive:** `AccountSnapshot` reuse means the existing invariants ([DD-1 §2.8](../dd/domain_objects.md#28-accountsnapshot)) carry over.
- **Negative:** a sudden large change between 30-s ticks is observed at most 30 s late; acceptable for v1 (the dashboard is monitoring, not control).
- **Negative:** thresholds are per-currency-unit and may need scaling for high-NAV accounts; revisit at M7 with observed real-account behaviour.
- **Follow-ups:**
  - DD-2 row added in this commit batch.
  - When IB pushes `pnlSingle` / `pnl` events (per-position PnL), wire those into the same cadence as a separate `PnLUpdate` event family — out of M2 scope; flagged for M5 reconciliation.

### Cross-References

- [INV-5](../inv/domain_events.md#1-event-catalogue) — `account.update` row (M2).
- [DD-1 §2.8](../dd/domain_objects.md#28-accountsnapshot) — `AccountSnapshot` payload.
- [DD-2](../dd/event_schemas.md) — DRAFT in this commit; carries the field-level dictionary for `AccountUpdate`.
- [REQUIREMENTS §6.5](../../REQUIREMENTS.md#65-data-retention), [§11](../../REQUIREMENTS.md).
- [TASK_REGISTRY](../../TASK_REGISTRY.md) M2 substrate transitions — INV-5 widens with `AccountUpdate`.

---

## ADR-034 — Multi-broker registry pattern (extends ADR-004)

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none (extends [ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement))
- **resolves:** —

### Context

[ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement) establishes hexagonal architecture: domain depends only on Ports; adapters implement them. M0+M1 shipped one concrete `BrokerPort` adapter (`PaperBroker`); M2-IB planned a second (`IBBroker`). The 2026-04-27 pivot to an IG demo bridge ([TASK_REGISTRY](../../TASK_REGISTRY.md) M2-IG) introduces a third (`IGBroker`), and the operator's directive — "make sure we have a clean abstraction layer for various broker apis" — asserts that we expect more, not just two.

The hexagonal Pattern alone does not specify:

- How a strategy YAML declares which broker it uses.
- Where per-broker config lives.
- How the runtime resolves the broker selection.
- How adapters discover their configuration.
- How credentials are loaded (split into [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets)).

These choices are currently implicit (M1 hardcoded `PaperBroker` construction in the test harness). Without explicit substrate, dispatch logic will accumulate as ad-hoc imports + conditionals across `runtime/`, `strategy/`, and `adapters/` — exactly the rot ADR-004 was meant to prevent. Substrate is needed before the second concrete adapter (IG) ships.

### Decision

Adopt a **multi-broker registry pattern**, layered on top of [ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement). Concrete shape:

1. **Top-level config field.** [DD-3 §1](../dd/config_schemas.md#1-livestrategyconfig-top-level) gains a required top-level `broker: Literal["paper", "ig", "ib"]` field. Per-broker config blocks are optional sub-objects (`paper_config`, `ig_config`, `ib_config`); only the selected broker's block is read.

2. **Adapter package layout convention.** Each broker adapter family lives at `blive.adapters.{broker_name}`. Required modules per broker:
   - `broker.py` — the `BrokerPort` implementation (e.g. `IGBroker`, `IBBroker`, `PaperBroker`)
   - `market_data.py` — the `MarketDataPort` implementation
   - `instrument_resolver.py` — `Instrument` ↔ broker-specific identity (skip for `paper` which has no native identity)
   - `credentials.py` — credential schema + load helpers (per [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets); skip for `paper`)

3. **Cross-cutting shared modules.** Pieces used by multiple broker adapters live under `blive.adapters.shared.*`:
   - `rate_limiter.py` — the [ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) token-bucket algorithm, configured per-broker at construction (defaults supplied by each broker's KB).
   - `credentials.py` — env-var / file loading helpers per [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets).

4. **Runtime dispatch.** A new module `blive.runtime.broker_registry` exposes:
   ```python
   def get_broker(name: str, config: BrokerConfig, *, clock: ClockPort) -> BrokerPort: ...
   def get_market_data(name: str, config: MarketDataConfig, *, clock: ClockPort) -> MarketDataPort: ...
   ```
   The registry maps broker names to factory functions. Importing the registry is the **only** path outside `blive.adapters.*` that knows which broker names exist; strategies, the Sizer, the RiskEngine, and the runtime never enumerate brokers directly.

5. **Strategy-broker binding.** The strategy loader resolves `LiveStrategyConfig.broker` via the registry before constructing the rest of the pipeline. A single blive process can run multiple strategies on different brokers simultaneously — each strategy holds its own `BrokerPort` instance from the registry; the registry caches per-(broker, account) connections so multiple strategies on the same demo account share a connection.

6. **Inventory tracking.** [INV-6 §2.1, §2.2](../inv/ports_adapters.md) widens to enumerate per-broker adapters as new rows. No new tables; broker dimension is just rows.

7. **Import-linter contract amendment.** The existing `Domain layer is broker-neutral (ADR-004)` contract stays unchanged. A **new** contract is added: `Broker registry isolation (ADR-034)` — only `blive.runtime.broker_registry` may import from `blive.adapters.{paper,ig,ib}.*`; no other `blive.runtime.*` or `blive.strategy.*` module may. Enforced via `lint-imports`.

### Alternatives Considered

1. **Implicit dispatch via type-checking at strategy-load time** (e.g. "if `LiveStrategyConfig.ig_config` is set, use IG; else `ib_config` → IB; else paper"). Rejected: encodes selection in config presence rather than declaration; surprises if multiple `_config` blocks are present; doesn't extend cleanly to runtime broker switching.
2. **Strategy module imports its broker adapter directly** ("the strategy's `build_strategy()` returns the `BrokerPort` it wants"). Rejected: violates [ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement) (strategies depend on Ports, not adapters); makes strategies broker-coupled; defeats the abstraction.
3. **Plugin-discovery via `setuptools` entry points.** Rejected for v1: adds installation-time complexity; the static `{paper, ig, ib}` set is small enough that explicit factory dispatch is clearer; revisit at M8+ if a third-party adapter ecosystem emerges.

### Consequences

- **Positive:** adding a new broker is mechanical — implement four modules under `blive.adapters.{name}.*`, register the factory in `broker_registry`, add a config block to DD-3, add KB pair, add INV-6 rows. No domain-side changes; no `runtime` changes.
- **Positive:** strategy YAML clearly declares which broker; per-broker config lives in its own block; multi-broker support is a property of the architecture, not bolted on.
- **Positive:** the contract is enforceable via `import-linter` — drift detected at CI time, not runtime.
- **Negative:** more substrate per broker (4 modules + 1 KB pair + 1 DD entry + 1 INV-6 entry); justified by "we expect more brokers, not fewer".
- **Negative:** the strategy YAML changes shape (top-level `broker` required) — a minor breaking change to [DD-3](../dd/config_schemas.md), mitigated by giving M1's PaperBroker `broker: "paper"` as the migration path.
- **Negative:** the registry adds an indirection between "load strategy" and "construct broker" that wasn't present in M1.
- **Follow-ups:**
  - [DD-3 §1](../dd/config_schemas.md#1-livestrategyconfig-top-level) amendment: top-level `broker` field + per-broker config blocks. M1 tests need a one-line addition (`broker: "paper"`).
  - [INV-6 §2.1, §2.2](../inv/ports_adapters.md) amendments: enumerate IG (new) + IB (PARKED) + Paper rows.
  - `pyproject.toml` import-linter amendment: new contract `Broker registry isolation (ADR-034)`.
  - New module: `blive.runtime.broker_registry` (M2-IG.2 deliverable).
  - The [ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) rate limiter relocates from "`blive.adapters.ib.rate_limiter`" to "`blive.adapters.shared.rate_limiter`" — that ADR's body update should accompany this one's ACCEPTED flip, or be captured as an amendment ADR if append-only discipline applies.

### Cross-References

- [ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement) — hexagonal architecture this ADR extends.
- [ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) — rate limiter; this ADR generalises its module location.
- [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets) — secrets handling (paired with this ADR).
- [DD-3](../dd/config_schemas.md) — config schemas (amendment forthcoming in M2-IG.1 batch 2).
- [INV-6](../inv/ports_adapters.md) — port catalogue + adapter tracker (amendment).
- [TASK_REGISTRY](../../TASK_REGISTRY.md) M2-IG — the active milestone informed by this ADR.

---

## ADR-035 — Secrets handling discipline (`~/.blive/secrets/`)

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** —

### Context

[REQUIREMENTS §6.3](../../REQUIREMENTS.md#63-security--audit) commits to "credentials in OS keyring or env; never in repo or logs (log redaction list enforced)". The IG bridge ([TASK_REGISTRY](../../TASK_REGISTRY.md) M2-IG) brings the first concrete credentials surface — IG demo API key + username + password + account id — and the operator-pasted-them-in-chat moment confirmed we need explicit substrate, not implicit "we'll handle it when we get there".

Implicit "handle later" is a known anti-pattern; secrets discipline rots into "the test harness happens to read from an env var that nobody documented" and from there into "credentials end up in CI logs". This ADR fixes the shape before any code touches a credential.

### Decision

1. **Storage location.** Credentials live at `~/.blive/secrets/{broker}.env` outside the repo. One file per broker (e.g. `ig.env`, `ib.env`). KEY=VALUE format readable by `python-dotenv` or shell. File permissions `chmod 600` (operator's responsibility on Linux/macOS; on Windows, NTFS user-only ACL — documented when [`RUNBOOK.md`](../../RUNBOOK.md) lands at M5).

2. **Loading mechanism.** `blive.adapters.shared.credentials.load_credentials(broker_name) -> Credentials` reads the appropriate `~/.blive/secrets/{broker}.env`, validates required keys per the broker's schema (declared in `blive.adapters.{broker}.credentials`), and returns a frozen dataclass. **Env vars take priority over file values** — this lets Docker / systemd / CI inject credentials without writing files.

3. **Per-broker schema.** Each broker adapter declares its credential schema as a frozen dataclass in `blive.adapters.{broker}.credentials`:
   - **IG**: `IG_API_KEY`, `IG_USERNAME`, `IG_PASSWORD`, `IG_ACCOUNT_ID`, `IG_ENVIRONMENT ∈ {"demo", "live"}`.
   - **IB**: `IB_HOST`, `IB_PORT`, `IB_CLIENT_ID`, `IB_PAPER_ACCOUNT_ID` (no password — IB Gateway handles auth via IBC per [KB-3 §5](../kb/ib_pacing_spec.md#5-daily-and-weekly-operational-events)).
   - **Paper**: empty (no credentials needed).

4. **Repo discipline.**
   - No credentials in git history (the inverse — committing a real secret — is a security incident requiring rotation, not a typo).
   - No credentials in tests; unit tests use mocked `Credentials` instances; integration tests against demo accounts pull from `~/.blive/secrets/`.
   - No credentials in commit messages, ADRs, OQs, or any `docs/` artefact.
   - A `secrets/` directory at repo root holds **example files** with placeholder values: `secrets/ig.env.example`, `secrets/ib.env.example`. Real `.env` files live outside the repo. `.gitignore` blocks `secrets/*.env` (only `.example` files committed).

5. **Log redaction.** A new `blive.utils.logging` module (M2-IG.2 deliverable) maintains a redaction list of credential field names (constructed from the union of every broker's credential-schema fields). Any log message containing a value matching a redaction-list key gets the value replaced with `[REDACTED]` before emission. The list is populated at process start by walking `blive.adapters.{paper,ig,ib}.credentials` schemas.

6. **Chat / transcript discipline (operational, not enforceable in code).** Credentials shall not be pasted into Claude Code conversations or any tool whose transcripts are logged externally. When credentials need to be communicated (e.g. operator → blive process), the channel is the `~/.blive/secrets/` files. Claude does not echo credentials it has been told and does not write them into any file in the repo.

### Alternatives Considered

1. **OS keyring as default** (Windows Credential Manager / macOS Keychain / Secret Service via the `keyring` Python package). Rejected as default: keyring is per-user-session and complicates Docker deployment; the file path is portable across host and container with a volume mount. Keyring remains an opt-in path via a future `KEYRING_BACKEND=…` env var; not v1.
2. **Plain env vars only.** Rejected: env vars work but are awkward for many keys; `.env` files are more ergonomic for the operator.
3. **HashiCorp Vault or equivalent.** Rejected for v1: massive overkill for a single-operator setting. Worth revisiting only if the project goes multi-operator.

### Consequences

- **Positive:** credentials never enter git history; each broker's credential schema is explicit; loading is one call.
- **Positive:** redaction protects against accidental log leaks (developer-side). The discipline is auditable.
- **Positive:** migration path to OS keyring or Vault is clean — swap the loader implementation; the schema dataclasses don't change.
- **Negative:** operator must maintain `~/.blive/secrets/` files manually (acceptable for v1 single-operator; flagged for the [`RUNBOOK.md`](../../RUNBOOK.md) draft at M5).
- **Negative:** Docker deployment requires volume mount for `~/.blive/secrets/` — documented at M5 alongside `RUNBOOK.md`.
- **Negative:** redaction list maintenance is manual; new credential keys must be added when new brokers land — the union-walk at process start makes drift detectable but not prevented.
- **Follow-ups:**
  - `.gitignore` rule: `secrets/*.env` (block all but `.example` files).
  - `secrets/.gitkeep` + `secrets/ig.env.example` + `secrets/ib.env.example` committed at first M2-IG.2 code session.
  - `blive.utils.logging` module with redaction; M2-IG.2 deliverable.
  - `blive.adapters.shared.credentials` loader; M2-IG.2 deliverable.
  - Each broker's `credentials.py` schema; M2-IG.3 (IG) / M2-IB resumption (IB).

### Cross-References

- [REQUIREMENTS §6.3](../../REQUIREMENTS.md#63-security--audit) — credentials policy.
- [ADR-034](#adr-034--multi-broker-registry-pattern-extends-adr-004) — multi-broker registry; this ADR is its operational pair.
- [INV-6 §1.1](../inv/ports_adapters.md#11-brokerport) — `BrokerPort` (consumes credentials at construction).
- [TASK_REGISTRY](../../TASK_REGISTRY.md) M2-IG — first milestone using this discipline.

---

## ADR-036 — IG wire-level driver: roll-our-own httpx + asyncio Lightstreamer

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** —

### Context

[ADR-034](#adr-034--multi-broker-registry-pattern-extends-adr-004) commits blive to multi-broker support; the IG bridge (M2-IG) is the first non-paper broker landing. IG Markets exposes its API via two channels:

- **REST** for connection management, account queries, instrument search, and order placement (`POST /session`, `GET /accounts`, `GET /positions`, `POST /positions/otc`, `GET /markets`, `GET /prices`, etc.).
- **Lightstreamer** (a streaming protocol over HTTP) for live price subscriptions and trade-update events.

Two driver options:

1. **`trading_ig`** — community Python wrapper for IG. Sync-leaning (uses `requests`); ~600 GitHub stars; reasonably maintained but the asyncio story is awkward.
2. **Roll our own** — `httpx` for async REST + an asyncio Lightstreamer client.

### Decision

**Roll our own.** Concretely:

- **REST client**: `httpx.AsyncClient` for async HTTP. The IG API surface needed for v1 is small (~10 endpoints); a focused module is cleaner than wrapping a sync library.
- **Lightstreamer client**: official IG-recommended `lightstreamer-client-lib` (Python; supports asyncio). Streaming subscriptions wrapped per-instrument inside `IGMarketData`.
- **Module location**: `blive.adapters.ig.client.IGClient` owns auth state (CST + X-SECURITY-TOKEN headers); used by both `IGBroker` and `IGMarketData`.
- **Auth flow**: `IGClient.connect()` performs the 3-step REST auth (`POST /session` → header tokens stored), and starts a Lightstreamer session using the same credentials. `IGClient.close()` calls `DELETE /session`. Token TTL is 6 h on demo / 24 h on live; auto-refresh via `POST /session/refresh-token` on 401.
- **Rate limiting**: outbound REST calls go through `blive.adapters.shared.rate_limiter` ([ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters), now broker-agnostic per [ADR-034](#adr-034--multi-broker-registry-pattern-extends-adr-004)) configured per [ADR-038](#adr-038--ig-rate-limit-defaults-parameterise-adr-031).
- **Error handling**: HTTP errors mapped to typed engine exceptions (`IGAuthError`, `IGRateLimited`, `IGOrderRejected`, `IGSessionExpired`, …) at the adapter boundary. Specific code mapping in [KB-17](../kb/ig_pacing_spec.md) §"Error codes".
- **Dependencies pinned in `pyproject.toml`**: `httpx>=0.27,<0.28`, `lightstreamer-client-lib>=2.0` (verify exact pin at first install).

### Alternatives Considered

1. **`trading_ig`.** Sync model fights [ADR-005](#adr-005--single-process-single-asyncio-loop-kernel-for-v1) (single asyncio loop). Wrapping in `asyncio.to_thread` adds threading concerns we just got rid of in M0. The library also pulls `pandas`/`requests` we'd otherwise control narrowly. Rejected.
2. **CCXT.** IG is not a CCXT-supported venue. Rejected.
3. **gRPC sidecar wrapping `trading_ig`.** Operationally heavy; defers the asyncio mismatch rather than solving it. Rejected.

### Consequences

- **Positive:** asyncio-native; clean fit with [ADR-005](#adr-005--single-process-single-asyncio-loop-kernel-for-v1); narrow dependency surface (`httpx`, `lightstreamer-client-lib`); errors mapped to typed exceptions at the boundary.
- **Positive:** "small enough to read" — ~10 REST endpoints + Lightstreamer subscriptions is bounded.
- **Negative:** more code to write and maintain than wrapping an existing library. Justified by the small surface area.
- **Negative:** Lightstreamer is a non-trivial protocol; we depend on `lightstreamer-client-lib` for the streaming layer. If that library stalls, vendor-fork plan flagged for OQ at first sign of trouble.
- **Follow-ups:**
  - `IGClient` module + `IGAuthError`/`IGRateLimited`/etc. typed-exception hierarchy in M2-IG.3.
  - First-pass `INV-?` IG error-code inventory drafted from observed responses; analogous to MISSING [INV-14](../inv/ib_error_codes.md) for IB.
  - Pin verification: `httpx` and `lightstreamer-client-lib` versions confirmed at first install.

### Cross-References

- [ADR-002](#adr-002--adopt-ib_async-v21-as-wire-level-ib-driver) — IB analogue (we adopted a wrapper for IB; for IG no good wrapper exists).
- [ADR-005](#adr-005--single-process-single-asyncio-loop-kernel-for-v1) — single-loop asyncio commitment.
- [ADR-034](#adr-034--multi-broker-registry-pattern-extends-adr-004) — multi-broker registry; this driver lives under that pattern.
- [ADR-038](#adr-038--ig-rate-limit-defaults-parameterise-adr-031) — IG rate-limit defaults consumed by this driver.
- [KB-17 IG pacing spec](../kb/ig_pacing_spec.md) — DRAFT this batch.

---

## ADR-037 — `Instrument.tradability` field (spot / cfd / spread_bet)

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none (extends [DD-1 §2.1](../dd/domain_objects.md#21-instrument))
- **resolves:** —

### Context

[DD-1 §2.1](../dd/domain_objects.md#21-instrument) defines `Instrument(symbol, venue, currency, asset_class, multiplier)` as the broker-neutral identity of a tradable thing. The `asset_class` enum has `EQUITY`, `ETF`, `INDEX`, `FX`, `FUTURE`, `OPTION`. None of these distinguish *how* the instrument is held: an `ETF` `Instrument` could be physical shares (cash equity), or a CFD on the same underlying, or a spread bet — three very different cost / leverage / settlement / tax profiles.

The IG bridge ([M2-IG](../../TASK_REGISTRY.md)) turns this abstract concern into a concrete one: `CAC.PA` ETF on IB ([ADR-021](#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf)) and `IX.D.CAC40.CASH.IP` CFD on IG are both broadly "CAC 40 exposure" but they're not interchangeable instances of `Instrument`. The Sizer's [ADR-027](#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero) integer-share rounding is correct for ETF shares and wrong for CFDs (which allow fractional contracts).

### Decision

Add `tradability: Literal["spot", "cfd", "spread_bet"] = "spot"` to `Instrument` ([DD-1 §2.1](../dd/domain_objects.md#21-instrument)) as a new field with default value, backward-compatible.

Semantics:

- **`"spot"`** — physical position in the underlying; cash equity / ETF / direct FX / direct futures contract. ADR-027 integer-share rounding applies. This is the M0+M1 default; no existing `Instrument` construction needs to change.
- **`"cfd"`** — Contract for Difference; fractional position size allowed; per-instrument precision (e.g. 0.01 for CAC 40 CFD on IG; 0.1 for some FX CFDs). The Sizer's quantize step uses an instrument-derived precision instead of the integer-share rule. Overnight financing applies.
- **`"spread_bet"`** — UK spread bet; sized in £/point; tax-free for UK retail. Quantize step uses pence-per-point precision. Overnight financing applies.

The Sizer's `quantize_share_qty(raw, *, precision=Decimal("1"))` already accepts a `precision` parameter; the change is at the *call site* — it picks `Decimal("1")` for `tradability=="spot"` and `Decimal("0.01")` (or whatever the instrument declares) for CFDs / spread bets.

The `Instrument` identity tuple ([DD-1 §2.1](../dd/domain_objects.md#21-instrument) "Equality / hashing") widens to include `tradability` — `CAC.PA` ETF and `IX.D.CAC40.CASH.IP` CFD are distinct `Instrument`s.

### Alternatives Considered

1. **Encode tradability in `venue`** (e.g. `venue="IG_DEMO_CFD"`). Rejected: conflates the venue (where the instrument trades) with the broker primitive (how it's held). Two separate concerns that should not be smashed into one field.
2. **Encode tradability in `asset_class`** (e.g. add `CFD`, `SPREAD_BET` enum members). Rejected: a CFD on `EQUITY` and a CFD on `INDEX` are still meaningfully different at the asset-class level; `tradability` is orthogonal to `asset_class`.
3. **Parallel `Instrument` types** (e.g. `CFDInstrument`, `SpreadBetInstrument`). Rejected: explodes the domain-type surface; the broker-neutral identity is one type, and tradability is just a discriminator on it.
4. **Defer the decision; have the Sizer call broker-specific code paths.** Rejected: violates [ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement) (Sizer is domain code; adapters are not).

### Consequences

- **Positive:** backward-compatible (default `"spot"`); M0+M1 tests need no change. The CAC.PA ETF `Instrument` continues to construct without tradability and defaults to `"spot"`.
- **Positive:** minimal expansion to the type surface; one field, one enum literal, zero new dataclasses.
- **Positive:** Sizer rule branches on `tradability`, not on broker — domain-side; broker-neutral.
- **Negative:** [DD-1 §2.1](../dd/domain_objects.md#21-instrument) and `src/blive/domain/types.py` need to be amended. DD-1 stays STABLE because the change is additive with default; `types.py` add the field; existing tests construct `Instrument(...)` without keyword-args other than the original five and continue to work.
- **Negative:** the Sizer has a new branching rule; per-instrument precision needs to be sourced from somewhere (probably an `IGInstrumentMetadata` mapping inside the IG adapter, or an extra field on `Instrument`). Resolved at M2-IG.2 / .3 time.
- **Follow-ups:**
  - DD-1 amendment (STABLE v0.1 → v0.2) lands in M2-IG.2 alongside the `types.py` change. Same commit.
  - Sizer ([`src/blive/sizing/sizer.py`](../../src/blive/sizing/sizer.py)) gets a per-instrument precision lookup. Open: where does precision live — on `Instrument`, on `LiveStrategyConfig`, or fetched from the broker adapter? Default lean: `Instrument.precision` field (broker-neutral, simple); revisit if a single instrument needs different precisions per broker (unlikely).
  - [`tests/conftest.py`](../../tests/conftest.py) `cac_pa` fixture stays unchanged (defaults `"spot"`); a new `cac40_cfd` fixture lands at M2-IG.3.

### Cross-References

- [DD-1 §2.1](../dd/domain_objects.md#21-instrument) — `Instrument` shape (amendment forthcoming in M2-IG.2).
- [ADR-021](#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) — CAC.PA ETF (PAUSED for the bridge per ADR-039).
- [ADR-027](#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero) — integer-share rounding (now scoped to `tradability=="spot"`).
- [ADR-034](#adr-034--multi-broker-registry-pattern-extends-adr-004) — multi-broker registry; the IG vs IB distinction surfaces this need.
- [ADR-039](#adr-039--phase-1-strategy-under-ig-bridge-cac-40-cfd) — Phase 1 under bridge (uses `tradability="cfd"`).

---

## ADR-038 — IG rate-limit defaults (parameterise ADR-031)

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none (parameterises [ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters))
- **resolves:** —

### Context

[ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) defined a two-level token-bucket rate limiter with **IB-specific defaults** (20 msg/sec global, 5 msg/sec per-strategy) sourced from [KB-3 §1, §9](../kb/ib_pacing_spec.md). [ADR-034](#adr-034--multi-broker-registry-pattern-extends-adr-004) generalised the limiter's location (`blive.adapters.shared.rate_limiter`) but left per-broker default budgets unspecified.

IG's published limits — see [KB-17 IG pacing spec](../kb/ig_pacing_spec.md) — are roughly an order of magnitude tighter than IB's, and have a different shape: per-minute buckets, separate buckets for trading vs general vs historical, plus a Lightstreamer subscription budget.

### Decision

Make the [ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) rate limiter accept a **per-bucket configuration table** at construction time, and ship the IG defaults in `blive.adapters.ig`. Concretely:

```python
@dataclass(frozen=True)
class RateLimitBucket:
    capacity: int
    refill_per_second: Decimal

@dataclass(frozen=True)
class RateLimitConfig:
    buckets: Mapping[str, RateLimitBucket]  # keyed by bucket name
```

The IG defaults (`blive.adapters.ig.rate_limiter.IG_DEFAULT_RATE_LIMITS`):

| Bucket | Capacity | Refill | Source |
|---|---|---|---|
| `global` | 30 | 0.5 / s (= 30/min) | IG REST general; [KB-17 §1](../kb/ig_pacing_spec.md) |
| `trading` | 60 | 1.0 / s (= 60/min) | IG REST trading endpoints (`/positions/otc`, `/workingorders/otc`); [KB-17 §1](../kb/ig_pacing_spec.md) |
| `historical_prices` | 40 | 2/3 per s (= 40/min) | IG REST `/prices`; [KB-17 §1](../kb/ig_pacing_spec.md) |
| `lightstreamer_subscriptions` | 40 | n/a (concurrent budget, not a refill bucket) | [KB-17 §3](../kb/ig_pacing_spec.md) |

Each call site declares which bucket it draws from — e.g. `IGBroker.submit()` consumes from `trading`; `IGMarketData.historical_bars()` consumes from `historical_prices`; everything else from `global`. The `lightstreamer_subscriptions` "budget" is enforced as a concurrent-subscription counter inside `IGMarketData`, not the token-bucket algorithm (no refill semantics).

The IB defaults (`blive.adapters.ib.rate_limiter.IB_DEFAULT_RATE_LIMITS`) preserve [ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) values: `global` 20/s, `per_strategy_*` 5/s, etc. They live in the parked M2-IB code surface (not implemented yet) but the config shape is now uniform.

Per-strategy overrides are admitted via [DD-3 §7 RiskOverrides](../dd/config_schemas.md#7-riskoverrides) when M4 widens that section; M2 reads constructor defaults only.

### Alternatives Considered

1. **Hardcode IG defaults in the limiter.** Rejected: makes the limiter broker-aware, breaks the shared-module abstraction.
2. **Per-broker subclasses of the rate limiter.** Rejected: the algorithm is shared; only the config differs.
3. **Single global ceiling, ignore per-bucket distinctions.** Rejected: IG's trading/general/historical buckets really are separate at the IG side; a single ceiling either over-throttles trading or under-throttles general.

### Consequences

- **Positive:** uniform algorithm across brokers; per-broker config localised in the broker's own module; the [G3-IG throttle test](../../TASK_REGISTRY.md) exercises the limiter with real IG defaults.
- **Positive:** the limiter stays in `blive.adapters.shared.rate_limiter`; no broker-specific code in domain or runtime.
- **Negative:** the limiter is now slightly more configurable than the M2-IB ADR-031 needed; minor over-engineering justified by "we now have two brokers".
- **Follow-ups:**
  - The [ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) body's "Public surface" sketch was per-strategy-only; it widens to the named-bucket shape under this ADR. Documented as a cross-reference here; ADR-031's body stays unchanged (append-only), readers follow the cross-ref.
  - `IGMarketData` Lightstreamer subscription counter implementation in M2-IG.3.
  - When M4 surfaces `RiskOverrides.max_orders_per_sec_strategy` etc., the IG strategy defaults (60/min) are the cap; per-strategy config can only narrow, not widen.

### Cross-References

- [ADR-031](#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters) — algorithm and shape; this ADR parameterises its config.
- [ADR-034](#adr-034--multi-broker-registry-pattern-extends-adr-004) — multi-broker registry; rate limiter relocation.
- [KB-17 §1, §3](../kb/ig_pacing_spec.md) — DRAFT this batch; numerical source.
- [INV-4 RC-05, RC-06](../inv/risk_checks.md) — order-rate risk checks (M4 widens to consume per-broker config).
- [TASK_REGISTRY](../../TASK_REGISTRY.md) M2-IG G3-IG gate — throttle test references these defaults.

---

## ADR-039 — Phase 1 strategy under IG bridge: CAC 40 CFD

- **status:** ACCEPTED
- **date:** 2026-04-27
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** —

### Context

The Phase 1 plan ([TASK_REGISTRY](../../TASK_REGISTRY.md)) was: run `tkan_v4_momentum_timing` 1× as the `CAC.PA` ETF on IB Paper, ±1 bps parity vs btest, ≥ 5 trading days, 5–10% NAV slice. The 2026-04-27 IG bridge pivot needs an explicit answer to: **what is the strategy's tradable instrument under the bridge, and what does "the strategy works on IG demo" mean concretely?**

Three things change under the bridge:

1. **Instrument.** IG retail UK accounts trade CFDs and spread bets, not actual ETF shares. The closest CAC 40 exposure is a CAC 40 cash CFD (`tradability="cfd"` per [ADR-037](#adr-037--instrumenttradability-field-spot--cfd--spread_bet)).
2. **Cost model.** CFDs charge daily overnight financing (tom-next or similar) instead of (or in addition to) the ETF's internal swap cost. Btest's [`FinancingCost`](../kb/cost_margin_dictionary.md#5-financingcost) handles the financing curve, but CFD-specific spread is a new component.
3. **Parity envelope.** The G2-IB ±1 bps target was tight because the only legitimate divergence was share-rounding ([ADR-027](#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero)). CFD financing-cost variability (intraday tom-next moves; weekend financing rolls) makes ±1 bps unachievable. The bridge needs a different envelope.

### Decision

1. **Tradable instrument.** `Instrument(symbol="CAC40", venue="IG_LDN", currency="EUR", asset_class=AssetClass.INDEX, tradability="cfd")` resolved by [DD-8](../dd/ig_instrument_dictionary.md) to IG epic — first guess `IX.D.CAC40.CASH.IP`, confirmed against `/markets?searchTerm=CAC%2040` on first IG handshake. The exact symbol/venue/currency triple may shift when the handshake confirms; this ADR locks the *concept*, not the keys.
2. **[ADR-021](#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) status: PAUSED** (not SUPERSEDED). The CAC.PA ETF path resumes when IB returns; ADR-021's choice is still correct for that path. The bridge runs in parallel.
3. **NAV slice**: unchanged — 5–10% per [ADR-020](#adr-020--phase-1-nav-slice-510-of-total-cap-10), hard cap 10%. CFD leverage built into the contract is irrelevant to NAV-slice computation; we slice account equity, not gross exposure.
4. **Cost model**: btest's `FinancingCost` curve handles base rate (ESTER); CFD financing spread adds ~25–50 bps annualised on top — provided as a `LiveFinancingProvider` override per [DD-3 §4](../dd/config_schemas.md#4-livefinancingprovider) when the bridge runs. Exact spread observed from IG `/positions` at first run; documented in [`docs/retros/M2-IG_retrospective.md`](../retros/) for future reference.
5. **Parity envelope**: the ±1 bps target is **not** the M2-IG.5 success criterion. Instead:
   - **Directional alignment**: every rebalance day's signed position matches btest's signed position (sign-only test). This is the strongest claim under CFD friction.
   - **Magnitude envelope**: end-of-period equity-curve divergence < 100 bps over the 5-day run, with the gap *characterised* (financing cost vs spread vs share-rounding-on-CFD-fractional-precision). The "characterised" requirement is harder than just "< 100 bps"; we need to attribute the residual.
   - The full parity diagnostic ([ADR-012](#adr-012--parity-diagnostic-mandatory-daily-degraded-mode-if-broken)) for M7 can absorb CFD-specific decomposition; M2-IG.5 is a sanity check, not a calibration.
6. **TKAN artefact**: unchanged. [ADR-022](#adr-022--tkan-artefact-freshness-window-30d-hard-21d-warning), [ADR-023](#adr-023--tkan-artefact-path-and-refresh-ownership) apply identically; broker-agnostic.
7. **Sizer rounding**: per [ADR-037](#adr-037--instrumenttradability-field-spot--cfd--spread_bet) `tradability="cfd"` rule — fractional contracts at the IG-instrument's declared precision (CAC 40 CFD on IG is typically 0.01 contract minimum; verified at first handshake).

### Alternatives Considered

1. **Skip the strategy, just exercise IG read-side connectivity.** Rejected: operator's intent is "exercise the broker abstraction with a real venue end-to-end". Stopping at read-side leaves the multi-broker abstraction untested under writes.
2. **Different instrument** (e.g. SP500 CFD on IG). Rejected: changes more variables than necessary; the strategy is calibrated against CAC; staying with CAC isolates the broker / tradability variables.
3. **Spread bet instead of CFD.** Rejected as default for v1 bridge: spread-bet sizing in £/point is more friction; CFD aligns better with the existing notional-EUR strategy mental model. Spread-bet path remains an option later.
4. **Tighter parity envelope (e.g. ±10 bps).** Rejected: financing-cost variability at IG demo over 5 trading days can exceed 10 bps just from the demo's idiosyncratic financing curve. 100 bps is the right "sanity check, not calibration" envelope.

### Consequences

- **Positive:** the bridge has a concrete, falsifiable success criterion that doesn't require chasing a parity envelope that's not achievable on CFDs anyway.
- **Positive:** ADR-021 stays valid for IB return; no decision is reversed; the bridge is a parallel track.
- **Negative:** the M2-IG.5 retro will record a CFD-financing characterisation that doesn't directly inform the M2-IB / M3 future ±1 bps target. Some M2-IG learning is bridge-specific.
- **Negative:** CFD financing is an additional cost component the operator hasn't seen in btest historical results; the strategy's net P&L on IG demo will differ from btest's net P&L by a non-trivial margin even when "directionally aligned".
- **Follow-ups:**
  - First IG handshake confirms the CAC 40 CFD epic; DD-8 row updated.
  - First IG `/positions` query records the demo's actual financing rate; documented.
  - Sizer per-instrument precision lookup: M2-IG.2/.3 work.
  - Strategy `LiveStrategyConfig` for the bridge: `~/.blive/strategies/tkan_v4_momentum_timing_1x_ig/live.yaml` with `broker: "ig"` per [ADR-034](#adr-034--multi-broker-registry-pattern-extends-adr-004) plus `live_financing_provider` override for IG's CFD financing curve. Concrete YAML lands in M2-IG.5.

### Cross-References

- [ADR-013](#adr-013--v1-scope-etf-and-index-strategies-only) — v1 scope (bridge phase exercises CFD; ETF path resumes when IB returns).
- [ADR-020](#adr-020--phase-1-nav-slice-510-of-total-cap-10) — NAV slice (unchanged).
- [ADR-021](#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) — CAC.PA ETF (PAUSED for the bridge).
- [ADR-022](#adr-022--tkan-artefact-freshness-window-30d-hard-21d-warning), [ADR-023](#adr-023--tkan-artefact-path-and-refresh-ownership) — TKAN artefact policy (unchanged).
- [ADR-034](#adr-034--multi-broker-registry-pattern-extends-adr-004), [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets) — multi-broker / secrets substrate.
- [ADR-037](#adr-037--instrumenttradability-field-spot--cfd--spread_bet) — `tradability="cfd"`.
- [DD-8 IG instrument dictionary](../dd/ig_instrument_dictionary.md) — DRAFT this batch.
- [TASK_REGISTRY M2-IG.5](../../TASK_REGISTRY.md) — strategy run + retro milestone.

---

## ADR-040 — Phase 1 deployment target: Windows host with native IB Gateway

- **status:** ACCEPTED
- **date:** 2026-04-28
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** —

### Context

[TASK_REGISTRY M2-IB §"Operator-side prerequisites"](../../TASK_REGISTRY.md) requires deciding the deployment target before M2-IB.3 first wire-level handshake. [REQUIREMENTS §12](../../REQUIREMENTS.md#12-operational-model) commits to "Linux preferred, Windows supported (the user runs Windows 11 daily; production target is Linux VM/box)" but does not pin the Phase 1 dev/paper-mode choice.

The decision matters because it drives:

- Whether IB Gateway runs in Docker (`gnzsnz/ib-gateway-docker` per [REQUIREMENTS §12](../../REQUIREMENTS.md#12-operational-model) + [KB-3 §5](../kb/ib_pacing_spec.md#5-daily-and-weekly-operational-events)) or as a native Windows process.
- Whether IBC ([KB-3 §5](../kb/ib_pacing_spec.md#5-daily-and-weekly-operational-events)) automates the daily 23:45 ET TWS restart or the operator handles it manually.
- How the [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets) `~/.blive/secrets/` discipline maps onto Windows NTFS ACLs vs Linux `chmod 600`.
- The latency / reliability profile of the M2-IB.5 ≥ 5-trading-day strategy run.

### Decision

For Phase 1 (M2-IB through M3 / G4 gate) use the **Windows host with native IB Gateway**, no Docker, no IBC. Concretely:

- Operator installs IB Gateway from the IB website (the "offline" installer per [KB-3 §5](../kb/ib_pacing_spec.md#5-daily-and-weekly-operational-events) recommendation).
- Operator launches IB Gateway manually, logs in to the paper account, leaves the process running.
- blive (running natively on Windows under `uv`) connects via TCP `127.0.0.1:4002`.
- Daily 23:45 ET restart is **operator-managed** for Phase 1: blive's [REQUIREMENTS §5.7](../../REQUIREMENTS.md#57-reconciliation) reconciliation loop already handles disconnect-then-reconnect; the operator just needs to log Gateway back in once a day during the M2-IB.5 5-day run.
- File permissions: `~/.blive/secrets/ib.env` lives at `C:\Users\olegr\.blive\secrets\ib.env`. Per-user-only NTFS ACL is the Windows analogue of `chmod 600`; Phase 1 relies on the file being inside the user profile (already access-controlled by the OS for non-admin processes). The full ACL hardening lands when [`RUNBOOK.md`](../../RUNBOOK.md) gets authored at M5 per [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets) §"Consequences".

Linux VM / Docker / IBC are **deferred to the production cutover at M8+** ([REQUIREMENTS §14](../../REQUIREMENTS.md) M8: "Hardening: ... ops runbook ... 2-week unattended paper trade clean").

### Alternatives Considered

1. **Linux VM with Docker (`gnzsnz/ib-gateway-docker` + IBC).** Rejected for Phase 1: operationally more standard and what the production cutover wants, but adds VM-host overhead, Docker-Desktop install, container-volume mounts for credentials, and a Linux-side ops layer that the user has not yet picked. The complexity is appropriate when the cutover to live trading is in scope (M8+); paying it now buys nothing for paper-mode dev. [REQUIREMENTS §12](../../REQUIREMENTS.md#12-operational-model)'s "Linux preferred" guidance applies to the production target, not the Phase 1 paper-mode workflow.
2. **WSL2 with Docker on Windows.** Considered as a hybrid. Lower friction than a full VM but still adds a container layer + IBC config. Worth re-evaluating at M5 when the operational story matures; not needed for Phase 1.
3. **TWS Desktop instead of IB Gateway.** Rejected: TWS has the same daily-restart and pacing characteristics ([KB-2 §1](../kb/ib_capability_matrix.md#1-connectivity-surface)), heavier UI, no operational benefit for headless-style automation. Gateway is the standard for API-only workflows.

### Consequences

- **Positive:** Lowest possible setup friction for the M2-IB.3 first handshake. Operator runs IB Gateway, fills in `~/.blive/secrets/ib.env`, runs blive's smoke probe — three steps, no VM / Docker / IBC config.
- **Positive:** No new dependencies or container-runtime requirements. blive runs the same way it has since M0 (`uv run`, native Windows process).
- **Positive:** Decision is reversible — switching to a Linux VM at M8 doesn't invalidate Phase 1 work; the abstraction layers (broker registry, IBClient, IBCredentials) are deployment-target-agnostic.
- **Negative:** Daily 23:45 ET TWS-restart window requires operator attention during the M2-IB.5 ≥ 5-trading-day strategy run. Acceptable for Phase 1 (paper, single-operator, dev workflow); blive's reconciliation handles the disconnect/reconnect transient correctly per [REQUIREMENTS §5.7](../../REQUIREMENTS.md#57-reconciliation).
- **Negative:** NTFS-ACL credential-file hardening is deferred (per [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets) "Consequences" already flagged for M5). Phase 1 risk is bounded by the file living inside the user profile and the system being a single-operator workstation.
- **Negative:** Re-doing the deployment at M8 will require a fresh setup pass on the Linux VM (Docker + IBC + secret-volume-mounts + systemd / `restart: always`); documented but not pre-built.
- **Follow-ups:**
  - M2-IB.3 first-handshake validation runs on the Windows native target.
  - [`RUNBOOK.md`](../../RUNBOOK.md) (M5) documents the Linux VM / Docker path as the production target with concrete steps.
  - Re-evaluate at the [G4 → Phase 2 readiness audit](../../CONTEXT_PROTOCOL.md#832-phase-boundary-rule) whether Phase 2 strategies justify the Linux migration earlier.
  - The existing [TASK_REGISTRY M2-IB §"Operator-side prerequisites"](../../TASK_REGISTRY.md) "Decide deployment target" item is closed by this ADR.

### Cross-References

- [REQUIREMENTS §12](../../REQUIREMENTS.md#12-operational-model) — operational model (Linux preferred for production).
- [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets) — secrets handling (NTFS ACL note).
- [KB-3 §5](../kb/ib_pacing_spec.md#5-daily-and-weekly-operational-events) — daily TWS restart + IBC + offline installer.
- [KB-8 §1](../kb/operational_events.md#1-daily-tws--ib-gateway-restart) — daily restart engine response.
- [TASK_REGISTRY M2-IB](../../TASK_REGISTRY.md) — M2-IB.3 prerequisite this ADR resolves.

---

## ADR-041 — Yahoo-suffix translation in IB instrument resolver

- **status:** ACCEPTED
- **date:** 2026-05-01
- **decider:** Oleg (with Claude)
- **supersedes:** none (refines [ADR-032](#adr-032--instrument-resolution-policy-blive-instrument--ib-contract))
- **resolves:** —

### Context

The M2-IB.3a `IBInstrumentResolver.resolve()` wire-level smoke test
([`scripts/probe_ib_resolve_contract.py`](../../scripts/probe_ib_resolve_contract.py))
ran against IB Paper Gateway 2026-05-01 with the Phase 1 instrument
`Instrument(symbol="CAC.PA", venue="XPAR", currency="EUR", asset_class=ETF, tradability="spot")`
and **failed** with IB error 200 (`No security definition has been
found for the request, contract: Contract(secType='STK', symbol='CAC.PA', exchange='SBF', currency='EUR')`).

A diagnostic probe of alternate symbols on `SBF` showed:

| Symbol attempted | IB result |
|---|---|
| `CAC.PA` | error 200 (unknown contract) |
| `CAC` | **resolved**, `conId=11183823`, `primaryExchange=SBF` |
| `LYXCAC` | error 200 |
| `CAC40` | error 200 |

The `.PA` suffix is **Yahoo Finance / EODHD convention** for "this ticker is listed on Euronext Paris". IB's TWS API expects the **bare exchange ticker**. The same convention applies to other European venues — `BARC.L` on Yahoo / EODHD is `BARC` on IB's `LSE`; `SAP.DE` is `SAP` on `IBIS`.

[ADR-021](#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) names the Phase 1 instrument as `CAC.PA` (matching the EODHD historical-data fixture path); btest's strategy module receives the same broker-neutral `Instrument` and the parquet-backed [`PaperMarketData`](../../src/blive/adapters/paper/market_data.py) reads from a fixture keyed by that symbol. Changing the canonical symbol to `CAC` would break the EODHD path; keeping `CAC.PA` and translating in the IB adapter keeps the broker-neutral identity stable while satisfying IB's wire format.

### Decision

The IB resolver strips known **Yahoo Finance / EODHD exchange suffixes** from `Instrument.symbol` when the suffix matches the instrument's `venue` MIC, before constructing the `ib_async.Contract`. Implementation: a small constant table `_YAHOO_SUFFIX_BY_MIC` in [`blive.adapters.ib.instrument_resolver`](../../src/blive/adapters/ib/instrument_resolver.py) and a `_ib_symbol(instrument)` helper called by `to_contract`.

Phase 1 + adjacent rows ([DD-7 §3.1](../dd/instrument_dictionary.md#31-yahoo-finance--eodhd-exchange-suffix--mic)):

| MIC | Yahoo suffix | Example |
|---|---|---|
| `XPAR` | `.PA` | `CAC.PA` → `CAC` (validated; conId=11183823) |
| `XLON` | `.L` | `BARC.L` → `BARC` |
| `XETR` | `.DE` | `SAP.DE` → `SAP` |
| `XAMS` | `.AS` | (post-M8 candidate) |

Symbols **not** ending in their venue's Yahoo suffix pass through unchanged (e.g. `AAPL` on `XNAS`). Symbols with a Yahoo-style suffix on a non-matching MIC also pass through (e.g. `ABC.PA` on `XNAS` — `.PA` is XPAR-only convention; cross-venue stripping would be unsafe).

The translation lives **only** in the IB resolver. The broker-neutral `Instrument` retains its EODHD-friendly form so the same dataclass round-trips through btest's `parquet://` / `eodhd://` data sources without translation. This matches the discipline ADR-004 / ADR-032 establish: broker-specific quirks live in the broker adapter; the domain stays portable.

### Alternatives Considered

1. **Per-`Instrument` IB-side override field** (e.g. `Instrument.ib_symbol: str | None`). Rejected: bloats the broker-neutral type with broker-specific data; not symmetric across brokers; defeats the abstraction. The adapter is the right home for venue translation.
2. **Change the canonical Phase 1 `symbol` to `CAC`** and have the EODHD adapter add `.PA` when fetching. Rejected: requires re-authoring the btest strategy module; breaks the parquet-fixture path (`tests_slow/fixtures/paper_market_data/{venue}/CAC.PA_1d.parquet`); contradicts [ADR-021](#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) prose; the EODHD-suffix convention is what every research consumer of the data uses.
3. **Generic suffix-stripping heuristic** (any `.X` suffix on any venue). Rejected: false-positives. A symbol legitimately containing a dot (`BRK.A`, `BRK.B`) would be stripped incorrectly; the Yahoo convention is venue-specific by design.
4. **Lazy fallback: try literal symbol first, then strip on `error 200`**. Rejected: implicit fallback masks diagnostic value; the canonical `CAC.PA` → `CAC` mapping is stable and testable once-and-done.

### Consequences

- **Positive:** `Instrument(symbol="CAC.PA", venue="XPAR", ...)` resolves on IB Paper as expected; the broker-neutral identity stays unchanged; the EODHD / parquet data path is unaffected.
- **Positive:** Translation table is small, declarative, and lives next to the `_MIC_TO_IB_EXCHANGE` table it complements. New venues add a single row.
- **Positive:** Symmetric with the IG analogue's epic-construction logic (per [DD-8 §3](../dd/ig_instrument_dictionary.md)) — both adapters do venue-specific translation; neither leaks into the domain.
- **Negative:** The `_YAHOO_SUFFIX_BY_MIC` table is hand-curated; new venues need an explicit row when they land. Mitigated by the table being a one-line addition per venue and by the failing instrument producing a clear "zero candidates" error that points the operator at the missing row.
- **Negative:** Yahoo Finance occasionally renames suffixes (rare). When that happens, the symbol stops resolving on IB and the operator updates the row. No regression risk to non-IB paths.
- **Follow-ups:**
  - DD-7 §3.1 row added in this commit batch (Yahoo-suffix sub-table).
  - When Phase 2 / Phase 3 land US strategies, no Yahoo suffix needed (US listings on Yahoo are unsuffixed); the table only matters for European venues.
  - If a future strategy uses an instrument whose IB symbol differs from the bare-ticker form (rare; e.g. `BRK B` on NYSE), the per-instrument override is a possible escape hatch — re-evaluate at that point.

### Cross-References

- [ADR-004](#adr-004--hexagonal-portsadapters-with-import-linter-enforcement) — broker-neutrality contract; this translation honours it.
- [ADR-021](#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) — Phase 1 `CAC.PA` instrument unchanged.
- [ADR-032](#adr-032--instrument-resolution-policy-blive-instrument--ib-contract) — instrument resolution policy this ADR refines.
- [DD-7 §3.1](../dd/instrument_dictionary.md#31-yahoo-finance--eodhd-exchange-suffix--mic) — Yahoo-suffix sub-table.
- [`scripts/probe_ib_resolve_contract.py`](../../scripts/probe_ib_resolve_contract.py) — wire-level smoke test that surfaced the issue.

---

## ADR-042 — Session-bootstrap files: agent-agnostic pattern for L0 warm-up entry point

- **status:** ACCEPTED
- **date:** 2026-05-02
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **extends:** [ADR-026](#adr-026--adopt-agentic-execution-layer-reduce-human-action-surface)

### Context

[CONTEXT_PROTOCOL §8.1](../../CONTEXT_PROTOCOL.md) requires every session to begin with a warm-up read of the substrate. In practice this requires the operator to tell a fresh agent where to start every session — paste [`NEXT_PROMPT.md`](../../NEXT_PROMPT.md) or a reading list into the first message, or remind the agent to read [`CONTEXT_INVENTORY.md`](../../CONTEXT_INVENTORY.md) before editing. The friction is small per session but compounds: across many sessions and contributors it is a vector for skipped warm-up and for the drift modes the discipline catalogues in [CONTEXT_PROTOCOL §1](../../CONTEXT_PROTOCOL.md).

[ADR-026](#adr-026--adopt-agentic-execution-layer-reduce-human-action-surface) codified the agentic-execution stack (L0–L4). L0 — substrate-aware warm-up — was specified as "an agent that reads `CONTEXT_INVENTORY.md` and walks the `depends_on` closure". The simplest, ahead-of-tooling implementation of L0 is a static **session-bootstrap file**: a small markdown file at the project root that any agent harness loads automatically at session start (per its native config convention) and that points at the canonical substrate.

Most modern AI coding harnesses already load such a file. Claude Code reads `CLAUDE.md`; other harnesses use `AGENTS.md`, `.cursorrules`, system-prompt config, or analogous mechanisms. The discipline-relevant fact is that *the file exists and reliably loads* — the specific filename is a per-agent convention.

### Decision

Adopt **session-bootstrap files** as the canonical L0 implementation under the agentic-execution stack. The pattern is **agent-agnostic in semantics, platform-specific in filename**:

1. The project root contains one or more small bootstrap files, each tailored to a specific agent platform's loading convention.
2. Every bootstrap file is a *pointer* to the canonical substrate (CONTEXT_PROTOCOL, CONTEXT_INVENTORY, REQUIREMENTS, TASK_REGISTRY, NEXT_PROMPT, methodology paper) — not a copy. SSOT ([CONTEXT_PROTOCOL §2.1](../../CONTEXT_PROTOCOL.md)) applies; the protocol remains the single source of truth and bootstrap files drift back to it on review.
3. Bootstrap files articulate the **mandatory warm-up sequence** (per [CONTEXT_PROTOCOL §8.1](../../CONTEXT_PROTOCOL.md)), the **discipline at-a-glance** (stable IDs, ADR-mandatory choices, status lifecycle, anti-patterns), and **operator-action conventions** (when to ask vs. act).
4. Bootstrap files are versioned substrate artefacts subject to the edit protocol — frontmatter (`id`, `status`, `last_reviewed`, `version`, `depends_on`, `referenced_by`) is mandatory; `last_reviewed` bumps on every edit; commits list bootstrap files by stable id like any other artefact.

**Initial instance:** [`CLAUDE.md`](../../CLAUDE.md) at the repo root (Claude Code's auto-loaded project file). Future agent-specific instances (e.g. `AGENTS.md`, `.cursorrules`) are added as they are needed; each is a thin agent-specific shim around the same pointer set.

### Alternatives Considered

1. **Rely on operator to paste NEXT_PROMPT each session.** Current state. Friction; vector for skipped warm-up; doesn't survive contributor handoff or fresh-agent-instance.
2. **Pre-prompt hook** (e.g. `UserPromptSubmit` injecting a reminder). Noisy; user-machine-specific (lives in `~/.claude/settings.json`, not in repo); less durable than a repo-committed file.
3. **Restate the discipline in the bootstrap file** rather than pointing at it. Violates SSOT; the bootstrap would drift from CONTEXT_PROTOCOL and become a second-source-of-truth that contradicts the first.
4. **Single agent-agnostic file (`AGENTS.md` only).** Plausible, but each platform has its own loading convention; one-file-fits-all loses zero-config auto-load on platforms whose convention differs. Each platform getting a thin shim is cheaper than fighting the harness.
5. **Hardcode a richer L0 agent now** (per [OQ-028](OPEN_QUESTIONS.md#oq-028--which-agentic-memory-framework--tooling-for-l0l1)). Premature; OQ-028 / OQ-029 explicitly defer richer L0 tooling, and a static bootstrap file is the durable fallback regardless of which framework that work eventually picks.

### Consequences

- **Positive:** Warm-up becomes near-zero-friction on supported harnesses; the agent self-initialises into the discipline. New contributors and new agent platforms onboard by reading one short file. The pattern compounds with existing memory / agentic frameworks: as L0+ tooling matures, the bootstrap file becomes the fallback for environments where richer tooling is unavailable.
- **Positive:** Agent-agnostic framing means the discipline does not couple to any single AI vendor or model generation. The methodology endures across model swaps and platform churn.
- **Negative / risks:** Bootstrap file content can drift from CONTEXT_PROTOCOL if amendments to the protocol don't propagate. **Mitigation:** explicit `depends_on` from the bootstrap file; review at every milestone freeze ([CONTEXT_PROTOCOL §6.4](../../CONTEXT_PROTOCOL.md)); bootstrap files are pointers, never restatements, so drift surface is minimal by construction.
- **Follow-ups:**
  - Add a `0. Bootstrap` row to [CONTEXT_INVENTORY §1](../../CONTEXT_INVENTORY.md#1-representation-hierarchy) (this batch).
  - Amend [CONTEXT_PROTOCOL §11.2](../../CONTEXT_PROTOCOL.md) to identify the bootstrap-file pattern as the manual L0 baseline (this batch).
  - Add Amendment v0.3 entry in [`docs/method/Amendments_Log.md`](../method/Amendments_Log.md) with paper-section guidance for the next iteration of `cognitive_cartography.tex` (this batch).
  - When a second agent platform comes into regular use (e.g. an `AGENTS.md` becomes desirable), add the second instance without re-litigating the pattern.

### Cross-References

- [CONTEXT_PROTOCOL §8.1](../../CONTEXT_PROTOCOL.md) — warm-up sequence the bootstrap files operationalise.
- [CONTEXT_PROTOCOL §11.2](../../CONTEXT_PROTOCOL.md) — L0 specification, of which session-bootstrap is the manual baseline.
- [ADR-024](#adr-024--add-session-retrospective-artefact-type) — comparable artefact-type-introducing ADR.
- [ADR-025](#adr-025--amend-context_protocol-83-with-milestone-close-and-phase-boundary-rules) — comparable protocol-amending ADR.
- [ADR-026](#adr-026--adopt-agentic-execution-layer-reduce-human-action-surface) — agentic-execution stack this ADR extends at L0.
- [`docs/method/Amendments_Log.md`](../method/Amendments_Log.md) Amendment v0.3 — methodology-paper amendment record.
- [OQ-028](OPEN_QUESTIONS.md#oq-028--which-agentic-memory-framework--tooling-for-l0l1), [OQ-029](OPEN_QUESTIONS.md#oq-029--when-to-implement-l0l1) — open questions on richer-L0 tooling that bootstrap files do not displace.

---

## ADR-043 — Phase 1 strategy switch: `triple_lev_sma_filter_dsl` (A3) replaces `tkan_v4_momentum_timing` (A2)

- **status:** ACCEPTED
- **date:** 2026-05-02
- **decider:** Oleg (with Claude)
- **supersedes:** [ADR-021](#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) — CAC ETF proxy as the Phase 1 strategy designation. The CAC.PA Instrument + Yahoo-suffix substrate per ADR-041 + DD-7 stay durable.
- **amends:** [KB-5 §7 phased priority](../kb/strategy_taxonomy.md#7-nav-slice--priorities) — A3 promoted to Phase 1; A2 (`tkan_v4_momentum_timing`) demoted to deferred-no-target.
- **refined-by:** [ADR-052](#adr-052--phase-1-accepts-the-pma-bound-leveraged-leg-non-fill-oq-031-option-1) — Phase 1 accepts that the QQL3 (3×) leveraged equity leg structurally does not fill on the PMA-bound UK-retail account ([OQ-031](OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account) Option 1). The QQL3 leg is **retained but provisional**; the leveraged-equity redesign is deferred to Phase 2 ([OQ-032](OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure)).

### Context

The M2-IB.4a tag chain wire-validated the IB write side end-to-end against IB Paper for **single-instrument** flow on `CAC.PA` (REJECTED disambiguation at `M2-IB.4a-rejected`; SUBMITTED → ACCEPTED → CANCELED at `M2-IB.4a-happy` and `M2-IB.4a-happy-cacpa`). The M2-IB.5 architectural-surface run (60-bar tape replay, 35 FSM cycles, 0 rejected, 0 breaches) validated the single-instrument pipeline. M2-IB.5 was originally scoped as the strategy run for A2 (`tkan_v4_momentum_timing` 1× on CAC.PA per ADR-021).

Operator decision 2026-05-02: switch the Phase 1 strategy from A2 to **A3 — `triple_lev_sma_filter_dsl`** (the strategy in `btest/research/Triple Leveraged ETF/triple_leveraged_etf_dsl.ipynb`). Rationale: A3 is the operator's *first live-trading candidate*; validating the production path end-to-end now is more valuable than running A2 paper validation as an intermediate step that doesn't directly compound into live readiness.

A3's mechanics (per [KB-5 §2 A3](../kb/strategy_taxonomy.md#a3--multi-instrument-trend-filter-with-safe-haven-park-s-universe-daily) and the notebook):

- Universe: **TQQQ** (3× QQQ), **TMF** (3× TLT 20+y Treasury), **IEF** (7-10y Treasury safe-haven park). All US-listed ETFs on NASDAQ / NYSE.
- Two independent legs, 50 / 50: TQQQ leg holds TQQQ when QQQ > SMA-200 (5% hysteresis re-entry), parks in IEF otherwise. TMF leg holds TMF when TLT > SMA-200, parks in IEF otherwise.
- IEF eligibility = `NOT(TQQQ_eligible AND TMF_eligible)` — guarantees exactly 2 instruments selected → `EqualWeight` gives 50 / 50.
- DSL realisation: `LongShortPortfolio` (empty short_book) + `MaskSelector(signal_name="sma_eligible")` + `ExternalFactor(per_instrument=True)` reading a wide parquet with one bool column per ticker.
- Execution: `signal_delay_bars=1` (T+1 open).
- Daily rebalance (DSL form; v1 notebook does bimonthly — operational refinement deferred to a future "smart rebalance" strategy variant per the operator).
- Backtest stats from the notebook: CAGR ~24%, Sharpe ~0.88, max DD ~-37%.

### Decision

1. **Phase 1 strategy = `triple_lev_sma_filter_dsl`** (archetype A3 per KB-5 §2). Universe TQQQ + TMF + IEF.
2. **NAV slice unchanged**: 5–10% of total NAV per [ADR-020](#adr-020--phase-1-nav-slice-510-of-total-cap-10). The strategy's internal 3× leverage on TQQQ / TMF is *strategy-internal exposure*, distinct from the engine-level NAV slice; ADR-020 still applies.
3. **Daily rebalance** for the M2-IB.6 paper run (matches the DSL form). Bimonthly v1-style cadence is a future operational refinement, not a Phase 1 decision.
4. **T+1 open execution** per `signal_delay_bars=1`. Order type = MKT (matches `run_m2ib5_paper.py` default; LMT is selectable).
5. **Live cutover venue: IB only.** Per the operator's M2-IB.6 scope decision, the IG-side cross-broker testing originally considered alongside this switch is dropped from M2-IB.6 scope (IG broker code stays archived per RETRO-M2-IG; revival not planned).
6. A2 (`tkan_v4_momentum_timing`) — code stays in the repo (loader, `SingleAssetRunner` dispatch via ADR-030, paper-pipeline wiring, tests). Marked **DEFERRED-NO-TARGET** in INV-1 / KB-5; reusable when an A2-style timing strategy returns to scope.
7. ADR-021 (CAC ETF proxy as Phase 1 strategy) → SUPERSEDED-BY-ADR-043. The CAC.PA Instrument + Yahoo-suffix translation table (DD-7 §3.1, ADR-041) + the M2-IB.4a-happy-cacpa wire validation are durable substrate; only the *Phase 1 strategy designation* moves.

### Alternatives Considered

1. **Stay with A2 on CAC.PA per ADR-021.** Rejected because (a) operator's intent is A3 as first live-trading candidate, so paper-validating A2 is rework; (b) A3 forces the multi-instrument pipeline + LongShortPortfolio dispatch + US-equity SMART routing that compound into Phase 2 / live readiness; (c) the M2-IB.4a-* tags already cover the IB write-side wire validation that A2 paper run would have re-exercised.
2. **Run BOTH A2 paper-validated AND A3 sequentially.** Rejected — doubles session count for marginal additional confidence; A2 has unit-test coverage already; the operator's stated next step is live trading on A3.
3. **A3 with 1× / 2× ETF variants (QQQ / TLT / IEF or 2× ETFs).** Rejected per operator: keep the 3× leveraged ETF universe as designed; dialing back the leverage changes the strategy's regime characteristics.
4. **Bimonthly rebalance per the v1 notebook.** Rejected for M2-IB.6 — DSL realisation is daily; operator-noted intent is a future "smart rebalance" strategy variant where the cadence is dynamic. Daily is the available form for the paper run.
5. **Test on both IB Paper AND IG paper before any live cutover (the original Q1 / Q5 / Q6 dual-broker proposal).** Rejected per operator — focus on IB operationability first; cross-broker testing can revive later if IG returns to scope. M2-IB.6 is IB-only.

### Consequences

- **Positive:** Phase 1 paper validation matches the actual live-trading candidate. Multi-instrument pipeline (per ADR-044) + LongShortPortfolio btest dispatch (per ADR-045) + IB SMART for US equities (per ADR-046) all become Phase 1 substrate, compounding into Phase 2 readiness. US-equity venues (XNAS / XNYS / ARCX) get exercised — broadens venue coverage beyond CAC.PA's single-venue path.
- **Negative:** bigger lift before first paper FILLED validation; complexity bugs hit at higher stakes than they would have on the simpler A2 path. Leveraged-ETF financing parity per [KB-6 §4](../kb/cost_margin_dictionary.md) becomes load-bearing earlier (3× ETFs decay overnight; intraday parity diverges from a static-rate model). The M2-IB.5 architectural-surface validation we just got remains useful but doesn't generalise to multi-instrument.
- **Risk:** the 3× leveraged ETFs amplify downside; even at 5% NAV slice, the strategy-internal max DD of -37% (per the notebook's backtest) maps to ~-1.85% drawdown on total NAV — still small, but a meaningful test of RC-04 (daily loss thresholds) and RC-11 (drawdown scaling) when those land at M4.
- **Follow-ups:**
  - INV-1 strategies — A3 row promoted to Phase 1 (M2-IB.6 target); A2 row marked DEFERRED-NO-TARGET (existing code stays).
  - INV-10 asset_classes — `us_etf` already at "high — Phase 1, 2, 3"; no change needed but the priority becomes load-bearing now rather than later.
  - KB-5 §7 phased priority reordered: A3 → Phase 1 (M2-IB.6); A2 → deferred-no-target. Phase 2 / Phase 3 / Phase 4+ ordering otherwise preserved.
  - DD-7 §3 grows US ETF venues with the SMART routing convention (per ADR-046) — XNAS / XNYS / ARCX → SMART with primaryExchange hint.
  - Multi-instrument pipeline support (per ADR-044) — `run_ib_pipeline` extends from `instrument: Instrument` to `instruments: list[Instrument]` + `target_weights_series: pd.DataFrame`.
  - LongShortPortfolio btest dispatch (per ADR-045) — wires `compute_target_weights_for_date()` analogous to `SingleAssetRunner` for TimingPortfolio per ADR-030.
  - Refresh script extended for QQQ + TLT + TQQQ + TMF + IEF (5 tickers; produces a wide eligibility-signals parquet matching `triple_lev_sma_eligible.parquet` format).
  - TASK_REGISTRY: M2-IB.5 closes at architectural surface 2026-05-02 (CLOSED-EARLY-BY-OPERATOR per the discipline-extension noted in RETRO-M2-IG §"Recommendations for the discipline itself"); M2-IB.6 opens with sub-milestones .6.1 (multi-instrument pipeline + 5-ticker refresh + LongShortPortfolio wiring) / .6.2 (IB Paper end-to-end run during US RTH) / .6-close (RETRO-M2-IB + NEXT_PROMPT v0.6).
  - The CAC.PA SBF historical-data subscription that was an open M2-IB.5 prereq (per INV-14 §"Codes catalogued in KB-3 but not yet observed" + the operator-action item from `b21c43c`) is no longer needed — drop from operator-prereqs.
  - The `run_m2ib5_paper.py` driver stays in repo as durable substrate for the single-instrument-pipeline shape; the M2-IB.6.2 driver `run_m2ib6_ib_paper.py` is its multi-instrument analogue.

### Cross-References

- [KB-5 §2 A3](../kb/strategy_taxonomy.md#a3--multi-instrument-trend-filter-with-safe-haven-park-s-universe-daily) — strategy archetype.
- [KB-5 §7](../kb/strategy_taxonomy.md#7-nav-slice--priorities) — phased priority (amended by this ADR).
- [ADR-013](#adr-013--v1-scope-etf-and-index-strategies-only) — v1 ETF/index scope (still holds; A3 is ETF).
- [ADR-016](#adr-016--leverage-support-both-margin-financed-and-leveraged-etf-instruments) — leveraged-ETF leverage path; A3 is the canonical Phase 1 instance.
- [ADR-019](#adr-019--a3-archetype-generalises-to-other-leveraged-etf-pairs) — A3 generalisation; Phase 1 picks the canonical TQQQ / TMF / IEF instance.
- [ADR-020](#adr-020--phase-1-nav-slice-510-of-total-cap-10) — NAV slice unchanged.
- [ADR-021](#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf) — superseded.
- [ADR-030](#adr-030--per-archetype-btest-interpreter-dispatch-amends-adr-010) — per-archetype dispatch; ADR-045 lights up the LongShortPortfolio path.
- [ADR-044](#adr-044--multi-instrument-pipeline-support) — pipeline extension (companion ADR).
- [ADR-045](#adr-045--longshortportfolio-btest-dispatch-extends-adr-030) — interpreter dispatch (companion ADR).
- [ADR-046](#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032) — IB SMART for US equities (companion ADR).
- INV-1 / INV-10 / TASK_REGISTRY — substrate amendments in the same commit batch.

---

## ADR-044 — Multi-instrument pipeline support (companion to ADR-043)

- **status:** ACCEPTED
- **date:** 2026-05-02
- **decider:** Oleg (with Claude)
- **companion:** [ADR-043](#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2)

### Context

[ADR-043](#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2) picks A3 (`triple_lev_sma_filter_dsl` on TQQQ/TMF/IEF) as the Phase 1 strategy. The current pipeline drivers — `blive.runtime.paper_pipeline.run_paper_pipeline` (M1) and `blive.runtime.ib_pipeline.run_ib_pipeline` (M2-IB.5) — walk a single `instrument: Instrument` per call. The Sizer (`blive.sizing.size_orders`) already accepts multi-instrument target weights (`target_weights: dict[str, float]`); the pipeline driver is the only thing that needs widening.

### Decision

The IB pipeline (per ADR-043 the Phase 1 path) extends to multi-instrument operation:

1. **Public surface**: `run_ib_pipeline(*, instruments: list[Instrument], ...)` instead of `instrument: Instrument`. The first instrument in the list is the canonical bar timeline (most strategies will share rebalance times across instruments; if not, the pipeline reads bar timestamps from the first instrument and applies the same rebalance moments to the rest, which matches A3's daily rebalance contract).
2. **Signal contract**: replace `position_series: pd.Series` (single-instrument 0/1) with `target_weights_series: pd.DataFrame` indexed by bar `close_time_utc`, columns being the per-instrument symbol (`TQQQ`, `TMF`, `IEF`), values float weights. The SMA stub (per `blive.runtime.signals`) extends accordingly; ADR-045's LongShortPortfolio dispatch produces the same shape from btest.
3. **Per-rebalance loop**: read the row from `target_weights_series` for the current bar's close_time_utc; pass the per-symbol dict to `Sizer.size_orders(...)`; the Sizer's existing per-instrument logic produces N orders (one per instrument with non-zero target delta); each order goes through the RiskEngine and IBBroker individually (per-order FSM drain unchanged).
4. **`PaperMarketData`** already supports multi-instrument fixtures via `fixtures: Mapping[Instrument, Path]`. The driver provides one parquet per instrument.
5. **`IBRunResult` schema widens**: `equity_curve` rows gain `positions: dict[str, Decimal]` (per-instrument quantity) replacing the single `position_qty`; `fills_count`, `submitted_count`, `canceled_count`, `rejected_count` stay scalar (across all instruments).

The single-instrument `run_paper_pipeline` (M1) and the single-instrument shape of the M2-IB.5 driver stay backwards-compatible — the multi-instrument extension lives on `run_ib_pipeline` only (via either an additional optional `instruments` arg defaulting to `[instrument]` for compat, or a sibling `run_ib_multi_pipeline` — final shape decided at M2-IB.6.1 implementation time; both meet ADR-044's contract).

### Alternatives Considered

1. **Build a separate `run_ib_multi_pipeline` and leave `run_ib_pipeline` single-instrument forever.** Rejected — code duplication; Sizer / RiskEngine paths are already multi-instrument-capable; consolidation under one pipeline stays cleaner.
2. **Wait for a broker-agnostic refactor of `paper_pipeline.py` and `ib_pipeline.py` into one `run_pipeline` that handles both modes.** Rejected — out of scope for M2-IB.6; the unification is meaningful M5+ work that benefits from a fresh-session task with proper scope, not glommed onto Phase 1's path to live trading.
3. **Pass `instruments` + a callable `target_weights_fn(bar) → dict[str, float]` instead of a pre-computed DataFrame.** Rejected — DataFrame is more testable (deterministic, comparable, replayable); btest's `compute_target_weights_for_date()` returns Series rows that pivot trivially to the DataFrame shape.

### Consequences

- **Positive:** A3 (and any future multi-instrument strategy) runs through the same orchestrator. The Sizer / RiskEngine / FSM-drain paths are unchanged. New strategies plug in via the signal contract (DataFrame), not by writing a new pipeline.
- **Negative:** `IBRunResult` schema change is a minor breaking change for the existing M2-IB.5 driver `run_m2ib5_paper.py` summary printer. Mitigated by treating the single-instrument case as a degenerate multi-instrument case (1 column DataFrame, 1-element instruments list) — the M2-IB.5 driver continues to work with the new pipeline if we route it through a thin compat shim.
- **Risk:** per-instrument FSM drains run sequentially within each rebalance — if the pipeline submits 3 orders at the same bar close, and each waits up to `event_wait_seconds` (default 10s) for terminal, the rebalance can take up to 30s. For a daily-frequency strategy with infrequent regime flips this is fine; intraday strategies will need per-order parallelism (M5+ concern).
- **Follow-ups:**
  - M2-IB.6.1 ships the implementation + 3-instrument synthetic-fixture tests.
  - The M2-IB.5 driver `run_m2ib5_paper.py` may stay single-instrument or upgrade to use the multi-instrument shape with a 1-element list — decided at implementation time.
  - The Sizer's existing multi-instrument capability is the load-bearing primitive — no Sizer changes needed.

### Cross-References

- [ADR-043](#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2) — the strategy switch this enables.
- [ADR-008](#adr-008--riskengine-no-bypass-enforced-architecturally) — RiskEngine no-bypass; per-order traversal preserved.
- [ADR-045](#adr-045--longshortportfolio-btest-dispatch-extends-adr-030) — produces the target_weights_series this pipeline consumes.
- `blive.sizing.size_orders` — existing multi-instrument capability.
- `blive.runtime.ib_pipeline.run_ib_pipeline` — extended at M2-IB.6.1.

---

## ADR-045 — LongShortPortfolio btest dispatch (extends ADR-030)

- **status:** ACCEPTED
- **date:** 2026-05-02
- **decider:** Oleg (with Claude)
- **extends:** [ADR-030](#adr-030--per-archetype-btest-interpreter-dispatch-amends-adr-010)

### Context

[ADR-030](#adr-030--per-archetype-btest-interpreter-dispatch-amends-adr-010) (per-archetype btest interpreter dispatch) lit up the `TimingPortfolio → SingleAssetRunner` path for M1's A2 strategy. `LongShortPortfolio` — the archetype A1 / A1a / A3 use — has a different btest interpreter: a free function `compute_target_weights_for_date()` in `quantdsl_backtest.engine.portfolio_engine`, surfaced at M1 via the [RETRO-M1](../retros/M1_retrospective.md#surprises) "PortfolioEngine is a function, not a class" surprise. ADR-030's "three engines" prose is incomplete and is acknowledged so in [OQ-030](OPEN_QUESTIONS.md#oq-030--which-btest-interpreter-does-blive-call-for-timingportfolio-and-other-non-longshort-archetypes) (resolved by ADR-030 with the dispatch pattern, not by enumeration of all archetype paths).

[ADR-043](#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2) picks A3, which uses `LongShortPortfolio` (with empty `short_book` + `MaskSelector` + `ExternalFactor(per_instrument=True)`). The pipeline needs the LongShortPortfolio dispatch path lit up.

### Decision

Extend the per-archetype dispatch from ADR-030 to cover `LongShortPortfolio`:

1. **Detection**: `blive.runtime.ib_pipeline` (and any future broker pipeline) inspects `live_strategy.strategy.portfolio` type at entry and dispatches:
   - `TimingPortfolio` → `quantdsl_backtest.runners.single_asset.SingleAssetRunner` (existing per ADR-030)
   - `LongShortPortfolio` → `quantdsl_backtest.engine.portfolio_engine.compute_target_weights_for_date()` (this ADR)
   - any other type → `NotImplementedError` with a clear "extend dispatch" message
2. **Call shape**: per-rebalance call `compute_target_weights_for_date(strategy=..., as_of=bar.close_time_utc, factor_data=..., signal_data=..., ...)` returning a `pd.Series[symbol → float]` (target weight per instrument). The pipeline pivots into the multi-instrument `target_weights_series` DataFrame contract from [ADR-044](#adr-044--multi-instrument-pipeline-support-companion-to-adr-043).
3. **Factor + signal data**: A3 specifically needs `ExternalFactor(per_instrument=True)` reading the wide eligibility parquet (`triple_lev_sma_eligible.parquet`); the M2-IB.6.1 refresh script produces this from the SMA logic. Other LongShortPortfolio strategies may use different `Factor` types — the FactorEngine evaluates them as it does in btest; blive provides the factor inputs.
4. **No reimplementation**: blive does NOT reimplement `compute_target_weights_for_date()` — per [ADR-010](#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import) we import it directly. The dispatch is the load-bearing change; the engine itself is btest's.

### Alternatives Considered

1. **Reimplement LongShortPortfolio's logic inside blive** (analogous to writing a SingleAssetRunner-equivalent). Rejected per ADR-010 (don't fork btest); also forfeits all the existing btest tests for the engine.
2. **Wait for btest to expose a unified `Engine.run(strategy, as_of)` API.** Rejected — indeterminate timing; the dispatch pattern is already established (ADR-030) and is what btest's surface naturally supports.
3. **Use a single dispatch table mapping (Portfolio type) → (interpreter callable)** to make the path data-driven rather than `if isinstance` chains. Reasonable but premature; with two archetypes lit up, an explicit `if/elif` is more readable. Promote to a registry when a third archetype lands.
4. **Drop the LongShortPortfolio path entirely and just compute the SMA eligibility client-side** (skip btest's interpreter, build target_weights from the eligibility booleans directly). Rejected — defeats ADR-010's reuse; loses the FactorEngine / SignalEngine code path that calibrates parity with btest backtests.

### Consequences

- **Positive:** A3 runs end-to-end through btest's actual interpreter — parity with the notebook's backtest is honest. Future LongShortPortfolio strategies (A1 single-name post-M8, A1a `lagging_indecies` Phase 2) plug in for free. The per-archetype dispatch pattern from ADR-030 generalises cleanly.
- **Negative:** small additional dispatch-site complexity in the pipeline driver. Tests cover both paths.
- **Risk:** btest API surface for `compute_target_weights_for_date()` may change before Phase 2 (the M1 retro flagged this as a substrate-vs-reality drift mode). Mitigated by the CI smoke-import test (`tests/contracts/test_btest_imports.py`) that catches signature breaks; if the API changes, blive adapts in the dispatch layer, not the strategy code.
- **Follow-ups:**
  - M2-IB.6.1 ships the implementation + tests.
  - When a strategy uses something other than `TimingPortfolio` or `LongShortPortfolio` (e.g. a pairs strategy with `PairsPortfolio` if btest grows one), this ADR's dispatch table extends. Each new archetype → new entry; the pattern stays the same.
  - KB-1 §6 (btest DSL inventory) gains an explicit row for the LongShortPortfolio interpreter dispatch when KB-1 next refreshes.

### Cross-References

- [ADR-010](#adr-010--reuse-btests-factor--signal--portfolio-engines-by-import) — reuse btest by import; this ADR honours that.
- [ADR-030](#adr-030--per-archetype-btest-interpreter-dispatch-amends-adr-010) — the dispatch pattern this extends.
- [ADR-043](#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2) — strategy that needs this path lit up.
- [ADR-044](#adr-044--multi-instrument-pipeline-support-companion-to-adr-043) — pipeline shape that consumes the target_weights_series this dispatch produces.
- [OQ-030](OPEN_QUESTIONS.md#oq-030--which-btest-interpreter-does-blive-call-for-timingportfolio-and-other-non-longshort-archetypes) — original open question; ADR-030 + this extension fully address it.
- [RETRO-M1 §"Surprises"](../retros/M1_retrospective.md#surprises) — `PortfolioEngine` is a function, not a class.

---

## ADR-046 — IB resolver SMART routing for US equities (refines ADR-032)

- **status:** ACCEPTED
- **date:** 2026-05-02
- **decider:** Oleg (with Claude)
- **refines:** [ADR-032](#adr-032--instrument-resolution-policy-blive-instrument--ib-contract)

### Context

[ADR-032](#adr-032--instrument-resolution-policy-blive-instrument--ib-contract) codified the `Instrument` ↔ `Contract` / `ConID` resolution policy. The current `IBInstrumentResolver` maps `venue` (MIC) → IB `exchange` directly via the [DD-7 §3](../dd/instrument_dictionary.md#3-venue-mic--ib-exchange) table (XPAR → SBF, XNAS → NASDAQ, etc.). For US-equity venues (NASDAQ / NYSE / ARCA / BATS), direct routing trips IB Paper's "Direct Routed Orders" precaution at error 10311 (observed at `M2-IB.4a-rejected`).

The probe-local `_SmartUsResolver` workaround in `scripts/probe_ib_submit.py` routes US-venue spot equities via `exchange="SMART"` with `primaryExchange=<NASDAQ/NYSE/...>` hint — works cleanly without depending on operator-side API → Precautions bypass. This is also IB's recommended best practice for US equities (the SMART router optimises across the listing exchange + ECNs); direct routing to NASDAQ-the-exchange is rarely correct in production.

[ADR-043](#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2) picks A3 with universe TQQQ / TMF / IEF — all US ETFs. Codifying SMART routing in the production resolver moves this from "probe-local workaround" to "load-bearing for Phase 1 / live cutover".

### Decision

The production `IBInstrumentResolver` routes US-equity venues via SMART:

1. For `Instrument` records with `tradability="spot"` and `asset_class ∈ {EQUITY, ETF}` whose `venue` is in the **US-SMART set** (`XNAS`, `XNYS`, `ARCX`, `BATS`), the resolver constructs `ib_async.Contract(secType="STK", symbol=..., currency=..., exchange="SMART", primaryExchange=<IB-named-exchange-from-§3>)`.
2. Other venues (XPAR/SBF, XLON/LSE, XETR/IBIS, etc.) retain direct routing. SMART support for European cash equities is limited and venue-by-venue; revisit per venue when those return to scope.
3. **DD-7 §3** is amended to grow a `primaryExchange` column for the US rows; the existing `IB exchange` column carries `SMART` for those rows.
4. The probe-local `_SmartUsResolver` in `scripts/probe_ib_submit.py` becomes redundant once the production resolver implements this — can be removed at M2-IB.6.1 with the production code, or kept as historical-substrate documentation.
5. Other `tradability` values (`cfd`, `spread_bet`) don't apply to IB retail per [ADR-040](#adr-040--phase-1-deployment-target-windows-host-with-native-ib-gateway) (and the resolver already raises `InstrumentNotResolvable` for them); this ADR's scope is `tradability="spot"` only.

### Alternatives Considered

1. **Keep direct routing + rely on the API → Precautions bypass.** Rejected: works for paper but the bypass is operator-side config that can drift across IB Gateway restarts; SMART routing is IB's recommended best practice anyway. The bypass mechanism stays as a safety net for venues that don't have SMART (e.g. SBF for European cash equities) — for US, SMART is the right default.
2. **Introduce an `Instrument.routing_hint` field** (`"smart"` / `"direct"`) and let the strategy author specify per-Instrument. Rejected: bloats the broker-neutral type with broker-specific knowledge per ADR-032 §"Alternatives" item 1 (the same reason `ib_symbol` was rejected); routing is the *adapter's* responsibility.
3. **Always SMART for everything**, with primaryExchange derived from the §3 table. Rejected: SMART support varies by venue; non-US venues frequently require direct routing. The US-only scope is empirically correct.
4. **Codify SMART routing in a separate `IBSmartResolver` class** (subclass of `IBInstrumentResolver` mirroring the probe-local `_SmartUsResolver`). Rejected: the production resolver should always do the right thing for production; subclass just for the SMART path is needless ceremony.

### Consequences

- **Positive:** Phase 1 A3 (TQQQ / TMF / IEF on US venues) routes via SMART → no precaution dance, no operator-side bypass dependency for US-equity orders, follows IB best practice. Future US-equity strategies (any A1 / A2 / A3 instance on NASDAQ / NYSE) inherit the convention.
- **Negative:** `DD-7 §3` table grows a column. The probe-local `_SmartUsResolver` retains as fallback documentation.
- **Risk:** SMART routing is opaque about which actual exchange the order routes to (the IB router decides per its internal scoring). For audit / parity purposes the realised execution venue is in the `Fill.execution.exchange` field at fill time — visible but not pre-determined. The discipline accepts this trade-off (matches IB recommended practice).
- **Follow-ups:**
  - M2-IB.6.1 ships the resolver code change + tests (existing `test_instrument_resolver.py` adds rows for XNAS/XNYS/ARCX/BATS spot equities).
  - DD-7 §3 amendment in this commit.
  - `scripts/probe_ib_submit.py` updates: remove the `_SmartUsResolver` workaround once the production resolver is updated, or keep it as a documentation comment of "this is what the production resolver does for US equities". Decided at M2-IB.6.1 implementation.
  - The Saturday-2026-05-02 `M2-IB.4a-happy-cacpa` validation (which used the operator's API → Precautions bypass for direct-routed CAC.PA) stays valid — that path is for non-US venues where SMART isn't an option. The bypass is still useful for those.

### Cross-References

- [ADR-032](#adr-032--instrument-resolution-policy-blive-instrument--ib-contract) — resolution policy this refines.
- [ADR-043](#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2) — strategy that needs this convention.
- [ADR-040](#adr-040--phase-1-deployment-target-windows-host-with-native-ib-gateway) — Phase 1 IB Gateway target; SMART routing is unaffected by this.
- [DD-7 §3](../dd/instrument_dictionary.md#3-venue-mic--ib-exchange) — table amended in same commit.
- `scripts/probe_ib_submit.py` `_SmartUsResolver` — prototype pattern.
- [INV-14 §"Open Questions"](../inv/ib_error_codes.md#open-questions) — flagged the SMART convention as a planning concern; this ADR settles it.
- `M2-IB.4a-rejected` wire finding (commit `7d64c47`) — original 10311 observation.

---

## ADR-047 — PRIIPs-compliant universe for Phase 1 A3 strategy (refines ADR-043)

- **status:** ACCEPTED
- **date:** 2026-05-03
- **decider:** Oleg (with Claude)
- **refines:** [ADR-043](#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2)
- **refined-by:** [ADR-052](#adr-052--phase-1-accepts-the-pma-bound-leveraged-leg-non-fill-oq-031-option-1) — the PRIIPs-substituted QQL3 (3×) leg structurally does not fill on the PMA-bound UK-retail account ([OQ-031](OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account) Option 1); **retained but provisional** for Phase 1, leveraged-equity redesign deferred to Phase 2 ([OQ-032](OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure)).

### Context

[ADR-043](#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2) picked the `triple_lev_sma_filter_dsl` strategy with universe TQQQ / TMF / IEF (US-domiciled ETFs). The M2-IB.6.1 architectural-surface wire run on 2026-05-03 against the operator's IB UK paper account submitted 104 orders across the 3 tradables — all rejected with **IB error 201**, reason text:

> *"No Trading Permission, Customer Ineligible; Ineligibility reasons: This product does not have a KID in English or in a language approved for your country. Retail clients can trade packaged retail products only if an appropriate KID is available."*

This is **PRIIPs / KID regulation** — the EU/UK rule (still in force in UK post-Brexit) that requires a Key Information Document (KID) in the consumer's language for any "packaged retail product" sold to retail clients. US-domiciled ETFs typically do not file KIDs in the UK; UK retail accounts therefore cannot trade them. The operator's IB UK paper account mirrors UK retail-client restrictions.

The wire run validated the multi-instrument pipeline + SMART routing + REJECTED disambiguation cleanly (104 round trips, 0 breaches, FSM correct throughout) — the blocker is purely regulatory, not a blive-side bug.

### Decision

The Phase 1 A3 universe substitutes UK-listed PRIIPs-compliant analogues:

| Original (US) | Phase 1 substitute (UK) | Notes |
|---|---|---|
| **TQQQ** (Direxion 3× QQQ) | **QQL3** (LSE — 3× Long Nasdaq 100 ETP, PRIIPs-compliant) | 3× leverage preserved. ETP rather than UCITS; KID filed for UK retail. Operator-confirmed tradable on IB UK paper 2026-05-03. |
| **TMF** (Direxion 3× 20+y Treasury) | **IBTL** (LSE — iShares $ Treasury Bond 20+yr UCITS ETF, PRIIPs-compliant) | **1× leverage** — no UK-listed 3× US-Treasury ETP exists per operator's IB lookup. **Strategy regime change**: the TMF leg's leverage drops from 3× to 1×; backtest CAGR / Sharpe / max-DD from `triple_leveraged_etf_dsl.ipynb` no longer carry forward exactly. The strategy's risk balance shifts from 50/50 to roughly 75/25 (risk-on/risk-off), since the equity leg keeps 3× while the bond leg loses 2/3 of its leverage. Operator-acknowledged trade-off in exchange for strategy executability on the UK retail account. |
| **IEF** (iShares 7-10y Treasury) | **IBTM** (LSE — iShares $ Treasury Bond 7-10yr UCITS ETF, PRIIPs-compliant) | Direct UCITS analogue. Operator-confirmed tradable. |

**Trend signals unchanged**: the strategy still uses **QQQ** (Nasdaq-100 ETF) and **TLT** (20+y Treasury ETF) closes from EODHD as the SMA-200 trend-filter inputs. These tickers are *never traded* — they are signal-only — so PRIIPs / KID does not apply.

**Venue**: all three tradables are on **LSE (XLON)**, direct-routed per [DD-7 §3](../dd/instrument_dictionary.md#3-venue-mic--ib-exchange) (XLON is not in the US-SMART set per [ADR-046](#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032)). The "Bypass Order Precautions for API Orders" toggle the operator already has ticked (per `M2-IB.4a-happy-cacpa`) covers any LSE direct-routing precaution.

**Currency**: USD (all three are USD-priced share classes on LSE; the operator's account base GBP triggers IB's automatic FX conversion at fill time).

### Alternatives Considered

1. **Margin-finance the bond leg per [ADR-016](#adr-016--leverage-support-both-margin-financed-and-leveraged-etf-instruments) to synthesise 3× exposure on the 1× IBTL.** Rejected — requires RC-01 (max gross leverage) / RC-04 (daily-loss thresholds) RiskEngine widening which is M4+ scope. The 1× substitution accepts the regime change in exchange for Phase-1-feasibility.
2. **Apply for IB Professional Client status to bypass PRIIPs.** Rejected per operator — not applying at this time.
3. **Substitute a different non-Treasury bond leg with an available 3× UK ETP** (if any existed). Rejected — would change the strategy's safe-haven semantics materially, and no clean substitute exists on UK retail venues per the operator's IB lookup.
4. **Drop the bond leg entirely, run a single-instrument leveraged-equity strategy (QQL3 only).** Rejected — collapses the archetype to A2 (single-instrument timing), defeating the multi-instrument pipeline / LongShortPortfolio dispatch / IEF safe-haven park work in M2-IB.6.1.
5. **Pivot back to A2 / CAC.PA per ADR-021 (which is PRIIPs-compliant).** Rejected — A3 was deliberately picked per ADR-043 as the first live-trading candidate; reverting forfeits the multi-instrument substrate work.

### Consequences

- **Positive:** the strategy is executable on the operator's IB UK retail paper account; M2-IB.6.2 can run with real fills during US / LSE RTH.
- **Positive:** UK-listed leveraged ETPs / UCITS ETFs are explicitly designed for retail consumption; KID, ESMA fact-sheet, and tracking-error documentation are public — better operational documentation than US analogues for retail use.
- **Negative — strategy regime change:** the bond leg's 3× → 1× leverage means the article's backtest numbers (CAGR ~24%, Sharpe ~0.88, max DD ~-37% per `triple_leveraged_etf_dsl.ipynb`) do not carry forward. Re-derive the parity envelope at M7 against this universe; the M2-IB.6 paper run is for FSM / pipeline validation, not strategy-quality validation.
- **Negative — instrument decay characteristics differ:** UK-listed 3× ETPs use synthetic replication (vs Direxion's swap-based US 3× products) which has different decay profile and counterparty exposure. Worth noting as a parity-residual driver.
- **Risk — IBTL drawdown profile under sustained Treasury sell-off:** without 3× leverage on the bond leg, the strategy spends more time effectively long-equity-only during regime-on periods, since IBTL contributes ~1/3 the volatility a 3× analogue would. RC-04 daily-loss thresholds (M4 work) become more important when the equity leg becomes structurally dominant.
- **Follow-ups:**
  - INV-1 strategies row updated: `triple_lev_sma_filter_dsl` Phase 1 universe column reflects the UK substitution + the 1× bond-leg note.
  - INV-14 grows: error 201 with PRIIPs-KID reason (catalogued explicitly to distinguish from the precaution-cascade variant from M2-IB.4a-rejected).
  - KB-9 (UK regulatory) gains a §"PRIIPs / KID restrictions" section documenting the rule, the IB error path, and the universe-substitution approach as the pragmatic mitigation.
  - DD-7 §3 XLON row "Used by" annotation updated to acknowledge Phase 1 UCITS / ETP use (was post-M8 only via ADR-018 UK cash equities).
  - `scripts/refresh_eodhd_signals.py` updates the tradable ticker list to `QQL3.LSE` / `IBTL.LSE` / `IBTM.LSE` (EODHD format with `.LSE` suffix); trend signals remain US `QQQ` / `TLT`. Per-ticker parquet filenames use the IB symbol (`QQL3_1d.parquet` etc.) so the driver's lookup pattern stays unchanged. The eligibility parquet's column names rename from leg-names (`TQQQ` / `TMF` / `IEF`) to actual tradables (`QQL3` / `IBTL` / `IBTM`) on save so the driver matches by `Instrument.symbol`.
  - `scripts/run_m2ib6_ib_paper.py` updates the `_TQQQ` / `_TMF` / `_IEF` Instrument records to `_QQL3` / `_IBTL` / `_IBTM` with `venue="XLON"`, `currency="USD"`.
  - `triple_lev_sma_eligibility` runtime function unchanged — its column names are *leg identifiers* (TQQQ / TMF / IEF) which abstract over the strategy's leg semantics. The refresh script does the leg-to-tradable rename when persisting.

### Cross-References

- [ADR-013](#adr-013--v1-scope-etf-and-index-strategies-only) — v1 ETF/index scope (still holds; the new universe is ETFs / ETPs).
- [ADR-016](#adr-016--leverage-support-both-margin-financed-and-leveraged-etf-instruments) — leverage paths; A3 originally targeted the leveraged-ETF path on both legs; ADR-047's IBTL substitution mixes paths (leveraged ETP on equity leg, 1× ETF on bond leg).
- [ADR-019](#adr-019--a3-archetype-generalises-to-other-leveraged-etf-pairs) — A3 generalises; this ADR is a concrete instance of that generalisation.
- [ADR-020](#adr-020--phase-1-nav-slice-510-of-total-cap-10) — NAV slice unchanged.
- [ADR-043](#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2) — Phase 1 strategy switch (refined here).
- [ADR-046](#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032) — SMART discriminator scoped to US venues; XLON stays direct-routed (correct for these LSE ETPs).
- [INV-14](../inv/ib_error_codes.md) — error 201 with PRIIPs-KID reason catalogued in same commit batch.
- [KB-9](../kb/uk_regulatory.md) — PRIIPs / KID restrictions section added.
- [DD-7 §3](../dd/instrument_dictionary.md#3-venue-mic--ib-exchange) — XLON row annotation updated.
- M2-IB.6.1 wire-run finding (2026-05-03; output saved at `~/AppData/Local/Temp/claude/.../tasks/brktw77np.output`) — empirical observation that motivated this ADR.

---

## ADR-048 — LSE-ETF SMART routing discriminator (refines ADR-046)

- **status:** ACCEPTED (PROPOSED 2026-05-03 → ACCEPTED 2026-05-06 at M2-IB.6 close after the Wed LSE-RTH wire run produced the first IB-paper FILL on the substituted universe)
- **date:** 2026-05-03
- **decider:** Oleg (with Claude)
- **refines:** [ADR-046](#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032)

### Context

[ADR-046](#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032) codified SMART routing for US-equity venues (XNAS / XNYS / ARCX / BATS) and explicitly scoped non-US venues to direct routing per the [DD-7 §3](../dd/instrument_dictionary.md#3-venue-mic--ib-exchange) `_MIC_TO_IB_EXCHANGE` table. The XLON row was `XLON → "LSE"` (direct).

[ADR-047](#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043) substituted the Phase 1 universe to UK-listed UCITS / ETPs (`QQL3` / `IBTL` / `IBTM` on LSE). The 2026-05-03 M2-IB.6.2 wire run with those instruments and the existing `XLON → "LSE"` direct mapping returned **IB error 200 ("No security definition has been found")** on every order — the bare LSE main book does not expose UCITS ETPs.

Direct probe via `reqContractDetails` against IB Paper found the actual venue:

```
Stock(symbol='QQL3', exchange='LSE',     currency='USD')  -> 0 results (error 200)
Stock(symbol='QQL3', exchange='LSEETF',  currency='USD')  -> conId 566361457 ("3X US TECH 100")
Contract(symbol='QQL3', exchange='SMART', primaryExchange='LSEETF', currency='USD')
                                                          -> conId 566361457 (same)

Stock(symbol='IBTL', exchange='LSE',     currency='USD')  -> 0 results (error 200)
Stock(symbol='IBTL', exchange='LSE',     currency='GBP')  -> 0 results (error 200)
Stock(symbol='IBTL', exchange='LSEETF',  currency='USD')  -> 0 results (no USD class)
Contract(symbol='IBTL', exchange='SMART', primaryExchange='LSEETF', currency='GBP')
                                                          -> conId 181150859 ("ISHARES USD TRES 20+yr"
                                                              GBP-hedged accumulating share class)

Contract(symbol='IBTM', exchange='SMART', primaryExchange='LSEETF', currency='GBP')
                                                          -> conId 68489974  ("ISHARES USD TREASURY 7-10Y"
                                                              GBP-hedged accumulating share class)
```

Two findings:

1. **LSE main book and LSE ETF book are distinct IB venues.** UCITS / ETP listings live on `LSEETF`; main-book equities live on `LSE`. The existing `XLON → "LSE"` mapping is correct for cash equities but wrong for ETFs — they need `LSEETF` (or SMART with `primaryExchange="LSEETF"`).
2. **GBP-hedged share-class divergence (related but separate from this ADR's scope):** the bare `IBTL` / `IBTM` symbols on LSEETF resolve to GBP-hedged accumulating share classes, not the USD distributing classes that ADR-047 implicitly assumed. QQL3 trades USD-denominated. Phase 1 P&L is therefore mixed-currency on the IB side (USD on QQL3, GBP on IBTL/IBTM). The hedge is designed to track USD-Treasury returns in GBP, so the strategy's directional signal is preserved; the M7 parity-envelope re-derivation absorbs the absolute-return divergence (already noted in ADR-047). This ADR scopes only the routing question; the share-class question is documented in `scripts/run_m2ib6_ib_paper.py` and may motivate a follow-up ADR if a pivot to USD share classes (`IDTL` / `IDTM`) is later preferred.

The pattern of "the LSE ETF book needs SMART with primaryExchange=LSEETF" mirrors ADR-046's US-equity SMART pattern exactly — same shape, different venue.

### Decision

The production `IBInstrumentResolver` adds an LSE-ETF SMART discriminator alongside the existing US-SMART one:

1. For `Instrument` records with `tradability="spot"` AND `venue="XLON"` AND `asset_class=ETF`, the resolver constructs `ib_async.Contract(secType="STK", symbol=..., currency=..., exchange="SMART", primaryExchange="LSEETF")`.
2. For `Instrument` records with `tradability="spot"` AND `venue="XLON"` AND `asset_class=EQUITY` (single-name UK shares), the resolver retains direct routing per the existing `_MIC_TO_IB_EXCHANGE["XLON"] == "LSE"` mapping. Main-book equities and the ETF book are distinct venues; the discriminator is `asset_class`.
3. Other venues (XPAR/SBF, XETR/IBIS, etc.) are unaffected — non-XLON, non-US-SMART venues retain direct routing per ADR-046's scoping.
4. The new constant is named `_LSE_ETF_SMART_PRIMARY = "LSEETF"` (singleton string rather than a venue-set frozenset, since this is a one-venue rule rather than a pattern over a multi-venue set; if other European ETF books surface — e.g. XETR Xetra ETF — the constant generalises to a `_EU_ETF_PRIMARY_BY_VENUE` map).
5. **DD-7 §3** is amended to reflect that XLON is split into two rows: `XLON + EQUITY → LSE` (direct), `XLON + ETF → SMART/primaryExchange=LSEETF`. Same shape as the ADR-046 US-equity rows.

### Alternatives Considered

1. **Introduce a separate `XLON_ETF` MIC pseudocode** (so `Instrument.venue="XLON_ETF"` triggers the LSEETF mapping). Rejected — `XLON` is the genuine MIC for the London Stock Exchange; inventing a non-MIC pseudocode pollutes the broker-neutral type with broker-specific routing knowledge per ADR-032 §"Alternatives" item 1 (the same reasoning that rejected `Instrument.routing_hint`). The discriminator stays in the resolver where broker-specific knowledge belongs.
2. **Keep direct `LSEETF` routing** (set `Contract.exchange="LSEETF"` with empty `primaryExchange`). Rejected — works for the contract resolution, but trips IB Paper's "Direct Routed Orders" precaution at error 10311 (same precaution that motivated ADR-046's SMART move for US equities). The operator's M2-IB.4a Precautions bypass currently masks this, but bypass is operator-side state that drifts across IB Gateway restarts. SMART routing is IB best practice and avoids the bypass dependency for LSE ETFs the same way ADR-046 avoids it for US equities.
3. **Always SMART for everything XLON** (drop the `asset_class` discriminator). Rejected — main-book LSE equities have their own SMART semantics for UK pre/post-trade transparency rules (LSE main book vs Cboe vs Aquis), and the resolver should preserve existing direct-routed equity tests until those venues need SMART. Conservative scoping: ETF-only for now; widen if equity SMART becomes desirable.
4. **Discriminate on currency** (e.g. "if USD on XLON, route to LSEETF"). Rejected — currency cleanly correlates with main-book vs ETF book in the Phase 1 universe (GBP main-book, USD/GBP ETFs), but in the general case GBP-denominated UCITS exist (IBTL/IBTM ARE GBP-hedged on LSEETF) — currency is not a reliable discriminator. `asset_class` is correct.

### Consequences

- **Positive:** Phase 1 A3 (QQL3 / IBTL / IBTM on LSE) routes via SMART → contracts resolve cleanly (10/10 reach PreSubmitted in the M2-IB.6.2 wire smoke), no precaution dance, no operator-side bypass dependency for LSE-ETF orders. Future LSE-ETF strategies (any A1 / A2 / A3 instance trading UK-listed UCITS) inherit the convention.
- **Positive:** Routing convention now reads consistently: US-equity SMART (ADR-046) and LSE-ETF SMART (this ADR) follow the same `(venue, asset_class) → exchange/primary` shape. Adding future European ETF venues (XETR, XAMS) is a one-line addition to the discriminator.
- **Negative:** DD-7 §3 grows complexity — XLON is no longer a single row; it's split by `asset_class`. The table grows roughly 2× columns to express the (venue, asset_class) → (exchange, primaryExchange) mapping fully. Acceptable cost; the discriminator is real.
- **Risk:** SMART routing is opaque about which actual ECN the order routes to (same risk as ADR-046). The realised execution venue is in `Fill.execution.exchange` at fill time. Discipline accepts this trade-off.
- **Follow-ups:**
  - **Validate at LSE RTH on Tue 2026-05-05 07:00–15:30 UTC** — the M2-IB.6.2 smoke run reached PreSubmitted but cancelled at the engine's 10s timeout because LSE was closed (Sun 2026-05-03; Mon 2026-05-04 is UK May Day Bank Holiday). Real fills only land during RTH.
  - DD-7 §3 amended to split XLON into two rows by `asset_class`. Lands in same commit as this ADR's flip to ACCEPTED.
  - Existing `tests/unit/adapters/ib/test_instrument_resolver.py::test_to_contract_strips_dot_l_suffix_on_xlon` (XLON + EQUITY) stays — it asserts `exchange == "LSE"` for the equity case. Add companion tests: `test_to_contract_xlon_etf_routes_via_smart_lseetf` (XLON + ETF → exchange="SMART", primaryExchange="LSEETF"), `test_to_contract_xlon_etf_currency_passthrough` (currency="USD" and currency="GBP" both pass through).
  - The GBP-hedged share-class question (IBTL/IBTM on LSEETF resolve to GBP-hedged accumulating classes only) is **out of scope of this ADR** — documented inline in `scripts/run_m2ib6_ib_paper.py`. If Path B (USD distributing share classes `IDTL` / `IDTM`) is later picked over the GBP-hedged versions, that's a Phase 1 universe revision, not a routing-discriminator change; ADR-047 amends, this ADR stays load-bearing.
  - INV-14 grows: error 200 row gains an annotation that LSE ETF requests against the bare `"LSE"` exchange surface as code 200 (in addition to the M2-IB.3a `CAC.PA` Yahoo-suffix variant) — empirical regression marker.

### Cross-References

- [ADR-046](#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032) — SMART routing pattern this extends; the discriminator shape (venue/asset_class → exchange/primaryExchange) is identical.
- [ADR-047](#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043) — Phase 1 universe that exposes this finding; the GBP-hedged share-class question is documented there + in driver script comments.
- [ADR-032](#adr-032--instrument-resolution-policy-blive-instrument--ib-contract) — overarching resolution policy; this is a compatibility refinement.
- [DD-7 §3](../dd/instrument_dictionary.md#3-venue-mic--ib-exchange) — table amended in same commit when this flips to ACCEPTED.
- [INV-14](../inv/ib_error_codes.md) — error 200 catalogue; gains annotation for the LSE-ETF-against-bare-LSE variant.
- M2-IB.6.2 wire-probe finding (2026-05-03) — empirical observation that motivated this ADR; `reqContractDetails` probe output captured in commit `c34267d` body.

---

## ADR-049 — `OrderType.ADAPTIVE_MKT` for IBALGO Adaptive routing + empirical PMA-cap finding

- **status:** ACCEPTED (PROPOSED → ACCEPTED same-day 2026-05-06 at M2-IB.6 close per established same-day-ACCEPTED pattern; the empirical investigation matrix already provided the validation that an out-of-session ACCEPTED flip would normally need)
- **date:** 2026-05-06
- **decider:** Oleg (with Claude)
- **refines:** [ADR-027](#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero) (order-construction policy), companion to [ADR-046](#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032) / [ADR-048](#adr-048--lse-etf-smart-routing-discriminator-refines-adr-046) (IB execution-routing trail)

### Context

The 2026-05-06 LSE-RTH validation runs of `scripts/run_m2ib6_ib_paper.py` against the ADR-047 PRIIPs-compliant universe surfaced **IB warning 2161** — a regulatory **disruptive-orders price cap** (Price Management Algo / PMA) that IB applies to volatile / leveraged products on certain venues for retail-account broker-of-record protection. Observed on **QQL3** (3× Nasdaq ETP on LSEETF, median 3.91% / max 11.74% daily range over the last 60 bars) but not on IBTM (1× UCITS Treasury ETF, median 0.52% range).

The cap binds the effective limit price to IB's live bid/ask reference (`mktCapPrice` ≈ best bid for BUY orders), regardless of the order's nominal limit. In a rising market, BUY orders capped at the bid don't fill — the order sits in `Submitted` state at a sub-cap LMT until the engine cancels on timeout.

IB's 2161 warning text recommends *"submit an algorithmic Market Order (IBALGO)"* as the workaround, suggesting that algorithmic routing bypasses the cap. To validate this hypothesis (and provide useful infrastructure for non-cap-bound venues / future strategies regardless), this ADR adds `OrderType.ADAPTIVE_MKT` — a new variant of the existing `OrderType` enum that maps to `ib_async.MarketOrder` with `algoStrategy="Adaptive"` and `algoParams=[("adaptivePriority","Normal")]` set on the wire-going order.

The variant landed and was wire-validated at M2-IB.6.2c on 2026-05-06: ib_async correctly carries the algo metadata; the FSM trace differs (now PendingSubmit → PreSubmitted → Submitted → ValidationError → PendingCancel → Cancelled). **However, the 2161 cap still binds** — `mktCapPrice=39.4` was set on the Adaptive order identically to the raw-MKT case, and 0/5 QQL3 placeOrders filled in the run 3 smoke. A follow-up single-shot LMT probe (`scripts/probe_qql3_lmt_cap.py`, LMT @ $50 well above IB's ~$39 reference) confirmed the cap binds on **LMT** too — IB literally cap-rounded the $50 LMT to $39.4 per the warning text.

### Decision

Two parts:

1. **`OrderType.ADAPTIVE_MKT` is a permanent addition to the `OrderType` StrEnum** in `blive.domain.types`. The `IBBroker._blive_to_ib_order` helper builds `ib_async.MarketOrder(...)` and sets `algoStrategy="Adaptive"`, `algoParams=[ib_async.TagValue("adaptivePriority","Normal")]`. Strategies opt in per-instrument by setting the order type at sizer / pipeline level — not a global default. The pipeline (`run_ib_multi_pipeline`) accepts an `order_type_by_symbol: Mapping[str, OrderType] | None` override to wire per-leg routing. Other adapters (paper, mock, and any future broker without an equivalent algo) raise `NotImplementedError` on submit per the registry contract.

2. **PMA-cap (warning 2161) is empirically a structural constraint of UK retail accounts on LSEETF leveraged products.** No operator-side toolkit available in code bypasses it: MKT, ADAPTIVE_MKT, and LMT are all subject to the cap; the `priceManagementOff` order flag is institutional-only. Bypass requires either MiFID II Professional Client classification (declined per ADR-047 alt #2) or substituting non-leveraged products. Captured in OQ-031 for pre-Phase-1-cutover resolution. INV-14 v0.7 documents the catalogued surface + the empirical-validation matrix across the four runs.

### Alternatives Considered

1. **Hardcode IBALGO Adaptive for all `OrderType.MKT` orders in `IBBroker._blive_to_ib_order`** (no new enum). Rejected — Adaptive is genuinely a different execution semantic from raw MKT (smart agency routing vs immediate-or-cancel-against-NBBO; per-priority cost and latency profiles vary), and forcing it implicitly hides that from strategy authors. The enum makes the choice explicit.
2. **Add an `algo_strategy: str | None` field on `Order`** instead of an enum variant. Rejected — `OrderType` already encodes the broker-side routing intent (MKT vs LMT vs STP), and Adaptive is conceptually a routing intent. Adding a parallel `algo_strategy` field bloats the type with broker-specific knowledge per ADR-027 / ADR-032 §"Alternatives Considered" (the same reasoning that rejected `Instrument.routing_hint`). Future algo variants (TWAP, VWAP, DARKICE) would similarly land as `OrderType.{TWAP,VWAP,DARKICE}` — keeping the algo distinction in the enum keeps the type small per algo and forces explicit opt-in.
3. **Defer the enum addition until a non-cap-bound use case demonstrates value.** Rejected — the wire-validation is already done (51st broker test passes); rolling the work back would be churn for no gain; and Adaptive is empirically useful infrastructure for fill-quality on non-cap-bound venues (US equities, IBTM/IBTL where the cap doesn't trigger) even if it doesn't solve the QQL3 PMA case.
4. **Pursue Professional Client classification to enable `priceManagementOff`.** Out of scope per ADR-047 alt #2 — requires meeting MiFID II "elective professional" criteria (wealth, experience, transaction frequency thresholds); operator declined at M2-IB.6.1.
5. **Substitute non-leveraged products on the affected leg of the strategy** (i.e. drop QQL3, restructure A3 around 1× equity exposure). Out of scope at this milestone — the 3× → 1× substitution on the bond leg per ADR-047 already shifts the strategy regime materially; further restructuring on the equity leg is a strategy-design decision belonging to its own ADR. Captured in OQ-031 as one of the candidate resolutions.

### Consequences

- **Positive:** `OrderType.ADAPTIVE_MKT` is a clean addition to the order-construction surface that future strategies can opt into. The implementation surface (broker branch + pipeline wiring + driver per-symbol override) is small and parallel to existing patterns; the FSM contract is unchanged.
- **Positive:** The 2161 PMA-cap is now empirically catalogued (INV-14 v0.7) with the full validation matrix across four wire runs. Future investigations of similar regulatory price-cap warnings (other codes in the 2xxx range; other venues) inherit the diagnostic methodology — single-shot LMT probe at known-above-reference price, inspect `trade.orderStatus.mktCapPrice`.
- **Negative:** Phase 1 deployment of A3 has a real-world fill-quality constraint on the QQL3 leg. The strategy's effective execution profile is regime-dependent (fills on flat/down moves, blocked on up moves). Backtest fill assumptions (immediate execution at close) do not carry forward; M7 parity envelope must absorb this divergence.
- **Risk — strategy-quality on QQL3 is structurally regime-biased:** in extended uptrends the strategy spends time long the equity leg without acquiring full position, then is forced to acquire on regime-flips into safe-haven (when ask drops to bid). This is opposite to the intended trend-following profile. RC-04 daily-loss thresholds (M4 work) become more important; the operator may decide to prefer Path B (IDTL/IDTM USD distributing share-class substitution, possibly with a non-leveraged equity leg) to avoid the cap entirely.
- **Risk — IB's 2161 warning text is empirically misleading.** The recommendation *"submit an algorithmic Market Order (IBALGO)"* does not bypass the cap on UK retail accounts. Documenting this in INV-14 v0.7 protects future investigations from re-running the same hypothesis.
- **Follow-ups:**
  - OQ-031 ("Phase 1 deployment under PMA-bound retail account — accept regime-dependent fills, pursue Pro Client, or substitute the leveraged equity leg?") — target resolution: pre-Phase-1-go-live.
  - M2-IB.6 retro should capture this as a **milestone-defining surprise** alongside the PRIIPs / KID block (M2-IB.6.1) and the LSEETF venue-split (M2-IB.6.2).
  - Address the EODHD-vs-IB QQL3 price 10× discrepancy at M7 parity work — either subscribe to IB live market data for sizing reference, or document the EODHD unit-of-quote convention so the strategy can convert.
  - Status PROPOSED until M2-IB.6 retro decision; flips to ACCEPTED in the same close-out commit batch as ADR-048.

### Cross-References

- [ADR-027](#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero) — order-construction policy this extends.
- [ADR-046](#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032) — SMART routing for US equities; the IB-execution-routing trail this ADR continues.
- [ADR-047](#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043) — Phase 1 universe substitution; QQL3 is the leveraged leg that surfaces the 2161 cap.
- [ADR-048 PROPOSED](#adr-048--lse-etf-smart-routing-discriminator-refines-adr-046) — LSE-ETF SMART routing discriminator (companion; both flip ACCEPTED at M2-IB.6 close).
- [INV-14 v0.7](../inv/ib_error_codes.md) — error 201 / 2161 catalogue with empirical validation matrix.
- [OQ-031](OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account) — Phase 1 deployment trade-off (accept / Pro Client / substitute).
- M2-IB.6.2b/c wire-finding (2026-05-06) — four-run investigation captured in INV-14 v0.7 changelog.
- `scripts/probe_qql3_lmt_cap.py` — single-shot LMT-bound diagnostic.

---

## ADR-050 — EODHD-vs-IB unit-of-quote conversion at sizing time (Hybrid: B-now / A-later free-MD-only)

- **status:** ACCEPTED (drafted 2026-05-06 at M3.1 entry PROPOSED; flipped ACCEPTED 2026-06-05 on the clean LSE-RTH wire run — QQL3 sized 65 sh @ ~$39 IB-USD-equivalent and placed with **no IB error 110**, jointly with ADR-051 per Decision #5 / the M2-IB pattern)
- **date:** 2026-05-06
- **decider:** Oleg (with Claude)
- **refines:** [ADR-014](#adr-014--data-sources-via-clean-api-abstraction) (data-source abstraction), [ADR-017](#adr-017--live-data-hybrid-eodhd--ib-streaming-per-instrument-routing) (hybrid EODHD+IB routing per-instrument), [ADR-027](#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero) (Sizer policy)
- **companion:** [INV-4 v0.2](../inv/risk_checks.md) (RC-10 promoted to implemented), [KB-15 stub-DRAFT v0.1](../kb/parity_methodology.md) (unit-of-quote / reverse-split section)

### Context

M2-IB.6.2c surfaced a side-finding (per [RETRO-M2-IB §"Surprises" #7](../retros/M2-IB_retrospective.md), [INV-14 v0.7](../inv/ib_error_codes.md) changelog): **EODHD reports QQL3 close ~$383 while IB live reference is ~$39 — a ~10× discrepancy.** Strategy sizing using EODHD's price under-sizes positions ~10× in actual IB-dollar terms; LMTs computed from EODHD close × multiplier produce IB error 110 ("price not in allowed range") *before* warning 2161 (PMA cap) fires. This contaminates the M3.2 empirical paper-mode window — under-sized positions don't generate the cap-binding behaviour the [OQ-031](OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account) decision rests on. Hence the M3.1 narrow fix lands first (per [TASK_REGISTRY M3.1](../../TASK_REGISTRY.md)).

The 2026-05-06 EODHD-side investigation (`scripts/probe_qql3_unit_of_quote.py`) gathered a four-hypothesis refutation matrix:

| # | Hypothesis | Status |
|---|---|---|
| H1 | EODHD `close` is unadjusted; `adjusted_close` carries the split factor | **REFUTED.** EODHD's `adjusted_close` equals `close` (ratio 1.0) across the entire 30-day window — EODHD considers its data already adjusted, but the latest close ($412.94 on 2026-05-06) is still ~10.6× IB's reference. The `/api/splits/QQQ3.LSE` endpoint returns only one historical event (2020-11-09); nothing recent. |
| H2 | EODHD reports LSE main-book GBp pence, IB reports USD on LSEETF | **REFUTED.** EODHD's `/api/fundamentals.General.CurrencyCode = "USD"` for `QQQ3.LSE`. Both quote in USD. |
| H3+H4 | Different share class / vendor-symbol divergence | **INCONCLUSIVE without operator-side IB ISIN cross-check.** EODHD fundamentals returned no ISIN for `QQQ3.LSE` (the bare ETP entry); IB conId 566361457 is operator-confirmed at the M2-IB.6.1 wire probe. M3.1 does not require resolving this — the manual-scale-factor catalogue entry below is correct regardless of whether the divergence is split-lag or share-class. |

**Empirical conclusion:** the most likely cause is a recent reverse-split that **IB has reflected but EODHD has not yet propagated** to its EOD feed. This is a known EODHD lag failure mode on volatile / leveraged ETPs (issuers commonly do 10:1 reverse-splits on 3× products after drawdowns; vendor splits-history feeds sometimes lag by days to weeks). The exact root cause does not need to be resolved at M3.1 — the M3.1 narrow fix is *operator-confirmed scale factor against IB live reference*, captured in a per-instrument convention catalogue. When EODHD propagates the missing split, `adjusted_close` will diverge from `close` and the catalogue entry can simplify.

The Phase 2 readiness audit ([PHASE_2_READINESS.md](../PHASE_2_READINESS.md)) and the M3.1 NEXT_PROMPT.md surface two implementation routes:

- **Route A — IB live market data subscription for sizing reference.** Sizer takes the live IB reference price instead of EODHD close. Authoritative; eliminates the unit-of-quote question entirely; sets up M7 parity diagnostics. Cons: monthly subscription cost (LSEETF tier per [KB-2](../kb/ib_capability_matrix.md)); operator-tariff-dependent.
- **Route B — EODHD-convention conversion at sizing time.** Per-instrument convention catalogue (split-adjustment, currency conversion, manual scale factor) applied at sizing-time. Pros: zero subscription cost; immediate fix; reversible. Cons: per-instrument convention may differ; reverse-split events require manual catalogue updates.
- **Hybrid — B now, A later.** Route B as M3.1's narrow fix; Route A as the M7 / live-cutover-time eventual replacement.

### Decision

**Hybrid: B-now, A-later, with A bounded to free IB market-data tiers only.**

Five concrete commitments:

1. **B-now: per-instrument convention catalogue** at `src/blive/adapters/eodhd/conventions.py` (the first non-script EODHD module; precursor to the eventual `EODHDDataSource` per [ADR-014](#adr-014--data-sources-via-clean-api-abstraction)). The catalogue is a module-level dict literal mapping IB symbol → `Convention` dataclass. Conventions supported at v0.1: `IDENTITY` (no conversion; default for unlisted symbols) and `MANUAL_SCALE` (`divisor: Decimal`, `source: str`, `notes: str`). Future conventions land here when M3.2's window or future ETP refreshes surface them.

2. **A-later, free-MD-only.** When the M7 parity-diagnostic surface is built, the Route A live-IB-MD reference path is **bounded to instruments that resolve via free IB market-data tiers** (no LSEETF or other paid subscription). This is an explicit, accepted limitation: instruments outside the free tier stay on B indefinitely. Rationale: operator-stated cost discipline at M3.1 entry (no monthly LSEETF subscription); the resulting blast radius is "Route A handles the easy cases (US-equity SMART feeds), Route B handles the hard cases (LSE-ETF / leveraged ETPs)" rather than full A coverage. Captured here so a future M7 implementor doesn't re-litigate scope.

3. **Sizing-time conversion, not data-time.** The `PaperMarketData` parquet stays unchanged — it's the EODHD raw record per [ADR-029](#adr-029--papermarketdata-as-marketdataport-adapter-fixture-backed-parquet). Conversion lives at the pipeline boundary (the `_price_lookup` closure in `run_ib_multi_pipeline`) so the parquet remains a clean vendor-pristine record and the Sizer continues to receive a single `Decimal` price per `Instrument`. This preserves the [ADR-027](#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero) Sizer purity contract.

4. **RC-10 (price sanity) lands as the code-side capture** of the M3.1 fix per [INV-4 v0.2](../inv/risk_checks.md). Default threshold ±50% (not the v0.1 ±20%); the wider band is calibrated for leveraged ETPs whose maximum daily range hits 11.74% (per INV-14 v0.7 QQL3 observation) — ±20% would false-positive on legitimate gap-overnight moves. RC-10 catches catalogue-miss / convention-error / reference-price-stale cases at sizing time before IB error 110 surfaces.

5. **PROPOSED → ACCEPTED on first wire exercise.** Per the M2-IB pattern (ADR-031, ADR-032, ADR-048, ADR-049), this ADR stays PROPOSED in the working tree until `scripts/run_m2ib6_ib_paper.py --max-bars 5` against IB Paper produces a QQL3 sized within ±1% of the IB-USD-equivalent target exposure with no IB error 110. The flip to ACCEPTED is a header-only edit (date trail in status field) in the wire-validation commit; body stays append-only.

### Alternatives Considered

1. **Pure Route A — subscribe to IB live MD for the full universe at M3.1.** Rejected — operator declined the subscription cost at M3.1 entry; pulling A forward to M3.1 would add a multi-day Operator + IB-Paper-tariff configuration loop unrelated to the unit-of-quote question. A as M7 work matches the original NEXT_PROMPT v1.0 framing and the M3.1 narrow scope.
2. **Hardcode QQL3 = ÷10 directly in the pipeline `_price_lookup` closure.** Rejected — premature crystallisation; pollutes the pipeline with broker-specific knowledge of one instrument; doesn't generalise when M3.2's window surfaces a second instrument with a different convention. The per-instrument catalogue at `blive.adapters.eodhd.conventions` is the same effective code at one extra indirection that scales gracefully.
3. **YAML-driven catalogue under `~/.blive/config/` (paralleling the [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets) secrets pattern).** Rejected at M3.1 — premature plumbing for a single-entry catalogue. Forward-noted in [TASK_REGISTRY Sketched M4+](../../TASK_REGISTRY.md) (the "vendor-convention catalogue centralisation" line) for promotion when the catalogue grows ≥3-5 entries or operator-side editing pressure justifies the YAML loader.
4. **Apply the conversion inside `refresh_eodhd_signals.py`** (write the IB-equivalent price to the parquet directly). Rejected — corrupts the vendor-pristine record; hides the convention from any other consumer of the parquet (notebooks, parity-diagnostic re-runs at M7); makes catalogue updates require a parquet refresh. Sizing-time conversion keeps the catalogue close to the consuming code path.
5. **Detect splits automatically by comparing latest EODHD close to a moving-average baseline.** Rejected — fragile (legitimate gap-overnight on volatile ETPs would false-trigger); operator-confirmed catalogue entries are simpler and auditable. RC-10 (price sanity) is the auto-detection layer for catalogue-miss cases; the catalogue itself is operator-curated.
6. **Use `Instrument.multiplier` to encode the conversion.** Rejected — `multiplier` is the contract-side multiplier (e.g. options 100×; futures contract size) per [DD-1](../dd/domain_objects.md). Overloading it with vendor-side unit conversion confuses two distinct semantics (broker-side vs vendor-side scaling) and breaks the broker-neutral `Instrument` shape.

### Consequences

- **Positive:** M3.1 fix lands as a small, contained surface — one new module (`blive.adapters.eodhd.conventions`), one new RiskEngine check (RC-10), one closure-level conversion at the `run_ib_multi_pipeline` boundary. Sizer purity preserved; PaperMarketData parquet unchanged. Catalogue scales to N instruments without further plumbing.
- **Positive:** RC-10 implementation is the code-side capture of the discrepancy — future similar discrepancies (any EODHD-vs-IB unit-of-quote drift on a new ticker; any catalogue entry that becomes stale) trip RC-10 at sizing time before IB error 110 surfaces. Diagnostic surface is operator-friendly (`RiskBreach` event with the discrepancy magnitude in the detail field).
- **Positive:** The M3.2 empirical paper-mode window now generates correctly-sized positions on QQL3, restoring the cap-binding behaviour the OQ-031 decision rests on. M3.2 readiness is unblocked.
- **Negative:** The convention catalogue is operator-curated. When the issuer does another reverse-split or EODHD updates its splits feed, the catalogue entry must be revised manually. This is an accepted maintenance burden for the M3.1 → M7 window. Forward-noted: when the operator notices RC-10 firing on a previously-conformant instrument, that's the signal to revise the catalogue.
- **Negative / risk — convention drift goes undetected if RC-10 is misconfigured.** The ±50% threshold is wide enough that a small (~5%) convention-drift wouldn't trigger it. Mitigation: catalogue entries carry a `notes: str` field where the operator records the date-of-confirmation against IB live reference; revisit cadence at each M-close per [CONTEXT_PROTOCOL §6.3](../../CONTEXT_PROTOCOL.md) review-cadence rules. Forward-list for M7: tighten RC-10 to per-instrument bands (e.g. QQL3 ±15% based on its volatility profile, IBTL ±5%) once the M3.2 window provides empirical volatility characterisation.
- **Risk — A-later free-MD-only constraint may force B as the *permanent* solution for QQL3-class instruments.** Accepted at M3.1 entry. The trade-off is documented; operator may revisit at M7 if the LSEETF subscription becomes affordable or if the strategy regime shifts toward instruments on free tiers.
- **Follow-ups:**
  - Wire exercise: `scripts/run_m2ib6_ib_paper.py --max-bars 5` during LSE RTH; QQL3 sized within ±1% of IB-USD-equivalent; no IB error 110. Flip ADR-050 PROPOSED → ACCEPTED in the wire-validation commit.
  - Catalogue v0.1 entry for QQL3: `MANUAL_SCALE(divisor=10.0, source="IB live reference, M2-IB.6.2c", notes="EODHD-side recent reverse-split lag; revisit when /api/splits/QQQ3.LSE picks up the event")`.
  - INV-4 v0.1 → v0.2 (RC-10 row promoted to implemented; threshold ±20% → ±50%).
  - INV-14 grows: error 110 row promoted from forward-list to catalogue with the EODHD-driven LMT-out-of-range observation as the canonical example.
  - KB-15 (`parity_methodology`) MISSING → DRAFT v0.1 (unit-of-quote / reverse-split section only; full M7 parity envelope defers to M7).
  - DD-7 footnote on the QQL3 reverse-split convention (cross-link to KB-15 + this ADR).
  - TASK_REGISTRY Sketched M4+ gains a forward-note: "vendor-convention catalogue centralisation — promote `blive.adapters.eodhd.conventions` dict-literal to YAML if the surface grows ≥3-5 entries or operator-side editing pressure builds".
  - M7 parity work picks up the A-later piece **bounded to free-MD instruments only**; this ADR is load-bearing for the bounded scope.

### Cross-References

- [ADR-014](#adr-014--data-sources-via-clean-api-abstraction) — EODHD data-source abstraction; this ADR adds the first concrete vendor-side convention layer.
- [ADR-017](#adr-017--live-data-hybrid-eodhd--ib-streaming-per-instrument-routing) — hybrid EODHD+IB routing per-instrument; the Hybrid B-now / A-later split here aligns with the per-instrument routing principle ADR-017 codifies.
- [ADR-027](#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero) — Sizer purity; this ADR preserves it (conversion at the pipeline boundary, not in the Sizer).
- [ADR-029](#adr-029--papermarketdata-as-marketdataport-adapter-fixture-backed-parquet) — PaperMarketData parquet contract; preserved (parquet remains vendor-pristine).
- [ADR-035](#adr-035--secrets-handling-discipline-blivesecrets) — secrets pattern; the M4+ YAML-catalogue forward-note parallels this pattern.
- [ADR-047](#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043) — PRIIPs-compliant universe; QQL3 is the leveraged leg that surfaces the discrepancy.
- [ADR-049](#adr-049--ordertypeadaptive_mkt-for-ibalgo-adaptive-routing-empirical-pma-cap-finding) — PMA-cap empirical finding; the EODHD-vs-IB discrepancy was first documented as a side-finding inline in ADR-049's `Side-finding` block.
- [INV-4](../inv/risk_checks.md) — RC-10 row promoted to implemented at v0.2.
- [INV-14](../inv/ib_error_codes.md) — error 110 promoted from forward-list to catalogue.
- [KB-15](../kb/parity_methodology.md) — stub-DRAFT v0.1 captures the unit-of-quote section.
- [DD-7](../dd/instrument_dictionary.md) — footnote on the QQL3 reverse-split convention.
- [OQ-031](OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account) — Phase 1 deployment trade-off; M3.1 unblocks the M3.2 evidence collection that grounds OQ-031 resolution.
- [PHASE_2_READINESS.md](../PHASE_2_READINESS.md) — Phase 2 entry audit; surfaced the EODHD-vs-IB question as a Phase 1 deployment-decision dependency.
- `scripts/probe_qql3_unit_of_quote.py` — EODHD-side investigation probe.

---

## ADR-051 — Normalize IB order prices to the contract tick grid at submit time

- **status:** ACCEPTED (drafted 2026-06-05 at M3.1b PROPOSED; flipped ACCEPTED 2026-06-05 on the clean LSE-RTH wire run — QQL3 limits snapped to its 0.10 grid on the live wire (`38.52→38.5`, `44.15→44.2`, …) and placed with **no IB error 110** (6 submitted, 0 rejected; IBTM filled), jointly with ADR-050 per Decision #6)
- **date:** 2026-06-05
- **decider:** Oleg (with Claude)
- **refines:** [ADR-032](#adr-032--instrument-resolution-policy-blive-instrument--ib-contract) (contract facts), [ADR-046](#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032) / ADR-048 (SMART routing produces the contracts whose tick grids this snaps to)
- **companion:** [ADR-050](#adr-050--eodhd-vs-ib-unit-of-quote-conversion-at-sizing-time-hybrid-b-now--a-later-free-md-only) (the *other* price-conditioning step — magnitude; this is grid), [INV-14](../inv/ib_error_codes.md) (error 110 now two sub-causes), [DD-7](../dd/instrument_dictionary.md) (tick / market-rule metadata)

### Context

The M3.1 wire-validation run on 2026-06-05 (`--order-type LMT --max-bars 5`, LSE RTH) confirmed [ADR-050](#adr-050--eodhd-vs-ib-unit-of-quote-conversion-at-sizing-time-hybrid-b-now--a-later-free-md-only)'s unit-of-quote fix works — QQL3 sized **65 sh @ ~$39** (vs the pre-fix 6 sh @ ~$381), a clean ~10× correction — but surfaced a **second, independent cause of IB error 110**: tick-size non-conformance. blive's pipeline hardcoded limit-price rounding to `quantize(0.01)` (one penny), but QQL3's minimum price variation on LSEETF is **0.10**. Limit prices `38.52` / `42.83` / `44.15` were rejected (error 110) while `39.60` / `41.50` passed — the clean signature of a 0.10 tick grid.

This is **distinct** from ADR-050: ADR-050 fixed the price *magnitude* (vendor→IB units); the price was correctly ~$39 yet still mis-rounded to a sub-tick value. The two were entangled in the original error-110 observation (a $381 price is *both* wrong-magnitude and off-grid), so fixing magnitude alone exposed the grid bug underneath.

Generalising: the minimum price increment is (a) **per-contract**, (b) sometimes price-**banded** (LSE / Euronext / MiFID-II tick regimes grow the increment with price; IB encodes these as *market rules*), and (c) applies to **every priced field** (limit, stop), not just QQL3 limits. A QQL3-specific constant would re-break on the next instrument — the same failure mode ADR-050's catalogue avoids for magnitude.

### Decision

**Normalize every priced order to its contract's valid price grid at the adapter boundary (`IBBroker.submit`), automatically, using a per-contract increment table sourced from IB and a pure snapping function.** Six commitments:

1. **Snap at submit, in the broker — universal by construction.** `IBBroker` snaps `limit_price` / `stop_price` to the contract grid inside `submit()` (the single `domain Order → ib_async order` chokepoint), so *any* strategy / pipeline / reconciliation-driven order is grid-valid without the caller knowing tick rules exist. Pipelines no longer round prices themselves — the hardcoded `quantize(0.01)` in `run_ib_(multi_)pipeline._ib_order_from_desired` is **removed**; pipelines emit the economically-intended price and the broker renders it venue-legal.

2. **Magnitude vs grid live at different layers — on purpose.** ADR-050's unit-of-quote conversion stays at **sizing time** (the pipeline) because the share *quantity* depends on it. Grid-snapping lives at **submit time** (the broker) because it touches only the price field, never the quantity. The split is principled, not accidental: *magnitude changes how many shares; grid changes only the limit's last decimal.* Recorded so a future reader does not "unify" them into a sizing-time bug.

3. **Band-table interface from day one (handles price-dependent ticks).** The snapping function consumes a **price-increment table** — `Sequence[PriceIncrement(low_edge, increment)]` — not a scalar. `IBPriceRuleService` populates it from the contract's **market rule** (`reqContractDetailsAsync` → `marketRuleIds` → `reqMarketRuleAsync` → `PriceIncrement` bands), falling back to a single-row `[(0, minTick)]` table when no rule is available. A flat-tick instrument (QQL3 ≈ 0.10) is just a one-row table; a banded venue works without redesign. Tables are cached per `Instrument` (mirrors the resolver's conId cache) with a `clear_cache` hook for M5 corp-action invalidation.

4. **Pure, policy-parameterised snapping (OCP).** `snap_price(price, increments, *, side, policy)` is a pure function in `blive.adapters.shared.price_grid` (broker-agnostic; IG-reusable). `RoundingPolicy` defaults to **NEAREST** (the sub-tick move is dwarfed by the pipeline's ±50bps limit buffer and is unbiased); **CONSERVATIVE** (BUY↓ / SELL↑ — never worse than the computed price) is implemented and parked as the recommended real-money policy. New policies / venues extend behaviour without modifying the snap core.

5. **Block (don't ship) on missing tick metadata.** If `reqContractDetailsAsync` yields neither a market rule nor a positive `minTick`, `IBPriceRuleService` raises `PriceRuleUnavailable` and the broker does **not** place the order — it surfaces a `REJECTED` with a clear diagnostic rather than send a price it cannot validate (which would reproduce error 110). The cost is bounded: the table is cached after first success, so the only window a fetch failure can block is the *first* order for an instrument per process.

6. **PROPOSED → ACCEPTED on first clean wire run, jointly with ADR-050.** Same pattern as ADR-050: stays PROPOSED until an LSE-RTH `--order-type LMT --max-bars 5` run places QQL3 / IBTL / IBTM limits with **no IB error 110**. Because ADR-050's flip criterion *also* requires "no error 110", the two now flip **jointly** on that run (the magnitude fix is necessary but not sufficient — the grid fix is the missing half). The wire-validation commit flips both header-only.

### Alternatives Considered

1. **Per-instrument tick catalogue (mirror ADR-050's conventions dict).** Rejected as the *primary* source — tick size is an authoritative IB contract fact available over the wire; a hand-maintained catalogue would drift and duplicate what `reqContractDetails` already knows. (The market-rule fetch *is* the generalisation; `minTick` is the fallback.)
2. **Round to a coarse fixed tick (e.g. 0.05 / 0.10) for everyone.** Rejected — wrong for fine-tick instruments (US equities 0.01), needlessly degrades prices, still wrong for banded venues at high prices.
3. **Catch error 110 and retry with an adjusted price.** Rejected — reactive, costs a wire round-trip + pacing budget per retry, and the error doesn't tell you the correct increment.
4. **`minTick` only (ignore market rules).** Rejected as the design, kept as the *fallback* — insufficient for banded venues where the valid tick at a given price is coarser than the global `minTick`.
5. **Snap in the Sizer (domain).** Rejected — violates [ADR-027](#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero) Sizer purity; the Sizer is broker-neutral and has no contract / venue data.
6. **Snap in each pipeline explicitly.** Rejected — every strategy / pipeline would have to remember; the whole point is that the broker makes it impossible to forget.

### Consequences

- **Positive:** error 110 from off-grid prices is structurally impossible for any order through `IBBroker` — not just QQL3, not just the current pipelines. The pipeline gets *simpler* (drops its rounding line). Banded venues are handled. The pure snapping fn is exhaustively unit-testable.
- **Positive:** clean composition with ADR-050 — convert magnitude (pipeline), then snap grid (broker); both are "render economic intent into a venue-legal instruction", at the right layers.
- **Positive / division of labour:** RC-10 (magnitude sanity, ±50%) catches *wrong* prices before submit; snapping handles *increment* validity. A wildly-off price is caught by RC-10; snapping only ever moves a sane price by <1 tick. No new RiskCheck needed.
- **Negative / cost:** first order per instrument per process pays 1–2 cached wire calls (`reqContractDetails` + `reqMarketRule`) against the `global` pacing budget ([KB-3](../kb/ib_pacing_spec.md)). Cached thereafter; negligible.
- **Negative / risk — band-crossing on round-up.** Rounding up across a band boundary could in principle land off the higher band's grid; benign in practice because IB constructs band edges to sit on the coarser grid. Documented as an assumption; revisit only if a venue violates it.
- **Follow-ups:**
  - Wire exercise (joint with ADR-050): `--order-type LMT --max-bars 5` LSE RTH; QQL3 / IBTL / IBTM limits placed with no error 110; flip ADR-050 + ADR-051 PROPOSED → ACCEPTED.
  - INV-14 error 110 row: document the two sub-causes (magnitude → ADR-050; tick grid → ADR-051).
  - DD-7: per-contract tick / market-rule metadata now sourced + cached by `IBPriceRuleService`.
  - Size / lot conformance (`minSize` / `sizeIncrement`) is the **same seam** (broker-on-submit, contract-rule-cached) — left as a documented forward-extension, not built (no Phase 1 instrument needs it).

### Cross-References

- [ADR-050](#adr-050--eodhd-vs-ib-unit-of-quote-conversion-at-sizing-time-hybrid-b-now--a-later-free-md-only) — the magnitude half of price-conditioning; this is the grid half. The two flip ACCEPTED jointly on the clean LMT wire run.
- [ADR-027](#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero) — Sizer purity preserved (snapping is in the broker, not the Sizer).
- [ADR-032](#adr-032--instrument-resolution-policy-blive-instrument--ib-contract) / [ADR-046](#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032) / ADR-048 — instrument resolution + SMART routing produce the contracts whose tick grids this reads.
- [INV-14](../inv/ib_error_codes.md) — error 110 second sub-cause (tick non-conformance).
- [DD-7](../dd/instrument_dictionary.md) — tick / market-rule metadata.
- `blive.adapters.shared.price_grid` (pure snap) / `blive.adapters.ib.price_rules` (IB source + cache) — the implementation.

---

## ADR-052 — Phase 1 accepts the PMA-bound leveraged-leg non-fill (OQ-031 Option 1)

- **status:** ACCEPTED (drafted 2026-06-05 at M3.3 PROPOSED; flipped ACCEPTED same-session on operator confirm — resolves [OQ-031](OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account) on the M3.2 empirical capture)
- **date:** 2026-06-05
- **decider:** Oleg (with Claude)
- **supersedes:** none
- **resolves:** [OQ-031](OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account) (Phase 1 deployment under PMA-bound retail account)
- **refines:** [ADR-043](#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2) (Phase 1 A3 strategy), [ADR-047](#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043) (PRIIPs universe) — the QQL3 leveraged leg is retained for Phase 1 but flagged *provisional* (both carry a `refined-by: ADR-052` backref); the leveraged-equity redesign is deferred to Phase 2 ([OQ-032](OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure)).
- **companion:** [ADR-049](#adr-049--ordertypeadaptive_mkt-for-ibalgo-adaptive-routing-empirical-pma-cap-finding) (the empirical PMA-cap finding this operationalises), [ADR-016](#adr-016--leverage-support-both-margin-financed-and-leveraged-etf-instruments) (margin-financed leverage — basis for OQ-032's leverage-preserving path), [INV-14 v0.9](../inv/ib_error_codes.md) (warning 2161 + error-110 rows)

### Context

[OQ-031](OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account) asked which of four deployment-mode options Phase 1 commits to for live cutover (G4), given M2-IB.6.2c's finding that IB warning 2161 (Price Management Algo / regulatory disruptive-orders cap) binds structurally on QQL3 (3× Nasdaq leveraged ETP on LSEETF) for the operator's UK-retail IB-Paper account. M3 sequenced this *inform-then-resolve* ([TASK_REGISTRY](../../TASK_REGISTRY.md) plan-call #1): M3.2 captures the fill profile; M3.3 (this ADR) resolves on the data.

**The M3.2 evidence** (`~/.blive/data/m3_2_window/runs.jsonl`, two flip-spanning LSE-RTH replay captures 2026-06-05, on now-correctly-sized ([ADR-050](#adr-050--eodhd-vs-ib-unit-of-quote-conversion-at-sizing-time-hybrid-b-now--a-later-free-md-only)) and on-grid ([ADR-051](#adr-051--normalize-ib-order-prices-to-the-contract-tick-grid-at-submit-time)) orders — **zero error 110, zero rejects, zero breaches**):

| Run | window | regime flips | QQL3 sub/fill | IBTM sub/fill | 2161 cap-binding |
|-----|--------|--------------|---------------|---------------|------------------|
| 1   | `--max-bars 40` | 2 | 25 / **0** | 3 / **3** | 0 |
| 2   | `--max-bars 60` | 2 | 44 / **0** | 3 / **3** | 0 |
| agg | — | 4 | **69 / 0 (0%)** | **6 / 6 (100%)** | **0** |

Every QQL3 order reached ACCEPTED then CANCELED on engine-timeout (`observed_error_codes` = `{202: N}`, IB cancel confirmations); every IBTM order reached ACCEPTED then FILLED. **The 3× leveraged equity leg does not fill; the 1× Treasury leg fills cleanly.**

Load-bearing nuance: QQL3 was routed `ADAPTIVE_MKT` (per the driver's `order_type_by_symbol` map), so the *visible* 2161 cap never fired (`cap_binding_2161_count` 0, `mktCapPrice` 0.0) — yet QQL3 still did not fill, unlike the M2-IB.6.2c raw-MKT runs where 2161 fired visibly. **The non-fill is robust to the order-type mechanism**: the equity leg fails via the visible PMA cap (raw MKT) *and* via the Adaptive algo declining to cross within the wait. Two honest caveats, recorded not buried: (a) the capture's 10s `--event-wait-seconds` contributes to the Adaptive non-fill — a longer-resting live order could mean-revert into a fill — but the raw-MKT cap binds independent of time (M2-IB.6.2c's 60s wait was also 0/5) and the structural PMA constraint on leveraged ETPs for UK retail is established, so only the *exact* live fill-rate is open (it re-derives at M7 parity); (b) IBTL had no eligibility-driven orders in these windows, so the Treasury evidence is IBTM-only.

### Decision

**Resolve OQ-031 with Option 1: accept the leveraged-equity-leg non-fill as a real Phase-1 deployment characteristic — no code change — and defer the leveraged-leg redesign to Phase 2.**

1. **Phase 1 deploys A3 as-is**, with the documented understanding that on this PMA-bound UK-retail account the QQL3 (3×) leg structurally ≈ never fills, so **live behaviour is Treasury-leg-dominated** (the strategy executes effectively as its 1× Treasury sleeve). Acceptable for Phase 1 because Phase 1's purpose is *execution-stack validation* — which the M2-IB → M3 ladder has substantially completed (FSM, SMART/LSEETF routing, sizing per ADR-050, tick-grid per ADR-051, RiskEngine, mixed-currency surface all wire-validated; the remaining M3.4–M3.6 items are P&L-reconciliation / chaos-drill / KB-STABLE work, not execution-correctness gaps) — **not** P&L generation on a paper account.

2. **No amendment to ADR-043 / ADR-047 now, and no new RiskCheck or order-path code.** The QQL3 leg is *retained* for Phase 1 but flagged **provisional** (a `refined-by: ADR-052` backref is added to ADR-043 + ADR-047 frontmatter for discoverability): its non-fill is a known, documented execution property, not a defect.

3. **The redesign that would restore the strategy's intended leveraged equity exposure is forward-listed to Phase 2 entry, captured as [OQ-032](OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure).** Phase 1 surfaced a deeper constraint — a *trilemma*: a UK-retail **Cash** account has **no** open path to leveraged equity exposure. **PRIIPs/KID** blocks US-domiciled leveraged ETPs (ADR-047); the **PMA cap (2161)** blocks UK-listed leveraged ETPs (ADR-049 / this ADR); a **Cash** account blocks margin-financed leverage. OQ-032 carries the *full* design space — including the **leverage-preserving** path (≈3× via 3:1 margin on a plain 1× Nasdaq-100 UCITS ETF, whose ~1–1.5% daily range very likely does not trip the volatility-triggered PMA cap; per [ADR-016](#adr-016--leverage-support-both-margin-financed-and-leveraged-etf-instruments) blive already supports margin-financed leverage) **alongside** de-levering to 1×/1×, Pro-Client classification, a mean-reversion restructure, and an archetype swap. The M3→M4 boundary is the natural home for this strategy-identity decision, where the M7 parity re-derivation informs it.

4. **Live-cutover posture:** before any real-money cutover (M8, well beyond G4) the operator monitors the QQL3 fill-rate empirically; if the Treasury-dominated profile is unacceptable for live, the Phase-2 redesign (OQ-032) supersedes this acceptance. Options 2 (Pro Client) and 4 (passive-limit-only) remain available re-entry points but are not chosen now.

### Alternatives Considered

1. **Option 3 — substitute the leveraged leg now** (UK-listed 1× UCITS Nasdaq analogue → 1×/1×). The 0% fill is the strongest argument for it, and it is the only OQ-031 option that makes the strategy trade both legs — but it *drops* the leverage. **Deferred, not rejected:** it changes strategy identity (amends ADR-043 + ADR-047) and costs a universe re-validation half-session. Deferred into [OQ-032](OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure), which carries the *broader* design space — including the **leverage-preserving** margin-on-1×-UCITS path that none of the four OQ-031 options captured (the omission this ADR's review corrected).
2. **Option 2 — MiFID II Professional Client classification** (enables `priceManagementOff`, so QQL3 itself fills — a leverage-*preserving* path). Declined at M2-IB.6.1; the M3.2 data does not move the wealth / experience / transaction-frequency thresholds. Re-entry point preserved via OQ-032.
3. **Option 4 — passive-limit-only restructure** (embrace the cap as a mean-reversion model; keeps the leveraged ETP but changes the strategy's character). Largest pivot from the A3 trend-following intent; needs a fresh ADR + re-derived parity envelope. The data does not point here — the equity leg's non-fill is a constraint to design around, not evidence the strategy *should* mean-revert.

### Consequences

- **Positive:** M3 gets an auditable, data-grounded deployment-mode commitment (data → Option 1 → why) with **no code change / no regression risk** — G3-IB-A3 and all M2-IB wire validations stand unchanged.
- **Positive:** the strategy-identity decision lands at the phase boundary where it belongs, informed by the M7 parity re-derivation, not rushed into a Phase-1-close edit; OQ-032 preserves the *full* design space (incl. the leverage-preserving margin path) so the Phase-2 decision is not pre-narrowed toward de-levering.
- **Negative / honest:** the Phase 1 *strategy as deployed* is materially not the intended 3×/1× trend-follower — it is a 1× Treasury sleeve in practice. Acceptable only under "Phase 1 = validate the engine"; explicitly **not** a real-money endorsement of A3-as-is.
- **Negative / risk:** if a future change makes the equity leg fill (account / venue change), live behaviour shifts toward the 3× profile without re-validation; mitigated because OQ-032 owns the redesign and any such change routes through it.
- **Follow-ups:**
  - Open [OQ-032](OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure) — Phase 2 A3 leveraged-leg redesign (full design space; target Phase 2 entry / M4).
  - Flip OQ-031 OPEN → RESOLVED-BY-ADR-052 (status field only; body untouched, append-only).
  - Add `refined-by: ADR-052` to ADR-043 + ADR-047 frontmatter (discoverability; the QQL3 leg is now provisional).
  - TASK_REGISTRY M3.3 marked resolved; G4 exit-criterion #1 satisfied. No INV-14 / INV-4 / code change.

### Cross-References

- [OQ-031](OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account) — resolved by this ADR (Option 1).
- [OQ-032](OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure) — the deferred Phase-2 redesign this ADR forward-lists (carries the leverage-preserving margin path).
- [ADR-049](#adr-049--ordertypeadaptive_mkt-for-ibalgo-adaptive-routing-empirical-pma-cap-finding) — the empirical PMA-cap finding this operationalises into a deployment decision.
- [ADR-043](#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2) / [ADR-047](#adr-047--priips-compliant-universe-for-phase-1-a3-strategy-refines-adr-043) — the A3 strategy + PRIIPs universe whose QQL3 leg is retained-but-provisional for Phase 1.
- [ADR-016](#adr-016--leverage-support-both-margin-financed-and-leveraged-etf-instruments) — blive supports margin-financed leverage (the basis for OQ-032's leverage-preserving path).
- [INV-14 v0.9](../inv/ib_error_codes.md) — warning 2161 (PMA cap) + error-110 rows.
- M3.2 capture: `~/.blive/data/m3_2_window/runs.jsonl` (two flip-spanning runs, 2026-06-05) — the empirical basis.

---

## ADR-053 — Upgrade to Python 3.12

- **status:** ACCEPTED (operator-authorised 2026-06-05; `.venv` recreated on 3.12.12 with all gates green — 591 tests, mypy --strict, black, isort, lint-imports)
- **date:** 2026-06-05
- **decider:** Oleg (with Claude)
- **supersedes:** none (the "Python 3.11.x exactly" baseline lived in CLAUDE.md + pyproject, never a formal ADR; this ADR establishes the version policy)
- **companion:** btest `fd106f9` (requires-python relax) + `32dab28` (remove unused/broken `signum`); [OQ-032](OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure) (the Phase-2 strategy that motivated it)

### Context

blive — and its editable sibling `quantdsl-backtest` (btest) — pinned **Python 3.11.x exactly** as a bootstrap choice. Phase 2's incoming strategy (the VIX-term-structure backtest in `lab/research/r_lev_001_triple_leveraged_etf`, which feeds [OQ-032](OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure)) requires **Python 3.12**. Since blive imports btest editable, both must move together.

A non-destructive 3.12 resolution + install + dual-suite dry-run (2026-06-05) proved feasibility: every C-extension dep has 3.12 wheels (numba 0.65.1, vectorbt 1.0.0, arcticdb 6.18.0), **blive's 591 tests and btest's 317 unit tests pass on 3.12**, and the only snags were tooling-side (not 3.12): btest's `requires-python` pin, an unused-but-broken `signum` optional dep, pandas over-reaching to the breaking 3.0 major, and mypy floating to 2.x (1 new finding). The current env was *already* on the modern majors (numpy 2.4, pandas 2.3, numba 0.65, vectorbt 1.0), so 3.12 is "same deps, newer interpreter".

### Decision

**Adopt Python 3.12** (the latest *viable* — see alternatives).

1. **`requires-python = ">=3.11"`** in blive + btest (allow 3.11 *and* 3.12 through the transition; don't strand anyone on 3.11). `[tool.mypy] python_version = "3.12"`; `[tool.black] target-version = ["py312"]`.
2. **Pin `pandas>=2.0,<3.0`.** pandas 3.0 is a breaking major (Copy-on-Write default, etc.); isolate the interpreter change from a dataframe-semantics change. numpy stays 2.x (already there).
3. **Adopt mypy 2.x, pinned `==2.1.0`** (like black/isort — the type gate's output must be reproducible). The one new 2.x finding — `float()` on a `Series`-typed scalar access in `ib_pipeline.py` — is fixed with a `cast` (the runtime value is a scalar). Chosen over pinning `mypy<2`, to keep the type checker current.
4. **btest: removed the unused/broken `signum`** core dep (research-only charting, try/except-guarded, never imported in `src`/tests; its git repo publishes mismatched `signum-charts` metadata that breaks `uv`). It blocked the 3.12 resolve (btest `32dab28`).
5. **Recreated `.venv` on 3.12** (`uv venv --python 3.12` + `uv sync --extra dev`); `uv.lock` re-locked. All gates green.

### Alternatives Considered

1. **Stay on 3.11.** Rejected — Phase 2's strategy needs 3.12; deferring just moves the work.
2. **Go to the latest (3.13 / 3.14).** Rejected — `numba` / `vectorbt` / `arcticdb` lag newer CPython; 3.12 is the latest version btest's heavy dep tree installs on. 3.13+ is a future step once those catch up.
3. **Pin `mypy<2`** (zero code change). Rejected — the one finding is a legitimate 1-line typing fix; keeping mypy current is worth more.
4. **Let pandas float to 3.0.** Rejected for *this* change — it couples the interpreter upgrade to a breaking dataframe major; pin `<3` and revisit pandas 3.0 on its own.

### Consequences

- **Positive:** blive + btest run on 3.12; Phase 2's 3.12-only strategy is unblocked; the dep tree is modern + 3.12-wheeled.
- **Positive:** the formatter + type gates are now all version-pinned (black 26.3.1, isort 8.0.1, mypy 2.1.0) — the gate is fully reproducible (the lesson from the M2-IG-era black drift).
- **Negative / deferred:** pandas 3.0 and Python 3.13/3.14 are deliberately deferred (separate steps, when deps catch up). `signum` research charts must be installed manually (corrected name `signum-charts`).
- **Negative / risk:** `requires-python >=3.11` still allows 3.11 — acceptable during the transition; tighten to `>=3.12` once 3.11 is retired.
- **Follow-ups:** revisit pandas 3.0 + Python 3.13 when numba/vectorbt support them; consider `requires-python >=3.12` later.

### Cross-References

- btest `fd106f9` (requires-python >=3.11) + `32dab28` (remove signum) — the sibling-repo half.
- [OQ-032](OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure) — the Phase-2 strategy redesign whose VIX/TQQQ/VXX notebook needs 3.12.
- `pyproject.toml` (requires-python / mypy / black / pandas / mypy pins); `uv.lock` (re-locked for 3.12); `src/blive/runtime/ib_pipeline.py` (the mypy 2.x cast fix); `CLAUDE.md` (toolchain line).

---

## Changelog

- **v0.1 (2026-04-26)** — initial bootstrap. ADR-001..012 backfill from REQUIREMENTS rationale; ADR-013..019 from Oleg's 2026-04-26 OQ resolution session.
- **v0.2 (2026-04-26)** — added ADR-020..023 covering Phase 1 operational specifics: NAV slice (5–10% cap 10%), CAC ETF proxy (`CAC.PA`), TKAN freshness window (30d hard / 21d warn), TKAN artefact path and refresh ownership.
- **v0.3 (2026-04-26)** — added ADR-024 (RETRO artefact type) and ADR-025 (protocol amendment for milestone-close + phase-boundary handoff rules).
- **v0.4 (2026-04-26)** — added ADR-026 (agentic-execution layer; human-governance / agent-execution division of labour; five-layer adoption stack).
- **v0.5 (2026-04-27)** — added ADR-027 (Sizer rounding policy: integer shares, truncate toward zero), ADR-028 (Strategy config shape: Python `build_strategy()` + blive YAML overrides), ADR-029 (`PaperMarketData` as `MarketDataPort` adapter, fixture-backed parquet) — drafted PROPOSED, accepted by operator same day; status flipped to ACCEPTED for all three.
- **v0.6 (2026-04-27)** — added ADR-030 (per-archetype btest interpreter dispatch; resolves OQ-030; amends ADR-010 prose), ADR-031 (token-bucket rate limiter shape for IB adapters), ADR-032 (instrument resolution policy `blive.Instrument` ↔ IB `Contract` / `ConID`), ADR-033 (`AccountUpdate` event shape and 30-s diff-suppressed cadence). All four PROPOSED at M2 entry; awaiting operator review before flip to ACCEPTED.
- **v0.7 (2026-04-27)** — operator-driven pivot to IG demo bridge (M2-IG) while IB Paper account is being reopened. Added cross-cutting ADRs: ADR-034 (multi-broker registry pattern; extends ADR-004 with explicit registry, package layout, and import-linter contract for N>2 brokers), ADR-035 (secrets handling discipline: `~/.blive/secrets/{broker}.env`, env-var override, log redaction list, never-in-git rule). Both PROPOSED; M2-IG.1 batch 1. IG-specific ADRs (036..039) + KB-16/17 + DD-8 land in batch 2.
- **v0.8 (2026-04-27)** — M2-IG.1 batch 2 IG-specific substrate. ADR-036 (IG wire-level driver: roll-our-own httpx + asyncio Lightstreamer; rejects `trading_ig` for asyncio mismatch with ADR-005), ADR-037 (`Instrument.tradability` field — backward-compatible spot/cfd/spread_bet discriminator; scopes ADR-027 integer-share rounding to spot only), ADR-038 (IG rate-limit defaults — parameterises ADR-031 with named-bucket config; IG defaults 30/60/40 per minute + 40 concurrent Lightstreamer subscriptions; broker-agnostic shape), ADR-039 (Phase 1 strategy under IG bridge — CAC 40 CFD as tradable instrument; ADR-021 PAUSED not SUPERSEDED; new parity envelope: directional alignment + characterised < 100 bps over 5-day run, *not* G2-IB ±1 bps). All four PROPOSED; awaiting operator review alongside ADR-034..035 to flip ACCEPTED en bloc.
- **v0.9 (2026-04-27)** — operator approval moment. Eight ADRs flipped PROPOSED → ACCEPTED en bloc: ADR-030 (per-archetype dispatch — broker-agnostic; resolves OQ-030), ADR-033 (AccountUpdate cadence — broker-agnostic), ADR-034 (multi-broker registry; load-bearing), ADR-035 (secrets handling discipline), ADR-036 (IG driver), ADR-037 (Instrument.tradability), ADR-038 (IG rate-limit defaults), ADR-039 (Phase 1 under IG bridge). **Two ADRs stay PROPOSED**: ADR-031 (IB-specific rate-limit defaults; revisit when M2-IB resumes) and ADR-032 (IB-specific instrument resolution; revisit when M2-IB resumes). Updated OQ-030 status RESOLVED-BY-ADR-030 in OPEN_QUESTIONS.md.
- **v0.10 (2026-04-28)** — M2-IB.2 milestone flip. ADR-031 (token-bucket rate limiter shape for IB adapters) PROPOSED → ACCEPTED: the algorithm shipped at M2-IG.2 inside `blive.adapters.shared.rate_limiter` and the IB-specific defaults table now lives at `blive.adapters.ib.rate_limiter.IB_DEFAULT_RATE_LIMITS` (`global` 20/s, `historical` 50/600s per [KB-3 §9](../kb/ib_pacing_spec.md#9-summary-adapter-budget-defaults)). `IBClient.connect()` exercises the limiter via `acquire("global")` per the M2-IB.2 unit-test suite. Body of ADR-031 unchanged (append-only); status field flipped + a parenthetical PROPOSED→ACCEPTED date trail added in the ADR header. **ADR-032 stays PROPOSED** until M2-IB.3 IBInstrumentResolver exercises `qualifyContractsAsync` against IB Paper.
- **v0.11 (2026-04-28)** — M2-IB.3 prereq closure. Added ADR-040 (Phase 1 deployment target: Windows host with native IB Gateway; no Docker / IBC for paper-mode dev; Linux VM revisited at M8 production cutover). Drafted PROPOSED, accepted same-session per the established same-day-ACCEPTED pattern; status flipped to ACCEPTED. Closes the "Decide deployment target" item from [TASK_REGISTRY M2-IB §"Operator-side prerequisites"](../../TASK_REGISTRY.md). Daily 23:45 ET TWS-restart handled by operator-managed manual relogin during the M2-IB.5 ≥5-trading-day run; blive's reconciliation handles the disconnect/reconnect transient unchanged.
- **v0.12 (2026-05-01)** — M2-IB.3a-resolved milestone flips. ADR-032 (instrument resolution policy `blive.Instrument` ↔ IB `Contract` / `ConID`) PROPOSED → ACCEPTED: `IBInstrumentResolver` exercised against IB Paper Gateway (`scripts/probe_ib_resolve_contract.py` 2026-05-01) and resolved Phase 1 instrument cleanly (`CAC.PA` → `conId=11183823`). Body of ADR-032 unchanged (append-only); status field flipped + PROPOSED→ACCEPTED date trail added in the ADR header. Added ADR-041 (Yahoo-suffix translation in IB instrument resolver) — drafted PROPOSED then ACCEPTED in same commit per established same-day-ACCEPTED pattern; refines ADR-032 with the EODHD/Yahoo `.PA` suffix-stripping rule discovered when the first probe attempt failed with IB error 200 on `CAC.PA`. Yahoo-suffix table seeded for `XPAR/.PA`, `XLON/.L`, `XETR/.DE`, `XAMS/.AS`. The broker-neutral `Instrument` keeps its EODHD-friendly form per ADR-004; only the IB resolver translates. **All ADRs accepted as of v0.12**: ADR-001..041 ACCEPTED. No PROPOSED ADRs remain.
- **v0.13 (2026-05-02)** — methodology-amendment batch. Added ADR-042 (session-bootstrap files: agent-agnostic pattern for L0 warm-up entry point) — drafted PROPOSED then ACCEPTED same-session per established pattern; extends ADR-026 by operationalising the L0 layer with a static manual-baseline implementation (a project-root markdown file the harness auto-loads). First instance lands as [`CLAUDE.md`](../../CLAUDE.md). Companion edits in this batch: [CONTEXT_PROTOCOL §11.2](../../CONTEXT_PROTOCOL.md) extended to identify the bootstrap-file pattern as the manual L0 baseline; [CONTEXT_INVENTORY §1](../../CONTEXT_INVENTORY.md) gains a "0. Bootstrap" row for `CLAUDE.md` and §7 file-layout updated; [`docs/method/Amendments_Log.md`](../method/Amendments_Log.md) Amendment v0.3 records paper-section guidance for the next iteration of `cognitive_cartography.tex`. **All ADRs accepted as of v0.13**: ADR-001..042 ACCEPTED. (Note: ADR-040 + ADR-041 were the most-recent prior IDs; ADR-042 is the next monotonic id.)
- **v0.14 (2026-05-02)** — Phase 1 strategy switch. Added ADR-043 (Phase 1 strategy switch: `triple_lev_sma_filter_dsl` (A3) replaces `tkan_v4_momentum_timing` (A2)) — drafted PROPOSED then ACCEPTED same-session. Phase 1 strategy is now A3 (TQQQ / TMF / IEF, daily rebalance, T+1 open). ADR-021 (CAC ETF proxy) status flipped ACCEPTED → SUPERSEDED-BY-ADR-043; the CAC.PA Instrument + Yahoo-suffix translation per ADR-041 + DD-7 §3 / §3.1 substrate stay durable (CAC.PA is wire-validated end-to-end at `M2-IB.4a-happy-cacpa` and may revive as a future strategy / comparison instrument). NAV slice unchanged at 5–10% per ADR-020. A2 (`tkan_v4_momentum_timing`) — code stays in repo, marked DEFERRED-NO-TARGET in INV-1 / KB-5. Companion ADRs (044 multi-instrument pipeline, 045 LongShortPortfolio dispatch, 046 IB SMART for US equities) follow in the next commit. Substrate updates in this batch: KB-5 §7 phased priority reordered, INV-1 A2/A3 phase columns swapped, TASK_REGISTRY M2-IB.5 closed at architectural surface + M2-IB.6 scope opened with sub-milestones .6.1 / .6.2 / .6-close, CONTEXT_INVENTORY §10 / status banner updated.
- **v0.15 (2026-05-02)** — M2-IB.6-substrate batch 2/2: companion ADRs to ADR-043. Added ADR-044 (multi-instrument pipeline support — `instruments: list[Instrument]` + `target_weights_series: pd.DataFrame`; ships at M2-IB.6.1), ADR-045 (LongShortPortfolio btest dispatch — extends ADR-030's per-archetype pattern; lights up `compute_target_weights_for_date()` for A3 / A1 / A1a), ADR-046 (IB resolver SMART routing for US equities — codifies the probe-local `_SmartUsResolver` workaround into the production `IBInstrumentResolver`; XNAS / XNYS / ARCX / BATS spot equities now route via `exchange="SMART"` + `primaryExchange` hint; refines ADR-032). All three drafted PROPOSED then ACCEPTED same-session. DD-7 §3 amended in same commit (US ETF venues gain a `primaryExchange` column; SMART convention documented). M2-IB.6-substrate complete; .6.1 (code) opens next.
- **v0.16 (2026-05-03)** — PRIIPs-compliant universe for Phase 1. Added ADR-047 (PRIIPs-compliant universe for Phase 1 A3 strategy — refines ADR-043). The 2026-05-03 M2-IB.6.1 architectural-surface wire run surfaced IB error 201 with PRIIPs-KID reason on every order against the US-domiciled TQQQ / TMF / IEF tickers — UK retail accounts cannot trade products without UK-filed Key Information Documents. ADR-047 substitutes UK-listed PRIIPs-compliant analogues: QQL3 (LSE, 3× Nasdaq 100 ETP), IBTL (LSE, iShares $ Treasury Bond 20+yr UCITS — **1× not 3×**, no UK-listed 3× US-Treasury exists), IBTM (LSE, iShares $ Treasury Bond 7-10yr UCITS). Trend signals (QQQ / TLT) unchanged — signal-only, not traded. Strategy regime shifts from 3×/3× to 3×/1× across the legs; backtest numbers don't carry forward exactly. Pipeline / FSM / SMART routing all validated correctly in the wire run; the blocker is regulatory, not technical. Companion edits in same commit batch: INV-14 (error 201 PRIIPs-KID variant catalogued alongside the precaution-cascade variant), KB-9 (new §"PRIIPs / KID restrictions" section), DD-7 §3 (XLON row "Used by" annotation updated for Phase 1 use), INV-1 (Phase 1 row universe column updated), refresh_eodhd_signals.py + run_m2ib6_ib_paper.py code updates for the new tickers.
- **v0.19 (2026-05-06 / M2-IB.6 close)** — Two ADRs flipped PROPOSED → ACCEPTED in the M2-IB.6 close batch: ADR-048 (LSE-ETF SMART routing discriminator — refines ADR-046; held PROPOSED since 2026-05-03 awaiting LSE-RTH fill validation) and ADR-049 (`OrderType.ADAPTIVE_MKT` + empirical PMA-cap finding — refines ADR-027, companion to ADR-046/048). Both bodies unchanged (append-only); status fields and PROPOSED→ACCEPTED date trails added in the ADR headers. Companion edits in same close commit batch: DD-7 §3 amended (XLON row split into XLON+EQUITY → direct LSE and XLON+ETF → SMART/primaryExchange=LSEETF, mirroring ADR-046's US-SMART pattern shape); CONTEXT_INVENTORY M2-IB.6 row ✓ marked complete with M2-IB.6.2c sub-milestone ledger; TASK_REGISTRY M2-IB.6 milestone closed with the actual sub-milestone path (M2-IB.6-substrate / .6.1 / .6.2a-PRIIPs-probe / .6.2b-LSE-RTH / .6.2c-PMA-cap-investigation / .6-close); RETRO-M2-IB written + frozen; NEXT_PROMPT.md replaced v0.7 → v0.8 targeting Phase 2 readiness audit per [CONTEXT_PROTOCOL §8.3.2](../../CONTEXT_PROTOCOL.md). All ADRs accepted as of v0.19: ADR-001..049 ACCEPTED. The M2-IB.6.2c PMA-cap investigation (4-run wire matrix; ADAPTIVE_MKT does not bypass the cap on UK retail accounts) is captured in [INV-14 v0.7](../inv/ib_error_codes.md) and [OQ-031](OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account); operator decided at close to address OQ-031 in M3 rather than block M2-IB.6 on it.
- **v0.18 (2026-05-06)** — Added ADR-049 (`OrderType.ADAPTIVE_MKT` for IBALGO Adaptive routing + empirical PMA-cap finding — refines ADR-027, companion to ADR-046 / ADR-048) **PROPOSED**. The M2-IB.6.2b/c LSE-RTH validation runs on 2026-05-06 surfaced IB warning **2161** (Price Management Algo / regulatory disruptive-orders cap) on QQL3 (3× Nasdaq leveraged ETP on LSEETF), preventing fills despite the order reaching ACCEPTED state — IB caps the effective limit price to the live bid/ask reference, and BUY orders capped at the bid don't fill in rising markets. ADR-049 adds `OrderType.ADAPTIVE_MKT` (IB IBALGO Adaptive variant of MKT) per IB's recommended workaround in the warning text — wire-validated as correctly-routed (algoStrategy='Adaptive' + algoParams set on the ib_async order; FSM trace differs) — but **empirically confirmed across four progressive wire runs that the 2161 cap binds structurally on UK retail accounts regardless of order type**: raw MKT (10s + 60s waits), ADAPTIVE_MKT, and LMT @ $50 (well above IB's ~$39 reference) all see `mktCapPrice` set and zero fills on QQL3. The `priceManagementOff` order flag (institutional-only opt-out) is unavailable to retail. Bypass requires either MiFID II Professional Client classification (declined per ADR-047 alt #2) or non-leveraged-product substitution. Documented as INV-14 v0.7 (catalogued + validation-matrix); raises OQ-031 ("Phase 1 deployment under PMA-bound retail") for pre-cutover resolution. `OrderType.ADAPTIVE_MKT` infrastructure stays — useful tooling for non-cap-bound venues / future strategies — captured in `src/blive/domain/types.py`, `src/blive/adapters/ib/broker.py`, `src/blive/runtime/ib_pipeline.py` (per-symbol order_type override), `scripts/run_m2ib6_ib_paper.py` (QQL3 → ADAPTIVE_MKT mapping), `tests/unit/adapters/ib/test_broker.py` (test_submit_adaptive_mkt_order_routes_via_ibalgo). Side-finding (not promoted into a separate ADR; flagged as M7 parity concern): EODHD reports QQL3 close ~$383 while IB reference is ~$39 — a 10× discrepancy, likely a recent reverse-split or EODHD unit-of-quote convention; the strategy's sizing/limit-pricing uses EODHD's price → 10× too high → IB rejects with error 110 (price out of allowed range) before 2161 even fires when LMTs are computed from EODHD close × multiplier.
- **v0.17 (2026-05-03)** — Added ADR-048 (LSE-ETF SMART routing discriminator — refines ADR-046) **PROPOSED**. The M2-IB.6.2 wire run with the ADR-047 universe returned IB error 200 on every order: bare `XLON → "LSE"` direct routing does not expose UCITS / ETP listings (the LSE main book and LSE ETF book are distinct IB venues — LSEETF). Direct probe via `reqContractDetails` confirmed all three Phase 1 tradables resolve cleanly via `Contract(exchange="SMART", primaryExchange="LSEETF")`. ADR-048 codifies the discriminator: `XLON + ETF → SMART/LSEETF`, `XLON + EQUITY → LSE` (direct, unchanged). Mirrors the ADR-046 US-equity SMART pattern shape. Status PROPOSED until the LSE RTH wake-up on Tue 2026-05-05 produces actual fills (M2-IB.6.2 smoke reached PreSubmitted / cancelled at engine timeout — LSE was closed Sun + UK May Day Bank Holiday Mon). Code change already landed in `c34267d`; substrate ADR-048 + DD-7 §3 follow-up land in this commit. **Side-finding documented inline (out of ADR-048 scope):** IBTL/IBTM on LSEETF resolve to GBP-hedged accumulating share classes (IB doesn't expose USD distributing classes for these symbols); QQL3 trades USD-denominated. Phase 1 P&L is mixed-currency (USD on QQL3, GBP-hedged on IBTL/IBTM). Documented in `scripts/run_m2ib6_ib_paper.py`; pivot to `IDTL` / `IDTM` USD distributing share classes (Path B) is a separate Phase 1 universe revision, not a routing-discriminator change.
- **v0.20 (2026-05-06 / M3.1 entry)** — Added ADR-050 (EODHD-vs-IB unit-of-quote conversion at sizing time — Hybrid B-now / A-later free-MD-only) **PROPOSED**. Operationalises the M3.1 narrow-scope sizing fix per [TASK_REGISTRY M3.1](../../TASK_REGISTRY.md): Route B (per-instrument convention catalogue at `src/blive/adapters/eodhd/conventions.py`) ships now; Route A (live-IB-MD reference for sizing) reserved for M7 but **bounded to free IB market-data tiers only** (operator-stated cost discipline; LSEETF and other paid subscriptions out of scope indefinitely). The 2026-05-06 EODHD-side investigation (`scripts/probe_qql3_unit_of_quote.py`) refuted the `adjusted_close` and currency-convention hypotheses; the operative cause is a recent reverse-split that EODHD has not yet propagated. Catalogue v0.1 entry for QQL3: `MANUAL_SCALE(divisor=10.0, source="IB live reference, M2-IB.6.2c")`. Companion edits in same M3.1 commit batch: RC-10 (price sanity, ±50% threshold) implemented in `blive.risk` per [INV-4 v0.2](../inv/risk_checks.md); KB-15 (`parity_methodology`) MISSING → DRAFT v0.1 (unit-of-quote / reverse-split section only); INV-14 grows the error 110 row promotion; DD-7 footnote on the QQL3 reverse-split convention; pipeline `_price_lookup` closure routes through the conventions catalogue. Status PROPOSED until the M3.1 wire-validation run produces a QQL3 sized within ±1% of the IB-USD-equivalent target exposure with no IB error 110; flips to ACCEPTED in the wire-validation commit per the established same-day-ACCEPTED pattern.
- **v0.21 (2026-06-05 / M3.1b)** — Added ADR-051 (Normalize IB order prices to the contract tick grid at submit time) **PROPOSED**. The 2026-06-05 M3.1 wire-validation run (`--order-type LMT --max-bars 5`, LSE RTH) confirmed ADR-050's unit-of-quote fix (QQL3 sized 65 sh @ ~$39 vs the pre-fix 6 sh @ ~$381) but surfaced a *second, independent* cause of IB error 110: tick-size non-conformance (QQL3's LSEETF minimum price variation is 0.10; blive's pipeline hardcoded `quantize(0.01)`, so 38.52 / 42.83 / 44.15 were rejected while 39.60 / 41.50 passed). ADR-051 moves price-grid conformance to the broker's `submit()` chokepoint: a pure `snap_price` (`blive.adapters.shared.price_grid`) + an IB increment-table source/cache (`blive.adapters.ib.price_rules` — market rule with `minTick` fallback, per-`Instrument` cache + `clear_cache`); the pipeline's `quantize(0.01)` is removed. Magnitude (ADR-050) stays at sizing time, grid (ADR-051) at submit time — distinct layers by design. Because ADR-050's flip criterion also requires "no error 110", ADR-050 + ADR-051 now flip PROPOSED → ACCEPTED **jointly** on the first clean LMT wire run. Companion edits in this batch: INV-14 error 110 row (two sub-causes), DD-7 (per-contract tick / market-rule metadata), TASK_REGISTRY M3.1 → M3.1b, CONTEXT_INVENTORY banner. Size/lot conformance noted as the same-seam forward-extension (not built). All ADRs ACCEPTED as of v0.21 **except** ADR-050 + ADR-051 (PROPOSED; joint wire-flip pending) and ADR-021 (SUPERSEDED-BY-ADR-043).
- **v0.22 (2026-06-05 / M3.1b wire-validation)** — ADR-050 + ADR-051 flipped PROPOSED → ACCEPTED **jointly** on the clean LSE-RTH wire run (`run_m2ib6_ib_paper.py --order-type LMT --max-bars 5`, 2026-06-05 11:38 BST). QQL3 limits snapped to its 0.10 LSEETF tick grid on the *live* wire (`38.519640 → 38.5`, `39.600015 → 39.6`, `41.500470 → 41.5`, `42.830085 → 42.8`, `44.152665 → 44.2`) and placed with **zero IB error 110** (6 submitted, 0 rejected; IBTM filled). QQL3 reaches ACCEPTED → CANCELED cleanly — the residual no-fill is the structural 2161 PMA-cap / resting-LMT behaviour tracked in [OQ-031](OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account) (M3.2/M3.3), not a tick or magnitude issue. Both ADR bodies unchanged (append-only); status fields + index rows flipped with the date trail. **All ADRs ACCEPTED as of v0.22 except ADR-021 (SUPERSEDED-BY-ADR-043).**
- **v0.23 (2026-06-05 / M3.3 OQ-031 resolution)** — Added **ADR-052** (Phase 1 accepts the PMA-bound leveraged-leg non-fill — OQ-031 Option 1) ACCEPTED (drafted PROPOSED then ACCEPTED same-session on operator confirm). Resolves [OQ-031](OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account) on the M3.2 empirical capture (QQL3 0/69 fills = 0% vs IBTM 6/6 = 100%; 2161 cap-binding 0; zero rejects / breaches / error-110 across two flip-spanning LSE-RTH runs): Phase 1 deploys A3 accepting the 3× leveraged equity leg ≈ never fills (live behaviour Treasury-leg-dominated), **no code change**; the leveraged-leg redesign is deferred to Phase 2 as [OQ-032](OPEN_QUESTIONS.md#oq-032--phase-2-a3-leveraged-leg-redesign-how-or-whether-to-restore-leveraged-equity-exposure). OQ-032 carries the *full* design space — including the **leverage-preserving** margin-on-a-1×-UCITS path (≈3× via 3:1 margin on a low-volatility 1× Nasdaq-100 UCITS that likely dodges the volatility-triggered PMA cap, per [ADR-016](#adr-016--leverage-support-both-margin-financed-and-leveraged-etf-instruments)) that the four OQ-031 options had omitted — the honest scope is a *trilemma* (PRIIPs blocks US leveraged ETPs, PMA blocks UK ones, Cash blocks margin-leverage). Companion edits (append-only / frontmatter-only): OQ-031 status OPEN → RESOLVED-BY-ADR-052; OQ-032 raised; `refined-by: ADR-052` backref added to ADR-043 + ADR-047 frontmatter (the QQL3 leg is now provisional — a new backref convention, the discoverability mirror of the supersede-chain); TASK_REGISTRY M3.3 resolved + G4 exit-criterion #1 satisfied; CONTEXT_INVENTORY §10 + banner. No code / INV-14 / INV-4 change (Option 1 = no code change); tests unchanged at 590. **All ADRs ACCEPTED as of v0.23 except ADR-021 (SUPERSEDED-BY-ADR-043).**
- **v0.24 (2026-06-05 / Python 3.12 upgrade)** — Added **ADR-053** (Upgrade to Python 3.12) ACCEPTED. Standalone tooling change (not a milestone deliverable): blive + btest move from "Python 3.11.x exactly" to **3.12** (`requires-python >=3.11`, `mypy python_version 3.12`, `black target py312`), motivated by Phase 2's VIX-term-structure strategy (the `r_lev_001` notebook / OQ-032) which needs 3.12. A non-destructive dry-run validated the full dep tree on 3.12 (numba 0.65.1 / vectorbt 1.0.0 / arcticdb 6.18.0 all have 3.12 wheels; blive 591 + btest 317 tests pass). Companion changes: `pandas` pinned `<3` (avoid the breaking 3.0 major); mypy bumped to 2.x pinned `==2.1.0` (the one new finding — `float(Series)` in `ib_pipeline.py` — fixed with a `cast`); btest's unused/broken `signum` optional dep removed (commits `fd106f9` + `32dab28`). `.venv` recreated on 3.12.12; `uv.lock` re-locked; all gates green. **All ADRs ACCEPTED as of v0.24 except ADR-021 (SUPERSEDED-BY-ADR-043).**
