"""IB per-contract price-grid metadata — source + cache for ADR-051.

Fetches each contract's minimum-price-variation grid from IB
(``reqContractDetailsAsync`` → ``marketRuleIds`` → ``reqMarketRuleAsync``)
and returns the banded
:class:`~blive.adapters.shared.price_grid.PriceIncrement` table that
:func:`~blive.adapters.shared.price_grid.snap_price` consumes. Caches per
:class:`~blive.domain.types.Instrument` (mirroring the conId cache in
:class:`~blive.adapters.ib.instrument_resolver.IBInstrumentResolver`),
with a :meth:`IBPriceRuleService.clear_cache` hook for M5 corp-action
invalidation.

The broker depends on the :class:`PriceIncrementProvider` Protocol, not
this concrete class (DIP) — tests inject a trivial fake.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Protocol, Sequence

import ib_async

from blive.adapters.ib.client import IBClient
from blive.adapters.ib.instrument_resolver import IBInstrumentResolver
from blive.adapters.shared.price_grid import PriceIncrement
from blive.domain.types import Instrument

log = logging.getLogger(__name__)


class PriceRuleUnavailable(Exception):
    """IB returned neither a usable market rule nor a positive ``minTick``
    for the contract; the order's price cannot be snapped to a legal grid
    and must not be sent (ADR-051 §"block, don't ship")."""


class PriceIncrementProvider(Protocol):
    """The narrow surface the broker needs (ADR-051 DIP): the price-increment
    table for an instrument. Implemented by :class:`IBPriceRuleService`;
    faked in tests."""

    async def increments_for(self, instrument: Instrument) -> Sequence[PriceIncrement]: ...


class IBPriceRuleService:
    """Sources + caches the IB price-increment table per instrument.

    One per :class:`IBClient`. Reuses an :class:`IBInstrumentResolver` for
    ``to_contract`` (no second conId cache); pass the broker's resolver to
    share it.
    """

    def __init__(
        self,
        client: IBClient,
        resolver: IBInstrumentResolver | None = None,
    ) -> None:
        self._client = client
        self._resolver = resolver if resolver is not None else IBInstrumentResolver(client)
        self._cache: dict[Instrument, tuple[PriceIncrement, ...]] = {}

    async def increments_for(self, instrument: Instrument) -> Sequence[PriceIncrement]:
        cached = self._cache.get(instrument)
        if cached is not None:
            return cached
        contract = self._resolver.to_contract(instrument)
        details = await self._fetch_details(contract, instrument)
        increments = await self._increments_from_details(details, instrument)
        self._cache[instrument] = increments
        return increments

    def clear_cache(self, instrument: Instrument | None = None) -> None:
        """Drop one or all cached tables (M5 corp-action hook; mirrors
        :meth:`IBInstrumentResolver.clear_cache`)."""
        if instrument is None:
            self._cache.clear()
            return
        self._cache.pop(instrument, None)

    # --- internals ----------------------------------------------------------

    async def _fetch_details(
        self, contract: ib_async.Contract, instrument: Instrument
    ) -> ib_async.ContractDetails:
        await self._client.rate_limiter.acquire("global")
        details_list = await self._client.ib.reqContractDetailsAsync(contract)
        candidates = list(details_list)
        if not candidates:
            raise PriceRuleUnavailable(
                f"reqContractDetails returned no details for {instrument!r}; "
                f"cannot determine the tick grid (ADR-051)."
            )
        # Prefer the details whose primaryExchange matches the routing hint
        # (a SMART contract returns one ContractDetails per valid exchange);
        # else the first.
        primary = getattr(contract, "primaryExchange", "") or ""
        if primary:
            for details in candidates:
                det_contract = getattr(details, "contract", None)
                if getattr(det_contract, "primaryExchange", "") == primary:
                    return details
        return candidates[0]

    async def _increments_from_details(
        self, details: ib_async.ContractDetails, instrument: Instrument
    ) -> tuple[PriceIncrement, ...]:
        # 1. Market rule (handles banded / price-dependent ticks).
        rule_id = self._governing_rule_id(details)
        if rule_id is not None:
            try:
                banded = await self._fetch_market_rule(rule_id)
            except Exception as exc:  # noqa: BLE001 — degrade to minTick on any wire error
                log.warning(
                    "IB reqMarketRule(%s) failed for %r (%s); falling back to minTick",
                    rule_id,
                    instrument,
                    exc,
                )
                banded = ()
            if banded:
                return banded
        # 2. Fallback: a single band from minTick.
        min_tick = _safe_decimal(getattr(details, "minTick", None))
        if min_tick is not None and min_tick > 0:
            return (PriceIncrement(low_edge=Decimal("0"), increment=min_tick),)
        raise PriceRuleUnavailable(
            f"IB contract details for {instrument!r} carry neither a market "
            f"rule nor a positive minTick; cannot snap to a tick grid (ADR-051)."
        )

    def _governing_rule_id(self, details: ib_async.ContractDetails) -> int | None:
        rule_ids = [r.strip() for r in (getattr(details, "marketRuleIds", "") or "").split(",")]
        valid_exch = [e.strip() for e in (getattr(details, "validExchanges", "") or "").split(",")]
        det_contract = getattr(details, "contract", None)
        target = (
            getattr(det_contract, "primaryExchange", "")
            or getattr(det_contract, "exchange", "")
            or ""
        )
        # Market-rule ids align positionally with valid exchanges; prefer the
        # rule for the governing (primary / routing) exchange.
        if target and len(rule_ids) == len(valid_exch):
            for exch, rid in zip(valid_exch, rule_ids):
                if exch == target and rid:
                    return _safe_int(rid)
        for rid in rule_ids:
            if rid:
                return _safe_int(rid)
        return None

    async def _fetch_market_rule(self, rule_id: int) -> tuple[PriceIncrement, ...]:
        await self._client.rate_limiter.acquire("global")
        rule = await self._client.ib.reqMarketRuleAsync(rule_id)
        out: list[PriceIncrement] = []
        for increment in rule or []:
            low = _safe_decimal(getattr(increment, "lowEdge", None))
            step = _safe_decimal(getattr(increment, "increment", None))
            if low is None or step is None or step <= 0:
                continue
            out.append(PriceIncrement(low_edge=low, increment=step))
        out.sort(key=lambda band: band.low_edge)
        return tuple(out)


def _safe_int(value: str) -> int | None:
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _safe_decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (ValueError, ArithmeticError):
        return None


__all__ = [
    "IBPriceRuleService",
    "PriceIncrementProvider",
    "PriceRuleUnavailable",
]
