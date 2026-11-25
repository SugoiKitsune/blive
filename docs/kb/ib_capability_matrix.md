---
id: KB-2
title: IB Capability Matrix
status: STABLE
owner: Claude
last_reviewed: 2026-06-05
version: 1.0
sources:
  - https://interactivebrokers.github.io/tws-api/introduction.html       # accessed 2026-04-26
  - https://interactivebrokers.github.io/tws-api/order_submission.html   # accessed 2026-04-26
  - https://interactivebrokers.github.io/tws-api/basic_orders.html       # accessed 2026-04-26
  - https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/    # accessed 2026-04-26
  - https://www.interactivebrokers.com/campus/ibkr-api-page/market-data-subscriptions/  # accessed 2026-04-26
  - https://github.com/ib-api-reloaded/ib_async                          # accessed 2026-04-26
depends_on: []
referenced_by:
  - REQUIREMENTS.md §5.2, §5.3, §10
  - KB-3 ib_pacing_spec (numerical limits)
  - KB-4 frameworks_survey (ib_async row)
  - INV-2 order_types (MISSING — derived from this KB)
  - INV-10 asset_classes
---

# KB-2 — IB Capability Matrix

## Purpose

What Interactive Brokers supports per asset class, order type, TIF, and venue. Companion to [KB-3 IB pacing spec](ib_pacing_spec.md) (numerical limits). Together they are the SSOT for "what IB can do" referenced by REQUIREMENTS, INV-2, INV-10, and the IBBroker adapter design.

## Scope

In scope:
- Asset classes IB exposes via TWS API.
- Order types and TIFs per asset class.
- Market hours / trading session concepts.
- Connectivity surface (TWS, IB Gateway, Web API / CPAPI).
- IB algos (TWAP, VWAP, Adaptive, etc.).
- Subscription tiers as they relate to capability (numerical pricing in KB-3).

Out of scope: pacing limits and quotas (KB-3), ib_async-specific Python wrapping (KB-4 row).

## Conventions

- "✓" = supported on TWS API; "✓*" = supported with caveats (footnoted); "✗" = not supported / not exposed; "—" = not applicable.

---

## 1. Connectivity Surface

| Surface | Protocol | Auth | When to use |
|---------|----------|------|-------------|
| **TWS Desktop** | TCP socket on `127.0.0.1:7497` (paper) / `7496` (live) | local | manual operator + API; daily restart needed |
| **IB Gateway** | TCP socket on `127.0.0.1:4001` (live) / `4002` (paper) | local | headless / Docker; recommended for automation |
| **CPAPI / Web API** | HTTPS REST + WebSocket via local Java gateway | session token via tickle | cloud deploys, but operationally worse for serious execution; see [REQUIREMENTS §9.3](../../REQUIREMENTS.md) |

