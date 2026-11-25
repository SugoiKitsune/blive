"""Tests for :mod:`blive.adapters.ib.price_rules` (ADR-051 IB tick-grid source).

Mocks ``ib_async.IB``'s ``reqContractDetailsAsync`` / ``reqMarketRuleAsync``
to exercise: market-rule → banded table, ``minTick`` fallback, per-instrument
caching + ``clear_cache``, and the two block (``PriceRuleUnavailable``) paths.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import ib_async
import pytest

from blive.adapters.clock.sim import SimClock
from blive.adapters.ib.client import IBClient
from blive.adapters.ib.credentials import IBCredentials
from blive.adapters.ib.price_rules import IBPriceRuleService, PriceRuleUnavailable
from blive.adapters.shared.price_grid import PriceIncrement
from blive.adapters.shared.rate_limiter import (
    RateLimitBucket,
    RateLimitConfig,
    TokenBucketRateLimiter,
)
from blive.domain.types import AssetClass, Instrument


def _instrument() -> Instrument:
    return Instrument(
        symbol="QQL3",
        venue="XLON",
        currency="USD",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
    )


def _details(
    *,
    min_tick: float,
    market_rule_ids: str = "",
    valid_exchanges: str = "",
    primary_exchange: str = "LSEETF",
) -> ib_async.ContractDetails:
    cd = ib_async.ContractDetails()
    cd.minTick = min_tick
    cd.marketRuleIds = market_rule_ids
    cd.validExchanges = valid_exchanges
    cd.contract = ib_async.Contract(
        symbol="QQL3",
        secType="STK",
        exchange="SMART",
        primaryExchange=primary_exchange,
        currency="USD",
    )
    return cd


def _service(mock_ib: MagicMock) -> IBPriceRuleService:
    clock = SimClock(start=datetime(2026, 6, 5, 9, 0, 0, tzinfo=timezone.utc))
    rate_limiter = TokenBucketRateLimiter(
        clock=clock,
        config=RateLimitConfig(
            buckets={"global": RateLimitBucket(capacity=100, refill_per_second=Decimal("20"))}
        ),
    )
    client = IBClient(
        credentials=IBCredentials(host="127.0.0.1", port=4002, client_id=1, account_id="DUTEST"),
        rate_limiter=rate_limiter,
        clock=clock,
        ib=mock_ib,
    )
    return IBPriceRuleService(client)


async def test_market_rule_produces_banded_table() -> None:
    mock_ib = MagicMock(spec=ib_async.IB)
    mock_ib.reqContractDetailsAsync = AsyncMock(
        return_value=[_details(min_tick=0.01, market_rule_ids="26", valid_exchanges="LSEETF")]
    )
    mock_ib.reqMarketRuleAsync = AsyncMock(
        return_value=[ib_async.PriceIncrement(0.0, 0.05), ib_async.PriceIncrement(50.0, 0.10)]
    )
    svc = _service(mock_ib)

    table = await svc.increments_for(_instrument())

    assert list(table) == [
        PriceIncrement(Decimal("0"), Decimal("0.05")),
        PriceIncrement(Decimal("50"), Decimal("0.1")),
    ]


async def test_falls_back_to_min_tick_when_no_market_rule() -> None:
    mock_ib = MagicMock(spec=ib_async.IB)
    mock_ib.reqContractDetailsAsync = AsyncMock(
        return_value=[_details(min_tick=0.10, market_rule_ids="", valid_exchanges="")]
    )
    mock_ib.reqMarketRuleAsync = AsyncMock()
    svc = _service(mock_ib)

    table = await svc.increments_for(_instrument())

    assert list(table) == [PriceIncrement(Decimal("0"), Decimal("0.1"))]
    mock_ib.reqMarketRuleAsync.assert_not_called()


async def test_market_rule_failure_degrades_to_min_tick() -> None:
    mock_ib = MagicMock(spec=ib_async.IB)
    mock_ib.reqContractDetailsAsync = AsyncMock(
        return_value=[_details(min_tick=0.10, market_rule_ids="26", valid_exchanges="LSEETF")]
    )
    mock_ib.reqMarketRuleAsync = AsyncMock(side_effect=RuntimeError("wire boom"))
    svc = _service(mock_ib)

    table = await svc.increments_for(_instrument())

    assert list(table) == [PriceIncrement(Decimal("0"), Decimal("0.1"))]


async def test_caches_table_no_second_fetch() -> None:
    mock_ib = MagicMock(spec=ib_async.IB)
    mock_ib.reqContractDetailsAsync = AsyncMock(return_value=[_details(min_tick=0.10)])
    svc = _service(mock_ib)
    inst = _instrument()

    await svc.increments_for(inst)
    await svc.increments_for(inst)

    mock_ib.reqContractDetailsAsync.assert_called_once()


async def test_clear_cache_forces_refetch() -> None:
    mock_ib = MagicMock(spec=ib_async.IB)
    mock_ib.reqContractDetailsAsync = AsyncMock(return_value=[_details(min_tick=0.10)])
    svc = _service(mock_ib)
    inst = _instrument()

    await svc.increments_for(inst)
    svc.clear_cache(inst)
    await svc.increments_for(inst)

    assert mock_ib.reqContractDetailsAsync.call_count == 2


async def test_no_details_raises_price_rule_unavailable() -> None:
    mock_ib = MagicMock(spec=ib_async.IB)
    mock_ib.reqContractDetailsAsync = AsyncMock(return_value=[])
    svc = _service(mock_ib)

    with pytest.raises(PriceRuleUnavailable):
        await svc.increments_for(_instrument())


async def test_no_rule_and_no_min_tick_raises() -> None:
    mock_ib = MagicMock(spec=ib_async.IB)
    mock_ib.reqContractDetailsAsync = AsyncMock(
        return_value=[_details(min_tick=0.0, market_rule_ids="", valid_exchanges="")]
    )
    svc = _service(mock_ib)

    with pytest.raises(PriceRuleUnavailable):
        await svc.increments_for(_instrument())
