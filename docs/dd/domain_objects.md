---
id: DD-1
title: Domain Objects Data Dictionary
status: STABLE
owner: Claude
last_reviewed: 2026-06-05
version: 0.3
sources:
  - REQUIREMENTS.md §5.3 (Order shape, FSM)
  - REQUIREMENTS.md §5.4 (Position, AccountSnapshot)
  - REQUIREMENTS.md §7.3 (Bar, Trade, Fill, OrderEvent)
depends_on:
  - REQUIREMENTS
  - KB-12 GLOSSARY
referenced_by:
  - INV-13 order_state_transitions (consumes OrderState, OrderEventKind)
  - INV-5 domain_events (extends OrderEvent with non-order events)
  - INV-6 ports_adapters (Port signatures use these types)
  - src/blive/domain/types.py (implementation)
---

# DD-1 — Domain Objects Data Dictionary

## Purpose

The single source of truth (SSOT) for the **broker-neutral domain types** used
across `blive`. Every dataclass listed here has exactly one home in
`src/blive/domain/types.py` (or a sibling module under `blive.domain.*`); every
adapter, port, test, and event-log row references these definitions.

A change to any field below is a multi-artefact edit per
[CONTEXT_PROTOCOL §3.1](../../CONTEXT_PROTOCOL.md): walk `referenced_by`, plan
the propagation in one commit.

## Scope

