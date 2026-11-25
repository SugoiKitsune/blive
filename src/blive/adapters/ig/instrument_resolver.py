"""IG instrument resolver — :class:`Instrument` ↔ IG epic.

Implements [DD-8](../../../../docs/dd/ig_instrument_dictionary.md) §6 public
surface per [ADR-032](../../../../docs/decisions/DECISIONS.md#adr-032--instrument-resolution-policy-blive-instrument--ib-contract)
(IB analogue) extended with [ADR-037](../../../../docs/decisions/DECISIONS.md#adr-037--instrumenttradability-field-spot--cfd--spread_bet)
``tradability`` discriminator.

Resolution flow (DD-8 §4):

1. Compute an epic *guess* from ``(asset_class, tradability, symbol)``
   per the DD-8 §3 family table. Phase 1 case: ``INDEX × cfd × CAC40``
   → ``IX.D.CAC40.CASH.IP``.
2. Try ``GET /markets/{epic}``. On 200, cache + return.
3. On 404 / unknown-instrument, fall back to ``GET /markets?searchTerm=…``
   and pick a candidate by family + symbol match.
4. Multiple candidates after filtering raise :class:`InstrumentAmbiguous` —
   never silently pick.

Cache lifetime: process. Corp-action invalidation via :meth:`clear_cache`
(M5 reconciliation hook). All wire calls go through :class:`IGClient`'s
rate-limited dispatch.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping

from blive.adapters.ig.client import IGClient, IGRequestInvalid
from blive.domain.types import AssetClass, Instrument, Tradability

log = logging.getLogger(__name__)


# --- IG epic family table (DD-8 §3) -----------------------------------------


def _epic_family(asset_class: AssetClass, tradability: Tradability) -> str:
    """Return the IG epic family code for the given (asset_class, tradability).

    Phase 1 row: ``INDEX × cfd`` → ``IX.D``. Other combinations either map
    to a cash-equity / FX / commodity family or raise.
    """
    if tradability == "spot":
        # Spot ownership on IG retail UK is share-dealing only and out of
        # this resolver's scope (M2-IG bridge runs on CFD demo per ADR-039).
        raise InstrumentNotResolvable(
            f"IG resolver does not support tradability='spot' instruments; "
            f"got asset_class={asset_class.value}, symbol-resolution requires "
            f"tradability='cfd' or 'spread_bet' on IG retail UK."
        )

    # CFD / spread bet: family by asset class (per DD-8 §1 epic taxonomy).
    if asset_class == AssetClass.INDEX:
        return "IX.D"
    if asset_class in (AssetClass.EQUITY, AssetClass.ETF):
        # IG treats ETFs in the cash-equity family per DD-8 §3 footnote.
        return "KC.D"
    if asset_class == AssetClass.FX:
        return "CS.D"
    if asset_class == AssetClass.FUTURE:
        # Continuous futures live under IX.D with .MONTHN.IP settlement.
        return "IX.D"
    if asset_class == AssetClass.OPTION:
        # KA = equity options; KB = index options. Resolver picks KA by default;
        # callers needing KB pass an override (out of M2-IG.3 scope).
        raise InstrumentNotResolvable(
            f"IG OPTION resolution not yet supported (M2-IG bridge runs on "
            f"CAC 40 CFD); got asset_class={asset_class.value}"
        )
    raise InstrumentNotResolvable(
        f"IG resolver has no family mapping for asset_class={asset_class.value!r}"
    )


def _epic_settlement_segment(tradability: Tradability) -> str:
    """Final ``.MODE.IP`` segment of an IG epic.

    Phase 1 case: ``cfd`` → ``CASH`` (rolling cash CFD). Per DD-8 §3, FX
    CFDs use ``.CFD.IP`` instead — handled by callers needing FX.
    """
    if tradability == "cfd":
        return "CASH.IP"
    if tradability == "spread_bet":
        # Spread bets share the same epic structure but a different account
        # type; the .IP suffix stays.
        return "CASH.IP"
    raise InstrumentNotResolvable(
        f"_epic_settlement_segment unreachable for tradability={tradability!r}"
    )


def _guess_epic(instrument: Instrument) -> str:
    """Compose the IG epic guess from `(family, type, symbol, settlement)`.

    Phase 1 example: ``Instrument(symbol="CAC40", asset_class=INDEX, tradability="cfd")``
    → ``"IX.D.CAC40.CASH.IP"``.
    """
    family = _epic_family(instrument.asset_class, instrument.tradability)
    settlement = _epic_settlement_segment(instrument.tradability)
    return f"{family}.{instrument.symbol}.{settlement}"


# --- Public types -----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class IGMarketMetadata:
    """Subset of IG ``GET /markets/{epic}`` response that the resolver caches.

    Sufficient for the Sizer's precision lookup and for sanity-checking
    currency / lot size on first resolve.
    """

    epic: str
    name: str
    currency: str
    lot_size: Decimal
    min_deal_size: Decimal
    """Minimum deal size in instrument units (CFD: typically 0.1 / 0.01 / 0.5)."""


class InstrumentNotResolvable(Exception):
    """The instrument's ``(asset_class, tradability)`` doesn't map to any IG
    epic family, or the search fallback found zero candidates."""


class InstrumentAmbiguous(Exception):
    """Multiple IG epic candidates matched after filtering. Carries the
    candidate list so the operator can construct a more specific
    :class:`Instrument` (e.g. by setting ``venue`` to the desired primary)."""

    def __init__(self, instrument: Instrument, candidates: list[Mapping[str, Any]]) -> None:
        self.instrument = instrument
        self.candidates = candidates
        super().__init__(
            f"IG returned {len(candidates)} candidates for {instrument!r}; "
            f"resolution requires a more specific Instrument. Candidates: "
            f"{[c.get('epic') for c in candidates]}"
        )


# --- Resolver ---------------------------------------------------------------


class IGInstrumentResolver:
    """Per DD-8 §6. Construct one of these per :class:`IGClient` instance.

    Cache is in-process memory keyed by full ``Instrument`` tuple equality
    (the dataclass is frozen so it hashes by value). Corp-action handling
    invokes :meth:`clear_cache` from M5 reconciliation when that lands.
    """

    def __init__(self, client: IGClient) -> None:
        self._client = client
        self._epic_cache: dict[Instrument, str] = {}
        self._metadata_cache: dict[str, IGMarketMetadata] = {}

    # --- Public surface -----------------------------------------------------

    async def resolve(self, instrument: Instrument) -> str:
        """Return the IG epic for the given instrument.

        Lazy + cached. First call triggers ``GET /markets/{epic_guess}``;
        on 404 falls back to ``GET /markets?searchTerm=…``. Multiple
        candidates raise :class:`InstrumentAmbiguous`.
        """
        if instrument in self._epic_cache:
            return self._epic_cache[instrument]

        epic_guess = _guess_epic(instrument)
        epic = await self._try_resolve_via_guess_then_search(instrument, epic_guess)
        self._epic_cache[instrument] = epic
        return epic

    async def market_metadata(self, instrument: Instrument) -> IGMarketMetadata:
        """Return the cached :class:`IGMarketMetadata` for the given instrument.

        First call triggers :meth:`resolve` (if not already cached) plus a
        ``GET /markets/{epic}`` fetch — but the typical case is that the
        resolution path *itself* fetched and cached the metadata, so this
        is a memo lookup.
        """
        epic = await self.resolve(instrument)
        if epic not in self._metadata_cache:
            await self._fetch_and_cache_metadata(epic)
        return self._metadata_cache[epic]

    async def precision_for(self, instrument: Instrument) -> Decimal:
        """Return the sizing precision per [ADR-037](../../../../docs/decisions/DECISIONS.md#adr-037--instrumenttradability-field-spot--cfd--spread_bet).

        - ``tradability == "spot"`` → ``Decimal("1")`` (integer shares).
          Note: the IG resolver doesn't actually resolve spot instruments
          (raises :class:`InstrumentNotResolvable`); this branch exists for
          a possible future where IG share-dealing accounts are supported.
        - ``tradability in {"cfd", "spread_bet"}`` →
          ``market_metadata.min_deal_size`` (per-instrument from IG).
        """
        if instrument.tradability == "spot":
            return Decimal("1")
        meta = await self.market_metadata(instrument)
        return meta.min_deal_size

    def clear_cache(self, instrument: Instrument | None = None) -> None:
        """Drop one or all entries from both caches.

        Called when M5 reconciliation observes corp-action drift. ``None``
        flushes everything.
        """
        if instrument is None:
            self._epic_cache.clear()
            self._metadata_cache.clear()
            return
        if instrument in self._epic_cache:
            epic = self._epic_cache.pop(instrument)
            self._metadata_cache.pop(epic, None)

    # --- Internals ----------------------------------------------------------

    async def _try_resolve_via_guess_then_search(
        self, instrument: Instrument, epic_guess: str
    ) -> str:
        """Try ``GET /markets/{epic}`` first; fall back to search on 404."""
        try:
            await self._fetch_and_cache_metadata(epic_guess)
            return epic_guess
        except IGRequestInvalid as exc:
            if exc.error_code != "error.invalid.instrument":
                raise
            # Fall through to search.
        return await self._resolve_via_search(instrument)

    async def _resolve_via_search(self, instrument: Instrument) -> str:
        """Search by symbol, filter by family, raise on zero / many."""
        family = _epic_family(instrument.asset_class, instrument.tradability)
        body = await self._client.get(
            "/markets",
            version=1,
            params={"searchTerm": instrument.symbol},
        )
        candidates_raw = body.get("markets", []) if isinstance(body, dict) else []
        # Filter to candidates whose epic starts with our family code.
        candidates: list[Mapping[str, Any]] = [
            m
            for m in candidates_raw
            if isinstance(m, dict)
            and isinstance(m.get("epic"), str)
            and m["epic"].startswith(f"{family}.")
        ]
        if not candidates:
            raise InstrumentNotResolvable(
                f"IG search for symbol={instrument.symbol!r} family={family!r} "
                f"returned no candidates"
            )
        if len(candidates) > 1:
            raise InstrumentAmbiguous(instrument, candidates)
        epic = str(candidates[0]["epic"])
        # Fetch and cache metadata for the resolved epic.
        await self._fetch_and_cache_metadata(epic)
        return epic

    async def _fetch_and_cache_metadata(self, epic: str) -> None:
        """``GET /markets/{epic}`` → parse → cache."""
        body = await self._client.get(f"/markets/{epic}", version=3)
        if not isinstance(body, dict):
            raise IGRequestInvalid(
                f"IG /markets/{epic} returned non-dict body: {type(body).__name__}"
            )
        metadata = _parse_market_metadata(epic, body)
        self._metadata_cache[epic] = metadata


def _parse_market_metadata(epic: str, body: Mapping[str, Any]) -> IGMarketMetadata:
    """Extract the fields :class:`IGMarketMetadata` cares about.

    IG's ``/markets/{epic}`` response has many more fields; this function
    is intentionally narrow — adding fields means changing the dataclass.
    """
    instrument = body.get("instrument")
    dealing_rules = body.get("dealingRules")
    if not isinstance(instrument, dict) or not isinstance(dealing_rules, dict):
        raise IGRequestInvalid(
            f"IG /markets/{epic} body missing instrument / dealingRules: keys={list(body)}"
        )

    name = str(instrument.get("name", ""))
    if not name:
        raise IGRequestInvalid(f"IG /markets/{epic} instrument has no name")

    currencies = instrument.get("currencies")
    if not isinstance(currencies, list) or not currencies:
        raise IGRequestInvalid(f"IG /markets/{epic} instrument has no currencies")
    first_currency = currencies[0]
    if not isinstance(first_currency, dict) or not isinstance(first_currency.get("code"), str):
        raise IGRequestInvalid(f"IG /markets/{epic} first currency missing 'code'")
    currency = str(first_currency["code"])

    lot_size_raw = instrument.get("lotSize", 1)
    lot_size = Decimal(str(lot_size_raw))

    min_deal_size_obj = dealing_rules.get("minDealSize")
    if not isinstance(min_deal_size_obj, dict) or "value" not in min_deal_size_obj:
        raise IGRequestInvalid(
            f"IG /markets/{epic} dealingRules.minDealSize malformed: {min_deal_size_obj!r}"
        )
    min_deal_size = Decimal(str(min_deal_size_obj["value"]))

    return IGMarketMetadata(
        epic=epic,
        name=name,
        currency=currency,
        lot_size=lot_size,
        min_deal_size=min_deal_size,
    )


__all__ = [
    "IGInstrumentResolver",
    "IGMarketMetadata",
    "InstrumentAmbiguous",
    "InstrumentNotResolvable",
]