For blive: **IB Gateway in Docker** ([REQUIREMENTS §12](../../REQUIREMENTS.md)). TWS API only (per [ADR-002](../decisions/DECISIONS.md#adr-002--adopt-ib_async-v21-as-wire-level-ib-driver)). CPAPI rejected. **Phase 1 deployment is the native Windows IB Gateway** (no Docker / IBC) per [ADR-040](../decisions/DECISIONS.md#adr-040--phase-1-deployment-target-windows-host-with-native-ib-gateway); the Docker + IBC bundling is deferred to M8 production cutover.

---

## 2. Asset Classes

| Asset class | TWS API support | Required tier | blive v1 priority |
|-------------|-----------------|----------------|-------------------|
| US cash equities (NYSE, NASDAQ, ARCA) | ✓ | `Network A/B/C` market data | high (Phase 2/3) |
| US ETFs | ✓ | as above | high (Phase 1–3) |
| European cash equities (LSE, XETR, EPA) | ✓ | per-exchange tier | medium (Phase 3, multi-currency) |
| European indices (CAC, DAX, FTSE) | ✓ as **index data** (not directly tradable) | per-exchange tier | high (A2 via tradable ETF proxy) |
| US listed options | ✓ | `OPRA` tier (paid) | future (A6, post-M8) |
| Index options (SPX, NDX, etc.) | ✓ | exchange tier | future |
| US index futures (ES, NQ, MES, MNQ) | ✓ | `CME L1` or `CME L2` tier | future (A2 alt or A8) |
| FX (IDEALPRO) | ✓ | `IDEALPRO` tier | future (A8) |
| Crypto (PAXOS) | ✓* | crypto sub-account | out of v1 |
| Bonds (corp, treasury) | ✓ | bond reference | out of v1 |
| Mutual funds | ✓ | — | out of v1 |
| CFDs | ✓ (non-US accounts) | per-exchange | out of v1 |

`Contract` resolution is by `ConID` (an integer IB ID); blive's `Instrument` ↔ `Contract` mapping happens in `IBBroker` and is documented in [DD-7 instrument_dictionary](../dd/instrument_dictionary.md) (STABLE v1.5).

---

## 3. Order Types

The TWS API exposes a long list; this is the subset blive cares about.

| Type | Equities / ETFs | Options | Futures | FX | Description |
|------|-----------------|---------|---------|-----|-------------|
| `MKT` | ✓ | ✓ | ✓ | ✓ | Market order at current best |
| `LMT` | ✓ | ✓ | ✓ | ✓ | Limit order at price |
| `STP` | ✓ | ✓ | ✓ | ✓ | Stop becomes market when triggered |
| `STP_LMT` | ✓ | ✓ | ✓ | ✓ | Stop becomes limit when triggered |
| `MOC` (Market on Close) | ✓ (US) | ✗ | ✓* | ✗ | Filled at closing auction |
| `LOC` (Limit on Close) | ✓ (US) | ✗ | ✓* | ✗ | Limit at close auction |
| `OPG` (At-the-Open) | ✓ | ✗ | ✓* | ✗ | Filled at opening auction |
| `MIDPRICE` | ✓ | ✓ | ✗ | ✗ | At midpoint of NBBO |
| `PEG_MID` | ✓ | ✓ | ✗ | ✗ | Pegged to midpoint |
| `TRAIL` (trailing stop) | ✓ | ✓ | ✓ | ✓ | Stop that trails best price |
| `RELATIVE` | ✓ | ✗ | ✓* | ✗ | Pegged to NBBO with offset |
| `BOX_TOP` | ✗ | ✓ | ✗ | ✗ | Options-only (BOX exchange) |

For blive v1: `MKT`, `LMT`, `MOC`, `LOC`, `OPG`, `STP`, `STP_LMT`. `TRAIL`, `MIDPRICE`, `PEG_MID` are nice-to-have post-M5.

---

## 4. Time-in-Force (TIF)

| TIF | Equities | Options | Futures | Notes |
|-----|----------|---------|---------|-------|
| `DAY` | ✓ | ✓ | ✓ | default; expires at session close |
| `GTC` (Good-til-Cancelled) | ✓ | ✓ | ✓ | survives daily TWS restart only if Order.Transmit was True; never for OCA-pending |
| `IOC` (Immediate-or-Cancel) | ✓ | ✓ | ✓ | fill what's possible immediately, cancel rest |
| `FOK` (Fill-or-Kill) | ✓ | ✓ | ✓ | fill all immediately or none |
| `OPG` (use Order.tif=OPG with `MKT`/`LMT`) | ✓ | ✗ | ✓* | only at open auction |
| `GTD` (Good-til-Date) | ✓ | ✓ | ✓ | requires `goodTillDate` field |
| `MOO` / `MOC` flavors | embedded in order_type | — | — | see §3 |

For blive v1: `DAY`, `IOC`, `OPG`. `GTC` only when explicit (parent-level OCA / multi-day work orders) — defer.

---

## 5. Routing

- **`SMART`** — IB's smart order router; default for most US equity routing. Handles dark pools and lit venues.
- **Direct exchange** — `NYSE`, `ARCA`, `ISLAND` (NASDAQ), `BATS`, `EDGEA`, etc. Used when SMART is wrong for a strategy.
- **For European exchanges**: routing matches the primary exchange (`SBF` for Paris, `IBIS` for Xetra, `LSE` for London).

For blive: strategies declare `Execution.live_overrides.routing` ([REQUIREMENTS §5.1](../../REQUIREMENTS.md)); default `SMART` for US equities/ETFs, primary exchange for European.

---

## 6. IB Algos

Available via `Order.algoStrategy` + `algoParams`:

| Algo | Use case |
|------|----------|
| `Adaptive` (with `adaptivePriority` Patient/Normal/Urgent) | most common drop-in for `MKT`/`LMT`; IB chooses tactic |
| `TWAP` | time-weighted across stated window |
| `VWAP` | volume-weighted; useful when `VolumeParticipation` is the binding constraint |
| `ArrivalPrice` | minimise impact vs. arrival mid |
| `Twap` (older) | pre-Adaptive; deprecated |
| `BalanceImpactRisk` | risk-adjusted impact |
| `MinimiseImpact` | aggressive impact minimisation |
| `ClosePrice` | volume-weighted approach to close |

For blive v1: Adaptive (Patient default) for non-MOC orders. TWAP/VWAP available via `live_overrides.algo` for high-impact rebalances. Algo selection per strategy.

**Wire finding (M2-IB.6.2c / M3.2):** `Adaptive` is available and correctly routed (`algoStrategy='Adaptive'`), but it does **not** bypass IB's regulatory Price-Management-Algo cap (warning **2161**) on UK-retail leveraged ETPs — QQL3 still doesn't fill under Adaptive (and the *visible* cap may not even fire; the non-fill is structural). See [INV-14](../inv/ib_error_codes.md) (2161), [ADR-049](../decisions/DECISIONS.md#adr-049--ordertypeadaptive_mkt-for-ibalgo-adaptive-routing-empirical-pma-cap-finding), [OQ-031](../decisions/OPEN_QUESTIONS.md#oq-031--phase-1-deployment-under-pma-bound-retail-account).

---

## 7. Market Hours

| Session | US equities | European equities | Notes |
|---------|-------------|-------------------|-------|
| Pre-market | 04:00–09:30 ET | venue-specific | requires `OutsideRTH=True` |
| Regular Trading Hours (RTH) | 09:30–16:00 ET | varies (08:00–16:30 LSE; 09:00–17:30 EPA) | most liquid |
| After-hours | 16:00–20:00 ET | venue-specific | requires `OutsideRTH=True` |
| Closing auction | 16:00 ET (US) | varies (16:30 EPA) | MOC/LOC fill here |
| Daily TWS restart window | ~23:45 ET | — | see [KB-3](ib_pacing_spec.md) |

For blive: RTH default; `OutsideRTH=True` allowed only via `Execution.live_overrides.outside_rth`. Calendar via `exchange_calendars` per [REQUIREMENTS §5.11](../../REQUIREMENTS.md).

---

## 8. Multi-Currency / FX

- IB accounts hold cash balances in multiple currencies natively (USD, EUR, GBP, JPY, etc.).
- Buying a EUR-denominated instrument from a USD-cash account: IB can auto-convert (settlement) or not, depending on account settings.
- FX is on `IDEALPRO` (with separate market data tier).
- For blive: realised FX P&L per fill at the rate IB applies; daily reval at close ([REQUIREMENTS §5.4](../../REQUIREMENTS.md), [OQ-007](../decisions/OPEN_QUESTIONS.md#oq-007--fx-real-time-conversion-vs-daily-close)).

---

## 9. Account Types

| Type | Notes | Relevance to blive |
|------|-------|---------------------|
| Individual | single owner | likely v1 |
| Cash | no margin | restricts strategies that need leverage |
| Margin (Reg-T or Portfolio Margin) | leverage available | needed for ADR-016 margin path |
| FA (Financial Advisor) sub-accounts | multi-client | out of v1 |
| Joint / Custodial / Trust | various | out of v1 |
| IBKR Pro vs Lite | Pro = full API + lower commissions; Lite = capped feature set | **IBKR Pro required** |

For blive: IBKR Pro Margin account. Sub-account routing deferred ([REQUIREMENTS §16](../../REQUIREMENTS.md)).

---

## 10. Authentication / Operations

- TWS / IB Gateway requires **2FA** on session start (mobile-key, IBKey, or fingerprint).
- **IBC** (Interactive Brokers Controller) automates the TWS / Gateway login screen. Works only with the *offline* installer; auto-update breaks it.
- **Daily restart** ~23:45 ET (configurable per region) — TWS / Gateway restarts; API session must reconnect; positions / orders persist on IB side.
- **Weekly token** — IBKey rotation Sundays.

Operational implications captured in [REQUIREMENTS §10 / §12](../../REQUIREMENTS.md) and [KB-3 §5](ib_pacing_spec.md#5-daily-and-weekly-operational-events).

---

## 11. Cross-References

- [KB-3 ib_pacing_spec](ib_pacing_spec.md) — numerical limits and pacing.
- [KB-4 frameworks_survey](frameworks_survey.md) — `ib_async` row.
- [REQUIREMENTS §5.2, §5.3, §10](../../REQUIREMENTS.md) — market data, orders, IB gotchas.
- [INV-2 order_types](../inv/order_types.md) (MISSING) — derived inventory of supported order types per asset class.
- [INV-10 asset_classes](../inv/asset_classes.md) (DRAFT) — derived inventory.

## Changelog

- **v0.1 (2026-04-26)** — initial bootstrap from IB docs.
- **v0.1.1 (2026-04-27)** — M2-entry review pass. No amendments needed; sources re-verified at IB docs (TWS API + Campus pages + `ib_async` README). The DRAFT → STABLE flip is deferred to M2 close once the IB read-side adapter has exercised the §2 (asset classes), §3 (order types), §4 (TIFs), §5 (routing), and §6 (algos) surfaces against IB Paper.
- **v1.0 (2026-06-05 / M3.6) — DRAFT → STABLE.** The Phase-1 IB surface is now wire-exercised end-to-end across M2-IB.6 + M3: §2 asset classes (US equities + LSE-ETF), §3 order types (MKT / LMT + ADAPTIVE_MKT), §5 routing (SMART + `primaryExchange=LSEETF` per [ADR-048](../decisions/DECISIONS.md#adr-048--lse-etf-smart-routing-discriminator-refines-adr-046)), §6 algos (Adaptive — with the 2161-cap finding added above), §7 market hours (LSE-RTH captures), §8 multi-currency (M3.4 live GBP+USD reconciliation). Stale ref fixed (DD-7 now STABLE v1.5); ADR-040 Phase-1-deployment + the 2161/Adaptive wire finding folded in. **Scope of STABLE: the Phase-1 equity/ETF surface.** Phase-2's futures / volatility instruments (VIX futures, leveraged / vol ETPs per the OQ-032 redesign) will re-exercise §2 / §3 / §6 / §7 and may flip this back to STALE for re-review.
