"""IB instrument resolver — :class:`Instrument` ↔ ``ib_async.Contract`` / ``conId``.

Implements [DD-7 §5](../../../../docs/dd/instrument_dictionary.md#5-public-surface-m2-module)
public surface per [ADR-032](../../../../docs/decisions/DECISIONS.md#adr-032--instrument-resolution-policy-blive-instrument--ib-contract).
The IB analogue of :class:`blive.adapters.ig.instrument_resolver.IGInstrumentResolver`.

Resolution flow (DD-7 §4):

1. Build an ``ib_async.Contract`` from the broker-neutral
   :class:`blive.domain.types.Instrument` via :meth:`to_contract` (sync,
   no wire call) per the DD-7 §1 field map + §2 secType + §3 exchange
   tables.
2. On first :meth:`resolve` call for a given instrument, invoke
   ``ib.qualifyContractsAsync(contract)``; the call consumes one
   ``global`` token from the rate limiter.
3. Cache the resulting ``conId`` keyed by full :class:`Instrument` tuple
   equality. Subsequent calls return the cached id without a wire trip.
4. Multiple candidates after qualification raise :class:`InstrumentAmbiguous`;
   zero candidates / ``conId == 0`` raise :class:`InstrumentNotResolvable`.
   The resolver **never silently picks** when the venue is ambiguous —
   the caller must construct a more specific :class:`Instrument`.

Cache lifetime: process. Corp-action invalidation via :meth:`clear_cache`
(M5 reconciliation hook). All wire calls go through :class:`IBClient`'s
:class:`TokenBucketRateLimiter` budget.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Mapping

import ib_async

from blive.adapters.ib.client import IBClient
from blive.domain.types import AssetClass, Instrument

log = logging.getLogger(__name__)


# --- DD-7 §2: AssetClass → IB secType ---------------------------------------

_ASSET_CLASS_TO_SEC_TYPE: Mapping[AssetClass, str] = {
    AssetClass.EQUITY: "STK",
    AssetClass.ETF: "STK",
    AssetClass.INDEX: "IND",
    AssetClass.FX: "CASH",
    AssetClass.FUTURE: "FUT",
    AssetClass.OPTION: "OPT",
}


# --- DD-7 §3: venue (MIC) → IB exchange -------------------------------------

# For *direct-routed* venues (XPAR, XLON, XETR), the value is the IB
# `Contract.exchange` field directly. For *SMART-routed* US-equity venues
# (XNAS, XNYS, ARCX, BATS — see :data:`_US_SMART_VENUES` below), the value
# is the IB-named exchange used as the `primaryExchange` hint, and the
# `Contract.exchange` field is set to ``"SMART"`` per [ADR-046](../../../../docs/decisions/DECISIONS.md#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032).
#
# Phase 1 needs XPAR (CAC.PA, substrate) + XNAS (TQQQ, IEF) + XNYS (TMF)
# per [ADR-043](../../../../docs/decisions/DECISIONS.md#adr-043--phase-1-strategy-switch-triple_lev_sma_filter_dsl-a3-replaces-tkan_v4_momentum_timing-a2).
# Future venues add rows. Keep this table internal — adapters import it
# via constants module if / when other modules need to reuse the mapping.
_MIC_TO_IB_EXCHANGE: Mapping[str, str] = {
    "XPAR": "SBF",
    "XNAS": "NASDAQ",
    "XNYS": "NYSE",
    "ARCX": "ARCA",
    "BATS": "BATS",
    "XLON": "LSE",
    "XETR": "IBIS",
    # EU single-name venues for the R05 dividend book (Nordics + Iberia + Amsterdam). IB exchange
    # codes are best-known; qualifyContractsAsync validates each on first resolve (a wrong code → 0
    # candidates → InstrumentNotResolvable, never a silent mis-route).
    # IB has NO direct Oslo Børs (OSE) destination — Norwegian names route via OMXNO (confirmed by IB
    # support; OSE → IB-460 "No trading permissions"). ISIN resolution + OMXNO finds the contract.
    # "many but not all" OSE names are on OMXNO; a missing one → 0 candidates → InstrumentNotResolvable.
    "XOSL": "OMXNO",  # Oslo Børs via OMXNO — most of R05 (FRO/DNO/BWO/SUBC/AKRBP/…)
    "XCSE": "CPH",    # Nasdaq Copenhagen (TRMD-A)
    "XMAD": "BM",     # Bolsa de Madrid / BME (REP)
    "XAMS": "AEB",    # Euronext Amsterdam (KENDR)
    # Nasdaq Stockholm (SWED-A, an 11% R05 weight). Its absence was NOT an account permission — the
    # resolver rejected the venue before ever calling IB ("no exchange mapping for MIC venue='XSTO'"),
    # so the leg was BLOCKED on every run since inception and SEK never appeared in the account.
    "XSTO": "SFB",    # Nasdaq Stockholm (SWED-A)
}


# US-equity venues that route via SMART per [ADR-046](../../../../docs/decisions/DECISIONS.md#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032).
# When ``instrument.venue`` is in this set AND
# ``instrument.tradability == "spot"`` AND ``instrument.asset_class`` is
# ``EQUITY`` or ``ETF``, :meth:`IBInstrumentResolver.to_contract`
# constructs a ``Contract`` with ``exchange="SMART"`` and the
# ``primaryExchange`` hint from :data:`_MIC_TO_IB_EXCHANGE`. This both
# avoids IB Paper's "Direct Routed Orders" precaution at error 10311
# (observed at `M2-IB.4a-rejected`) and matches IB's recommended
# best practice for US equities.
#
# Non-US venues retain direct routing — SMART support varies by venue
# and revisits per venue (XLON / XETR direct routing per DD-7 §3).
_US_SMART_VENUES: frozenset[str] = frozenset({"XNAS", "XNYS", "ARCX", "BATS"})


# LSE ETF / ETP venue: WisdomTree / iShares UCITS-ETPs on LSE are not
# accessible via the bare ``"LSE"`` direct exchange (IB error 200). They
# trade on IB's separate ``"LSEETF"`` venue. Probed at M2-IB.6.1 against
# the Phase 1 universe (QQL3 / IBTL / IBTM): all three resolve via
# ``Contract(exchange="SMART", primaryExchange="LSEETF")`` regardless of
# share-class currency. Mirrors the ADR-046 SMART pattern for US equities.
#
# Discriminator: ``venue == "XLON" AND asset_class == ETF AND
# tradability == "spot"`` -> SMART + primaryExchange=LSEETF. XLON +
# EQUITY (single-name UK shares) keeps direct ``"LSE"`` routing per the
# existing _MIC_TO_IB_EXCHANGE table — the LSE main book and LSE ETF
# book are distinct IB venues.
_LSE_ETF_SMART_PRIMARY = "LSEETF"


# Asset classes that participate in the SMART convention. Options /
# futures grow their own routing table when those asset classes land
# (per DD-7 §3 SMART discriminator note).
_SMART_ELIGIBLE_ASSET_CLASSES: frozenset[AssetClass] = frozenset(
    {AssetClass.EQUITY, AssetClass.ETF}
)


# --- DD-7 §3.1: Yahoo Finance / EODHD exchange-suffix → MIC -----------------

# Yahoo Finance and EODHD encode the listing exchange in the ticker suffix
# (e.g. "CAC.PA" for Euronext Paris, "BARC.L" for London). IB's TWS API
# uses the *bare* ticker on the corresponding primary exchange. When the
# blive Instrument's symbol arrives with a known Yahoo suffix matching its
# venue, the IB resolver strips the suffix before constructing the
# Contract. Per [ADR-041](../../../../docs/decisions/DECISIONS.md#adr-041--yahoo-suffix-translation-in-ib-instrument-resolver):
# the broker-neutral Instrument keeps the EODHD-friendly form;
# adapter-specific translation lives here.
#
# Confirmed at M2-IB.3a probe (2026-05-01): IB rejects "CAC.PA" /
# accepts "CAC" on SBF (conId=11183823). Other rows are best-known-as-of
# the Yahoo suffix convention; lazy-validated when the corresponding
# instrument is first resolved.
_YAHOO_SUFFIX_BY_MIC: Mapping[str, str] = {
    "XPAR": ".PA",  # Euronext Paris
    "XLON": ".L",  # London Stock Exchange
    "XETR": ".DE",  # Xetra (Deutsche Börse)
    "XAMS": ".AS",  # Euronext Amsterdam
}


def _ib_symbol(instrument: Instrument) -> str:
    """Translate the broker-neutral symbol to IB's wire form.

    When the instrument's ``symbol`` ends with a Yahoo Finance / EODHD
    exchange suffix matching its ``venue`` MIC, strip the suffix. Otherwise
    pass through unchanged. Per ADR-041 + DD-7 §3.1.
    """
    suffix = _YAHOO_SUFFIX_BY_MIC.get(instrument.venue)
    if suffix is not None and instrument.symbol.endswith(suffix):
        return instrument.symbol[: -len(suffix)]
    return instrument.symbol


# --- Public errors ----------------------------------------------------------


class InstrumentNotResolvable(Exception):
    """The instrument's ``(asset_class, tradability, venue)`` doesn't map to
    any IB ``secType`` / ``exchange``, **or** ``qualifyContractsAsync`` returned
    zero candidates / a candidate with ``conId == 0``."""


class InstrumentAmbiguous(Exception):
    """Multiple IB ``Contract`` candidates matched after qualification.

    Carries the candidate list so the caller can pick by primary exchange
    or currency; the resolver never silently picks per [ADR-032 §"Ambiguity"](../../../../docs/decisions/DECISIONS.md#adr-032--instrument-resolution-policy-blive-instrument--ib-contract).
    """

    def __init__(
        self,
        instrument: Instrument,
        candidates: list[ib_async.Contract],
    ) -> None:
        self.instrument = instrument
        self.candidates = candidates
        candidate_summary = [(c.conId, c.primaryExchange, c.currency) for c in candidates]
        super().__init__(
            f"IB qualifyContractsAsync returned {len(candidates)} candidates "
            f"for {instrument!r}; resolution requires a more specific Instrument. "
            f"Candidates (conId, primaryExchange, currency): {candidate_summary}"
        )


# --- Resolver ---------------------------------------------------------------


class IBInstrumentResolver:
    """:class:`Instrument` → ``conId`` resolution + cache per DD-7.

    Construct one of these per :class:`IBClient` instance. Cache is
    in-process memory keyed by full :class:`Instrument` tuple equality
    (the dataclass is frozen and hashable). Corp-action handling invokes
    :meth:`clear_cache` from M5 reconciliation when that lands.
    """

    def __init__(self, client: IBClient) -> None:
        self._client = client
        self._conid_cache: dict[Instrument, int] = {}

    # --- Public surface -----------------------------------------------------

    def to_contract(self, instrument: Instrument) -> ib_async.Contract:
        """Build a fresh ``ib_async.Contract`` from the instrument's fields.

        Synchronous, pure — no wire call, no cache mutation. Does NOT fill
        in ``conId``; that's :meth:`resolve`'s job. Used both by
        :meth:`resolve` and by callers that need a Contract for a
        ``reqHistoricalData`` / ``reqMktData`` call where pre-qualification
        isn't desired.

        Raises :class:`InstrumentNotResolvable` on field mappings the
        resolver can't translate (CFD/spread_bet tradability, unknown
        ``asset_class``, unknown ``venue`` MIC).
        """
        if instrument.tradability != "spot":
            # Per ADR-037: IB Paper trades cash ETFs / shares (spot). CFD
            # and spread-bet variants don't exist on IB retail; the IG
            # adapter handles those.
            raise InstrumentNotResolvable(
                f"IB resolver does not support tradability="
                f"{instrument.tradability!r}; IB retail trades spot only "
                f"(per ADR-037 + ADR-021). Got instrument={instrument!r}"
            )

        sec_type = _ASSET_CLASS_TO_SEC_TYPE.get(instrument.asset_class)
        if sec_type is None:
            raise InstrumentNotResolvable(
                f"IB resolver has no secType mapping for asset_class="
                f"{instrument.asset_class!r}; extend "
                f"_ASSET_CLASS_TO_SEC_TYPE or DD-7 §2."
            )

        ib_exchange_value = _MIC_TO_IB_EXCHANGE.get(instrument.venue)
        if ib_exchange_value is None:
            raise InstrumentNotResolvable(
                f"IB resolver has no exchange mapping for MIC venue="
                f"{instrument.venue!r}; extend _MIC_TO_IB_EXCHANGE or DD-7 §3."
            )

        # SMART-routing discriminator per [ADR-046](../../../../docs/decisions/DECISIONS.md#adr-046--ib-resolver-smart-routing-for-us-equities-refines-adr-032)
        # + DD-7 §3: applies when venue ∈ US-SMART set AND tradability="spot"
        # AND asset_class ∈ {EQUITY, ETF}. For SMART-routed venues, the
        # _MIC_TO_IB_EXCHANGE value is the primaryExchange hint and the
        # Contract.exchange is "SMART"; otherwise it's the routing exchange
        # directly.
        #
        # XLON ETFs route via SMART with primaryExchange="LSEETF" (not the
        # main-book "LSE") — IB exposes LSE-listed UCITS ETPs on a distinct
        # venue. Probed at M2-IB.6.1; see :data:`_LSE_ETF_SMART_PRIMARY`.
        if (
            instrument.venue in _US_SMART_VENUES
            and instrument.asset_class in _SMART_ELIGIBLE_ASSET_CLASSES
        ):
            exchange = "SMART"
            primary_exchange = ib_exchange_value
        elif instrument.venue == "XLON" and instrument.asset_class == AssetClass.ETF:
            exchange = "SMART"
            primary_exchange = _LSE_ETF_SMART_PRIMARY
        else:
            exchange = ib_exchange_value
            primary_exchange = ""  # IB convention: empty string when not SMART-routed.

        # multiplier: empty string for STK / IND / CASH (DD-7 §1); the
        # actual multiplier value for OPT / FUT.
        multiplier_str = "" if instrument.multiplier == Decimal("1") else str(instrument.multiplier)

        contract = ib_async.Contract(
            symbol=_ib_symbol(instrument),
            secType=sec_type,
            currency=instrument.currency,
            exchange=exchange,
            primaryExchange=primary_exchange,
            multiplier=multiplier_str,
        )
        if getattr(instrument, "isin", None):
            # Resolve by ISIN (secIdType/secId) — robust for cross-border EU listings where the IB wire
            # symbol differs from the EODHD/Yahoo ticker (BP.LSE, TRMD-A.CO both failed by symbol). IB
            # qualifies on ISIN + exchange + currency; clear the symbol hint so a stale ticker can't
            # conflict with the ISIN match.
            contract.secIdType = "ISIN"
            contract.secId = instrument.isin
            contract.symbol = ""
        return contract

    async def resolve(self, instrument: Instrument) -> int:
        """Return the IB ``conId`` for the given instrument.

        Lazy + cached. First call triggers ``ib.qualifyContractsAsync``
        on the constructed Contract; on success, the integer ``conId``
        is cached and returned.

        Raises :class:`InstrumentNotResolvable` if the field mapping
        rejects the instrument (see :meth:`to_contract`), if
        ``qualifyContractsAsync`` returns zero candidates, or if the
        single candidate has ``conId == 0`` (ib_async's "unqualified"
        sentinel).

        Raises :class:`InstrumentAmbiguous` if multiple candidates
        match — the caller must construct a more specific Instrument
        (typically by setting ``venue`` to the desired primary exchange's
        MIC).

        Consumes one token from the ``global`` rate-limiter bucket per
        wire-level call (cache hits don't acquire).
        """
        if instrument in self._conid_cache:
            return self._conid_cache[instrument]

        contract = self.to_contract(instrument)
        await self._client.rate_limiter.acquire("global")
        # ib_async typing: qualifyContractsAsync is variadic and may return
        # nested lists / Nones for individual inputs. We pass exactly one
        # Contract, so the result is a flat list of qualified Contracts;
        # filter to drop any Nones / nested lists defensively.
        result = await self._client.ib.qualifyContractsAsync(contract)
        candidates: list[ib_async.Contract] = [
            c for c in result if isinstance(c, ib_async.Contract)
        ]

        if not candidates:
            raise InstrumentNotResolvable(
                f"IB qualifyContractsAsync returned zero candidates for "
                f"{instrument!r}; the symbol/exchange/currency triple may be "
                f"wrong, or the instrument may not be available under the "
                f"market-data subscription tier."
            )
        if len(candidates) > 1:
            raise InstrumentAmbiguous(instrument, candidates)

        conid = candidates[0].conId
        if not conid:
            raise InstrumentNotResolvable(
                f"IB qualifyContractsAsync returned a Contract with "
                f"conId=0 for {instrument!r} — IB treats this as 'not "
                f"qualified'; check the contract fields (symbol, exchange, "
                f"currency) for a typo."
            )

        self._conid_cache[instrument] = conid
        return conid

    def clear_cache(self, instrument: Instrument | None = None) -> None:
        """Drop one or all entries from the conId cache.

        Called when M5 reconciliation observes corp-action drift (a fresh
        ``conId`` arrives from the venue, indicating a contract change).
        ``instrument=None`` flushes the entire cache; ``instrument=...``
        drops just that one row.
        """
        if instrument is None:
            self._conid_cache.clear()
            return
        self._conid_cache.pop(instrument, None)


__all__ = [
    "IBInstrumentResolver",
    "InstrumentAmbiguous",
    "InstrumentNotResolvable",
]