**In:** the eight value types listed in §1; their shared enums (`OrderSide`,
`OrderType`, `TimeInForce`, `OrderState`, `OrderEventKind`, `AssetClass`); the `Tradability` literal alias ([ADR-037](../decisions/DECISIONS.md#adr-037--instrumenttradability-field-spot--cfd--spread_bet)).

**Out:** event payloads beyond `OrderEvent` (covered by INV-5);
broker-specific identifiers like IB `ConID` (covered by DD-7
`instrument_dictionary`, MISSING — added when the IB adapter lands at M2);
SQLite DDL for persisted rows (DD-4, MISSING — added at M4); REST payloads
(DD-5, MISSING — added at M6).

## Conventions

- All dataclasses are `@dataclass(frozen=True, slots=True)`. Mutability is
  modelled through event streams, not field reassignment, per the crash-only
  design ([ADR-009](../decisions/DECISIONS.md#adr-009--crash-only-design)).
- All monetary quantities are `decimal.Decimal`, never `float`. Rationale:
  share counts can be fractional (IB cash account fractional shares); prices
  carry tick precision; `float` rounding silently corrupts P&L.
- All timestamps are `datetime` in **UTC** (`tzinfo=timezone.utc`). UI display
  conversion happens at the edge per [REQUIREMENTS §5.11](../../REQUIREMENTS.md).
- All IDs that originate inside `blive` use `uuid.UUID` (specifically `uuid4`
  for non-monotonic uniqueness; the IB adapter owns the venue-side
  monotonic-`orderId` separately per [KB-3 §4](../kb/ib_pacing_spec.md#4-order-id--multi-client)).
- All enum members are uppercase string-valued so they round-trip as JSON.

---

## 1. Type catalogue

### 1.1 Enums

| Enum | Members | Notes |
|------|---------|-------|
| `OrderSide` | `BUY`, `SELL` | No `SHORT`/`COVER`; long/short is a *position* concept (see [REQUIREMENTS §5.4](../../REQUIREMENTS.md)), not an order concept. |
| `OrderType` | `MKT`, `LMT`, `MOC`, `LOC`, `STP`, `STP_LMT` | Lifted verbatim from [REQUIREMENTS §5.3](../../REQUIREMENTS.md). Extension at INV-2 (MISSING; landed at M3). |
| `TimeInForce` | `DAY`, `GTC`, `IOC`, `FOK`, `OPG` | Lifted from REQUIREMENTS §5.3. Extension at INV-3 (MISSING; M3). |
| `OrderState` | `INITIALIZED`, `SUBMIT_PENDING`, `SUBMITTED`, `ACCEPTED`, `PARTIALLY_FILLED`, `FILLED`, `CANCELED`, `REJECTED`, `EXPIRED` | The FSM states ([INV-13](../inv/order_state_transitions.md)). |
| `OrderEventKind` | `SUBMITTED`, `ACCEPTED`, `PARTIAL_FILL`, `FILLED`, `CANCELED`, `REJECTED`, `EXPIRED` | The seven event kinds emitted by FSM transitions. Names match REQUIREMENTS §7.3 verbatim. Note `PARTIAL_FILL` (event) vs `PARTIALLY_FILLED` (state). |
| `AssetClass` | `EQUITY`, `ETF`, `INDEX`, `FX`, `FUTURE`, `OPTION` | v1 trades `EQUITY`/`ETF` only ([ADR-013](../decisions/DECISIONS.md#adr-013--v1-scope-etf-and-index-strategies-only)); other members declared so the type exists at the signature surface but throw at the adapter layer when unsupported. |

### 1.2 Value types

| Type | Lifecycle | Description |
|------|-----------|-------------|
| [`Instrument`](#21-instrument) | immutable per identity | broker-neutral identity of a tradable thing |
| [`Bar`](#22-bar) | append-only | OHLCV record over a time interval |
| [`Trade`](#23-trade) | append-only | a single executed transaction in the market (tick) |
| [`Order`](#24-order) | immutable request | the *intent* to submit; lifecycle lives in the event stream |
| [`Fill`](#25-fill) | append-only | a single execution against an order |
| [`OrderEvent`](#26-orderevent) | append-only | every FSM transition for an order |
| [`Position`](#27-position) | snapshot | current holding of one instrument by one strategy |
| [`AccountSnapshot`](#28-accountsnapshot) | snapshot, sampled | account-level financials at a point in time |
| [`OrderUpdate`](#29-orderupdate) | immutable request | new fields for a cancel-replace |
| [`ConnectionStatus`](#210-connectionstatus) | append-only | broker connection state change |
| [`BrokerEvent`](#211-brokerevent) | union | what `BrokerPort.events()` yields |

---

## 2. Field-level definitions

### 2.1 `Instrument`

Broker-neutral identity. Adapter-side resolution to broker-native form is governed by [DD-7 (IB)](./instrument_dictionary.md) and [DD-8 (IG)](./ig_instrument_dictionary.md).

| Field | Type | Semantics | Invariant |
|-------|------|-----------|-----------|
| `symbol` | `str` | broker-neutral ticker, e.g. `"CAC.PA"`, `"AAPL"`, `"TQQQ"`, `"CAC40"` | non-empty; ASCII; no whitespace |
| `venue` | `str` | exchange / MIC code, e.g. `"XPAR"`, `"XNAS"`, `"ARCA"` | non-empty; uppercase ISO 10383 MIC where one exists |
| `currency` | `str` | trading currency, ISO 4217, e.g. `"EUR"`, `"USD"` | exactly 3 uppercase letters |
| `asset_class` | `AssetClass` | enum classifier | one of the enum members |
| `multiplier` | `Decimal` | contract multiplier (1 for cash equities/ETFs; 100 for US options; etc.) | strictly positive |
| `tradability` | `Tradability` | how the instrument is held: `"spot"` (cash equity / ETF / direct), `"cfd"` (Contract for Difference), `"spread_bet"` (UK spread bet). Defaults to `"spot"` for backward compatibility. Per [ADR-037](../decisions/DECISIONS.md#adr-037--instrumenttradability-field-spot--cfd--spread_bet). | one of the literal members |

**Equality / hashing.** Identity is the tuple `(symbol, venue, currency, asset_class, tradability)`; `multiplier` is informational. Per [ADR-037](../decisions/DECISIONS.md#adr-037--instrumenttradability-field-spot--cfd--spread_bet) `tradability` widens the identity — `CAC.PA` ETF (spot) and `IX.D.CAC40.CASH.IP` CFD are distinct `Instrument`s even when symbol/venue/currency/asset_class match. The dataclass is frozen so equality is field-wise — callers should not rely on multi-symbol aliases (e.g. corp-action renames) being equal.

**Sample (spot — Phase 1 IB path, [ADR-021](../decisions/DECISIONS.md#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf)).**

```python
Instrument(
    symbol="CAC.PA",
    venue="XPAR",
    currency="EUR",
    asset_class=AssetClass.ETF,
    multiplier=Decimal("1"),
    # tradability="spot" (default; explicit when documenting)
)
```

**Sample (CFD — Phase 1 IG bridge path, [ADR-039](../decisions/DECISIONS.md#adr-039--phase-1-strategy-under-ig-bridge-cac-40-cfd)).**

```python
Instrument(
    symbol="CAC40",
    venue="XPAR",
    currency="EUR",
    asset_class=AssetClass.INDEX,
    multiplier=Decimal("1"),
    tradability="cfd",
)
```

**Sizer interaction.** [ADR-027](../decisions/DECISIONS.md#adr-027--sizer-rounding-policy-integer-shares-truncate-toward-zero) integer-share rounding scopes to `tradability == "spot"`. CFDs and spread bets use per-instrument fractional precision sourced from the broker resolver (`IGInstrumentResolver.precision_for(instrument)` per [DD-8 §5](./ig_instrument_dictionary.md#5-per-instrument-precision)).

**Lineage.** Constructed by the strategy ingest layer from the btest
`Universe` (see [KB-1 §3](../kb/btest_dsl_inventory.md#3-universe)) or by the
strategy YAML directly. Adapters never mint an `Instrument` — they only
*resolve* one to their native form.

---

### 2.2 `Bar`

OHLCV bar over a closed interval. Lifted from [REQUIREMENTS §7.3](../../REQUIREMENTS.md).

| Field | Type | Semantics | Invariant |
|-------|------|-----------|-----------|
| `instrument` | `Instrument` | the instrument the bar describes | — |
| `open_time_utc` | `datetime` | start of the bar window, UTC, inclusive | `tzinfo == timezone.utc`; ≤ `close_time_utc` |
| `close_time_utc` | `datetime` | end of the bar window, UTC, exclusive | `tzinfo == timezone.utc`; > `open_time_utc` |
| `open` | `Decimal` | first trade price in window | strictly positive |
| `high` | `Decimal` | highest trade price in window | ≥ `low` and ≥ `open` and ≥ `close` |
| `low` | `Decimal` | lowest trade price in window | ≤ `open` and ≤ `close` and ≤ `high` |
| `close` | `Decimal` | last trade price in window | strictly positive |
| `volume` | `Decimal` | total traded volume in window | ≥ 0 |
| `vwap` | `Decimal \| None` | volume-weighted average price | when present, `low ≤ vwap ≤ high` |

**Sample.** A 1-minute bar on CAC.PA at 2026-04-26 14:30 UTC, closing at €78.42 on 12,000 shares — see `tests/conftest.py` fixtures.

**Lineage.** `MarketDataPort.subscribe_bars()` (live) or
`MarketDataPort.historical_bars()` (warm-up) per [INV-6](../inv/ports_adapters.md). The PaperBroker may also synthesise bars from a deterministic fixture for paper-mode replay.

---

### 2.3 `Trade`

A single market trade tick — independent of any order **we** placed.

| Field | Type | Semantics | Invariant |
|-------|------|-----------|-----------|
| `instrument` | `Instrument` | — | — |
| `time_utc` | `datetime` | tick timestamp | `tzinfo == timezone.utc` |
| `price` | `Decimal` | trade price | strictly positive |
| `quantity` | `Decimal` | trade size | strictly positive |
| `aggressor` | `Literal["BUY", "SELL", "UNKNOWN"]` | which side initiated | always one of the three |

**Distinct from `Fill`.** `Trade` describes any market activity; `Fill`
describes execution of *our* order.

**Lineage.** `MarketDataPort.subscribe_trades()`.

---

### 2.4 `Order`

Immutable request submitted by the engine. The order's lifecycle (state
transitions) lives in the `OrderEvent` stream; the `Order` itself never
mutates after creation.

| Field | Type | Semantics | Invariant |
|-------|------|-----------|-----------|
| `client_order_id` | `UUID` | blive-generated; owned through full lifecycle | unique within the engine instance |
| `strategy_id` | `str` | originating strategy id | non-empty; per-strategy attribution per [REQUIREMENTS §5.4](../../REQUIREMENTS.md) |
| `instrument` | `Instrument` | what to trade | — |
| `side` | `OrderSide` | `BUY` or `SELL` | — |
| `quantity` | `Decimal` | size in instrument units | strictly positive |
| `order_type` | `OrderType` | `MKT \| LMT \| MOC \| LOC \| STP \| STP_LMT` | — |
| `time_in_force` | `TimeInForce` | `DAY \| GTC \| IOC \| FOK \| OPG` | — |
| `limit_price` | `Decimal \| None` | LMT / STP_LMT price | required iff `order_type ∈ {LMT, STP_LMT}`; None otherwise |
| `stop_price` | `Decimal \| None` | STP / STP_LMT trigger | required iff `order_type ∈ {STP, STP_LMT}`; None otherwise |
| `parent_id` | `UUID \| None` | parent order for OCA / brackets | None for v1 (no OCA in scope yet) |
| `tags` | `Mapping[str, str]` | routing hints, algo params, audit context | keys non-empty; serialisable as JSON |
| `created_at` | `datetime` | when the engine constructed the request | `tzinfo == timezone.utc` |

**Idempotency.** Re-submitting the same `client_order_id` is a no-op that
returns the existing order's current state ([REQUIREMENTS §5.3](../../REQUIREMENTS.md)).

**Sample.**

```python
Order(
    client_order_id=UUID("3f4f7a4e-9f88-4e3e-8a39-7f6e1f6b1c53"),
    strategy_id="tkan_v4_momentum_timing_1x",
    instrument=Instrument(symbol="CAC.PA", venue="XPAR", currency="EUR",
                          asset_class=AssetClass.ETF, multiplier=Decimal("1")),
    side=OrderSide.BUY,
    quantity=Decimal("10"),
    order_type=OrderType.MKT,
    time_in_force=TimeInForce.DAY,
    limit_price=None,
    stop_price=None,
    parent_id=None,
    tags={"rebalance_id": "2026-04-26-EOD"},
    created_at=datetime(2026, 4, 26, 13, 30, tzinfo=timezone.utc),
)
```

**Lineage.** Constructed by the Sizer (M1) from `target_weights` per
[REQUIREMENTS §5.13](../../REQUIREMENTS.md); for M0 round-trip tests, by the
test directly.

---

### 2.5 `Fill`

A single execution against one of our orders. Lifted from REQUIREMENTS §7.3.

| Field | Type | Semantics | Invariant |
|-------|------|-----------|-----------|
| `client_order_id` | `UUID` | parent order id | must reference a known order |
| `venue_order_id` | `str` | venue-assigned id (IB `permId` for example) | non-empty when set by venue; "" allowed for paper-broker pre-venue records |
| `venue_exec_id` | `str` | venue-assigned execution id (idempotency key) | non-empty; the dedup key for replayed fills |
| `instrument` | `Instrument` | what was filled | matches the order's instrument |
| `side` | `OrderSide` | `BUY` or `SELL` | matches the order's side |
| `quantity` | `Decimal` | filled quantity | strictly positive; cumulative ≤ order's `quantity` |
| `price` | `Decimal` | execution price | strictly positive |
| `commission` | `Decimal` | venue commission for this execution | ≥ 0; in `currency` |
| `currency` | `str` | currency of `price` and `commission` (ISO 4217) | exactly 3 uppercase letters |
| `time_utc` | `datetime` | execution timestamp at the venue | `tzinfo == timezone.utc` |

**Idempotency.** `venue_exec_id` is the dedup key. Receiving the same
`venue_exec_id` twice is a no-op.

**Lineage.** `BrokerPort.events()` stream, derived by the adapter from
`execDetails` + `commissionReport` callbacks (IB) or by the in-process
matcher (paper).

---

### 2.6 `OrderEvent`

Append-only record of one FSM transition. Lifted from REQUIREMENTS §7.3 and
extended with an optional `Fill` payload for `PARTIAL_FILL` / `FILLED`.

| Field | Type | Semantics | Invariant |
|-------|------|-----------|-----------|
| `client_order_id` | `UUID` | the order this event belongs to | must reference a known order |
| `venue_order_id` | `str \| None` | venue id when known | None until `ACCEPTED` |
| `kind` | `OrderEventKind` | which transition fired | one of the enum members |
| `reason` | `str \| None` | venue or engine explanation (e.g. reject reason) | None except for `REJECTED`, `CANCELED`, `EXPIRED` where it should be populated |
| `time_utc` | `datetime` | when the event was observed | `tzinfo == timezone.utc` |
| `fill` | `Fill \| None` | the execution payload | non-None iff `kind ∈ {PARTIAL_FILL, FILLED}` |

**Why `fill` lives on `OrderEvent`.** A partial-fill event in REQUIREMENTS
§5.3 implies a `Fill` happened. Putting `Fill` on the event keeps the audit
chain in one record and avoids dangling references in the persistence layer.
A `FILLED` event with `fill=None` is allowed only when the order completed
via cumulative prior partial fills (degenerate — flagged by an invariant
test).

**Lineage.** Emitted by the FSM transition function in
`blive.domain.order_fsm` whenever the `BrokerPort` reports a state change.

---

### 2.7 `Position`

Current holding of one instrument by one strategy.

| Field | Type | Semantics | Invariant |
|-------|------|-----------|-----------|
| `instrument` | `Instrument` | what is held | — |
| `strategy_id` | `str` | which strategy owns this slice (per-strategy attribution) | non-empty |
| `quantity` | `Decimal` | net signed quantity (negative = short) | any |
| `avg_cost` | `Decimal` | average cost per unit, in `instrument.currency` | strictly positive when `quantity != 0`; undefined (Decimal("0")) when `quantity == 0` |
| `currency` | `str` | currency of `avg_cost` (ISO 4217) | matches `instrument.currency` |
| `opened_at` | `datetime \| None` | when the position became non-zero | None when `quantity == 0`; UTC otherwise |
| `updated_at` | `datetime` | last update | UTC |

**Lineage.** Updated by the engine on `Fill` (per
[REQUIREMENTS §5.4](../../REQUIREMENTS.md)) or by reconciliation when the
venue snapshot disagrees (M5).

---

### 2.8 `AccountSnapshot`

Account-level financials at a point in time. Lifted from REQUIREMENTS §5.4.

| Field | Type | Semantics | Invariant |
|-------|------|-----------|-----------|
| `equity` | `Decimal` | total NAV in `base_currency` | any |
| `cash_by_ccy` | `Mapping[str, Decimal]` | cash balance per currency | keys are 3-letter ISO 4217 codes |
| `buying_power` | `Decimal` | available to deploy | ≥ 0 |
| `gross_exposure` | `Decimal` | `Σ |position notional|` in `base_currency` | ≥ 0 |
| `net_exposure` | `Decimal` | `Σ position notional` in `base_currency` (signed) | any |
| `leverage` | `Decimal` | `gross_exposure / equity` | ≥ 0 when `equity > 0` |
| `margin_used` | `Decimal` | broker-reported margin consumption | ≥ 0 |
| `base_currency` | `str` | account base currency (ISO 4217) | exactly 3 uppercase letters |
| `taken_at` | `datetime` | snapshot time | UTC |

**Lineage.** Sampled every 30 s by the engine from
`BrokerPort.account_snapshot()`; persisted per
[REQUIREMENTS §6.5](../../REQUIREMENTS.md) retention.

**Mixed-currency note (M3.4, 2026-06-05).** In a multi-currency account IB
reports `NetLiquidationByCurrency` for *each* currency sleeve **and** a `BASE`
aggregate; `equity` is the **`BASE` aggregate** (the whole-account total in
`base_currency`), never a single-currency sleeve. The IB adapter reads the
`BASE` row primary, falling back to the base-currency sleeve, and infers
`base_currency` from the unit `ExchangeRate` row (not by comparing unconverted
cross-currency magnitudes). Verified live on IB `DUP886336` (GBP base + USD
cash): equity £1,003,855 = GBP sleeve £902,839 + the USD sleeve (~£100k),
*not* the GBP sleeve alone — the bug M3.4 caught and fixed. `cash_by_ccy`
carries the per-currency sleeves (the `BASE` row is excluded).

---

### 2.9 `OrderUpdate`

Cancel-replace payload. Identifies which fields of a live order to change;
all fields are optional (None = "do not change"). Implementation may be
cancel-then-new on venues that don't support atomic replace per
[REQUIREMENTS §5.3](../../REQUIREMENTS.md).

| Field | Type | Semantics | Invariant |
|-------|------|-----------|-----------|
| `quantity` | `Decimal \| None` | new total quantity | strictly positive when set |
| `limit_price` | `Decimal \| None` | new limit price | strictly positive when set |
| `stop_price` | `Decimal \| None` | new stop trigger | strictly positive when set |

At least one field must be non-None — the FSM raises if a no-op replace is
attempted.

**Lineage.** Constructed by the engine; consumed by `BrokerPort.replace()`.
For M0 the type exists but no code path produces one; M3 wires the live
flow.

---

### 2.10 `ConnectionStatus`

Broker connectivity state-change event.

| Field | Type | Semantics | Invariant |
|-------|------|-----------|-----------|
| `connected` | `bool` | True when connected, False on disconnect | — |
| `detail` | `str` | human-readable explanation (`"connected to IB Gateway"`, `"socket EOF"`, …) | non-empty |
| `time_utc` | `datetime` | when the change was observed | UTC |

**Lineage.** Adapter-emitted (e.g. `IBBroker` translates `ib_async`
`connectedEvent` / `disconnectedEvent`). The PaperBroker only emits a
single `connected=True` on construction.

---

### 2.11 `BrokerEvent`

Type alias for the discriminated union of events that
`BrokerPort.events()` yields.

```python
BrokerEvent = OrderEvent | ConnectionStatus
```

The set will widen in later milestones (M2 adds `AccountUpdate` for periodic
broker-pushed account-value changes; M5 may add reconciliation-derived
events).

---

## 3. Cross-References

- [REQUIREMENTS §5.3, §5.4, §7.3](../../REQUIREMENTS.md) — narrative origin.
- [INV-13](../inv/order_state_transitions.md) — uses `OrderState`, `OrderEventKind`.
- [INV-5](../inv/domain_events.md) — extends `OrderEvent` with non-order events.
- [INV-6](../inv/ports_adapters.md) — Port signatures use these types.
- [KB-1 §1](../kb/btest_dsl_inventory.md) — btest `Strategy` (broker-neutral) consumes these in live.
- [ADR-009](../decisions/DECISIONS.md#adr-009--crash-only-design) — frozen-types rationale.
- [KB-12 GLOSSARY](../GLOSSARY.md) — term definitions.

## Open Questions

None blocking M0. Future follow-ups are tracked in
[KB-11 OPEN_QUESTIONS](../decisions/OPEN_QUESTIONS.md).

## Changelog

- **v0.1 (2026-04-26)** — initial STABLE write at M0.
- **v0.2 (2026-04-27)** — M2-IG.2 amendment per [ADR-037](../decisions/DECISIONS.md#adr-037--instrumenttradability-field-spot--cfd--spread_bet). Added `Tradability` literal alias (`spot` / `cfd` / `spread_bet`) and `Instrument.tradability` field with default `"spot"`. Backward-compatible — every existing `Instrument(...)` construction keeps working with default. Identity tuple widens to include `tradability`; CAC.PA ETF (spot) and CAC 40 CFD (cfd) are distinct identities. Sample showing CFD form added. Sizer-interaction note added linking ADR-027 scope. Status stays STABLE — change is purely additive.
