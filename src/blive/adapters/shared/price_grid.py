"""Venue price-grid snapping — pure, broker-agnostic (ADR-051).

Renders a strategy's economic price intent (a ``Decimal`` in real units)
onto a venue's legal price grid, so priced orders (LMT / STP / STP_LMT)
never violate the contract's minimum price variation (IB error 110).

The broker calls :func:`snap_price` at submit time with a per-contract
increment table sourced from the venue (IB market rule; ``minTick``
fallback — see :mod:`blive.adapters.ib.price_rules`). This module owns
only the *math*; sourcing + caching the table is a broker concern.

Price grids can be **banded**: the legal increment grows with price (LSE /
Euronext / MiFID-II tick regimes). A :class:`PriceIncrement` table
expresses each band as ``(low_edge, increment)``; a flat-tick instrument
is a single-row table. The table is assumed to cover from price 0 — the
IB market-rule invariant, and the ``minTick`` fallback constructs a
``low_edge=0`` band.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Sequence

from blive.domain.types import OrderSide


class RoundingPolicy(StrEnum):
    """How :func:`snap_price` resolves a price that falls between ticks.

    - :attr:`NEAREST` — closest legal tick (ties round up). The default;
      the sub-tick adjustment is dwarfed by the pipeline's aggressive
      limit offset and is directionally unbiased.
    - :attr:`CONSERVATIVE` — never worse than the computed price for the
      account: BUY rounds **down**, SELL rounds **up**. The recommended
      real-money policy (parked until live cutover per ADR-051).
    - :attr:`AGGRESSIVE` — preserve fill intent: BUY rounds **up**, SELL
      rounds **down**.
    """

    NEAREST = "NEAREST"
    CONSERVATIVE = "CONSERVATIVE"
    AGGRESSIVE = "AGGRESSIVE"


@dataclass(frozen=True, slots=True)
class PriceIncrement:
    """One band of a venue price grid: the legal tick ``increment`` for
    prices at or above ``low_edge`` (until the next band's ``low_edge``)."""

    low_edge: Decimal
    increment: Decimal

    def __post_init__(self) -> None:
        if self.increment <= 0:
            raise ValueError(f"PriceIncrement.increment must be > 0, got {self.increment}")
        if self.low_edge < 0:
            raise ValueError(f"PriceIncrement.low_edge must be >= 0, got {self.low_edge}")


def _band_for(price: Decimal, increments: Sequence[PriceIncrement]) -> PriceIncrement:
    """Return the band governing ``price``: the one with the greatest
    ``low_edge`` not exceeding ``price``. Falls back to the lowest band
    when ``price`` is below every ``low_edge`` (not expected when the
    table covers 0, which IB rules and the ``minTick`` fallback do)."""
    chosen = min(increments, key=lambda band: band.low_edge)
    for band in increments:
        if chosen.low_edge <= band.low_edge <= price:
            chosen = band
    return chosen


def snap_price(
    price: Decimal,
    increments: Sequence[PriceIncrement],
    *,
    side: OrderSide,
    policy: RoundingPolicy = RoundingPolicy.NEAREST,
) -> Decimal:
    """Snap ``price`` to a legal tick in its band per ``policy``.

    ``side`` selects the rounding direction for the directional policies
    (CONSERVATIVE / AGGRESSIVE); it is ignored for NEAREST. Raises
    :class:`ValueError` on a non-positive ``price`` or an empty table.
    """
    if price <= 0:
        raise ValueError(f"price must be > 0 to snap, got {price}")
    if not increments:
        raise ValueError("increments table must be non-empty")

    band = _band_for(price, increments)
    steps = (price - band.low_edge) / band.increment
    if policy is RoundingPolicy.NEAREST:
        rounding = ROUND_HALF_UP
    elif policy is RoundingPolicy.CONSERVATIVE:
        rounding = ROUND_FLOOR if side is OrderSide.BUY else ROUND_CEILING
    else:  # AGGRESSIVE
        rounding = ROUND_CEILING if side is OrderSide.BUY else ROUND_FLOOR
    k = steps.to_integral_value(rounding=rounding)
    snapped = band.low_edge + k * band.increment
    return snapped.quantize(band.increment)


__all__ = ["PriceIncrement", "RoundingPolicy", "snap_price"]
