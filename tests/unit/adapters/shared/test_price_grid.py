"""Tests for :mod:`blive.adapters.shared.price_grid` (ADR-051 pure snapping).

The snapping math is the most edge-case-rich part of the tick-grid fix, so
it carries the bulk of the coverage: flat + banded grids, every rounding
policy, band selection (incl. unsorted tables and band edges), and the
input guards. The QQL3 0.10-tick regression (38.52 → 38.50) is covered
explicitly.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from blive.adapters.shared.price_grid import PriceIncrement, RoundingPolicy, snap_price
from blive.domain.types import OrderSide


def _flat(tick: str) -> list[PriceIncrement]:
    return [PriceIncrement(Decimal("0"), Decimal(tick))]


def _banded() -> list[PriceIncrement]:
    # 0.001 below 1.0, 0.005 in [1, 10), 0.01 at/above 10.
    return [
        PriceIncrement(Decimal("0"), Decimal("0.001")),
        PriceIncrement(Decimal("1"), Decimal("0.005")),
        PriceIncrement(Decimal("10"), Decimal("0.01")),
    ]


# --- PriceIncrement validation ----------------------------------------------


def test_increment_must_be_positive() -> None:
    with pytest.raises(ValueError):
        PriceIncrement(Decimal("0"), Decimal("0"))
    with pytest.raises(ValueError):
        PriceIncrement(Decimal("0"), Decimal("-0.1"))


def test_low_edge_must_be_nonnegative() -> None:
    with pytest.raises(ValueError):
        PriceIncrement(Decimal("-1"), Decimal("0.1"))


# --- flat grid, NEAREST (the QQL3 regression) -------------------------------


@pytest.mark.parametrize(
    "price,expected",
    [
        ("38.52", "38.50"),  # the exact pre-ADR-051 error-110 case
        ("42.83", "42.80"),
        ("44.15", "44.20"),  # ties round up (441.5 -> 442)
        ("39.60", "39.60"),  # already on grid -> no-op
        ("41.50", "41.50"),
    ],
)
def test_nearest_snaps_to_010_grid(price: str, expected: str) -> None:
    out = snap_price(Decimal(price), _flat("0.10"), side=OrderSide.BUY)
    assert out == Decimal(expected)


def test_fine_penny_grid_leaves_penny_price_unchanged() -> None:
    assert snap_price(Decimal("123.45"), _flat("0.01"), side=OrderSide.BUY) == Decimal("123.45")


# --- directional policies ----------------------------------------------------


def test_conservative_buy_down_sell_up() -> None:
    grid = _flat("0.10")
    assert snap_price(
        Decimal("44.15"), grid, side=OrderSide.BUY, policy=RoundingPolicy.CONSERVATIVE
    ) == Decimal("44.10")
    assert snap_price(
        Decimal("44.11"), grid, side=OrderSide.SELL, policy=RoundingPolicy.CONSERVATIVE
    ) == Decimal("44.20")


def test_aggressive_buy_up_sell_down() -> None:
    grid = _flat("0.10")
    assert snap_price(
        Decimal("44.11"), grid, side=OrderSide.BUY, policy=RoundingPolicy.AGGRESSIVE
    ) == Decimal("44.20")
    assert snap_price(
        Decimal("44.19"), grid, side=OrderSide.SELL, policy=RoundingPolicy.AGGRESSIVE
    ) == Decimal("44.10")


# --- banded grid (price-dependent ticks) ------------------------------------


def test_banded_selects_correct_band() -> None:
    assert snap_price(Decimal("0.4567"), _banded(), side=OrderSide.BUY) == Decimal("0.457")
    assert snap_price(Decimal("5.123"), _banded(), side=OrderSide.BUY) == Decimal("5.125")
    assert snap_price(Decimal("42.834"), _banded(), side=OrderSide.BUY) == Decimal("42.83")


def test_band_edge_is_on_grid() -> None:
    assert snap_price(Decimal("10.00"), _banded(), side=OrderSide.BUY) == Decimal("10.00")


def test_unsorted_band_table_still_selects_correctly() -> None:
    grid = list(reversed(_banded()))
    assert snap_price(Decimal("5.123"), grid, side=OrderSide.BUY) == Decimal("5.125")


# --- guards -----------------------------------------------------------------


def test_nonpositive_price_raises() -> None:
    with pytest.raises(ValueError):
        snap_price(Decimal("0"), _flat("0.1"), side=OrderSide.BUY)


def test_empty_table_raises() -> None:
    with pytest.raises(ValueError):
        snap_price(Decimal("1"), [], side=OrderSide.BUY)
