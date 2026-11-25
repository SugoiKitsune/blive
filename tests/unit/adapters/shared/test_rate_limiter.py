"""Tests for :mod:`blive.adapters.shared.rate_limiter`.

Covers [ADR-031](../../../../../docs/decisions/DECISIONS.md#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters)
algorithm, [ADR-038](../../../../../docs/decisions/DECISIONS.md#adr-038--ig-rate-limit-defaults-parameterise-adr-031)
named-bucket parameterisation, and the [G3-IB throttle test](../../../../../TASK_REGISTRY.md)
("60 calls/sec → ≤ 20/sec sustained") + [G3-IG throttle test](../../../../../TASK_REGISTRY.md)
("100 calls/min → ≤ 30/min sustained") at unit scale via SimClock.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from blive.adapters.clock.sim import SimClock
from blive.adapters.shared.rate_limiter import (
    BucketMetrics,
    RateLimitBucket,
    RateLimitConfig,
    TokenBucketRateLimiter,
    UnknownBucket,
)

# --- Validation invariants ---------------------------------------------------


def test_rate_limit_bucket_rejects_zero_capacity() -> None:
    with pytest.raises(ValueError, match="capacity must be > 0"):
        RateLimitBucket(capacity=0, refill_per_second=Decimal("1"))


def test_rate_limit_bucket_rejects_negative_capacity() -> None:
    with pytest.raises(ValueError, match="capacity must be > 0"):
        RateLimitBucket(capacity=-5, refill_per_second=Decimal("1"))


def test_rate_limit_bucket_rejects_zero_refill() -> None:
    with pytest.raises(ValueError, match="refill_per_second must be > 0"):
        RateLimitBucket(capacity=10, refill_per_second=Decimal("0"))


def test_rate_limit_bucket_rejects_negative_refill() -> None:
    with pytest.raises(ValueError, match="refill_per_second must be > 0"):
        RateLimitBucket(capacity=10, refill_per_second=Decimal("-1"))


def test_rate_limit_config_rejects_empty_buckets() -> None:
    with pytest.raises(ValueError, match="at least one bucket"):
        RateLimitConfig(buckets={})


def test_rate_limit_config_rejects_empty_bucket_name() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        RateLimitConfig(buckets={"": RateLimitBucket(capacity=10, refill_per_second=Decimal("1"))})


# --- Single-bucket basic flow -----------------------------------------------


@pytest.fixture
def clock_2026() -> SimClock:
    return SimClock(start=datetime(2026, 4, 27, 13, 0, 0, tzinfo=timezone.utc))


@pytest.fixture
def ib_global_limiter(clock_2026: SimClock) -> TokenBucketRateLimiter:
    """IB-style global bucket: 20 capacity, 20/s refill (per ADR-031 §"Decision")."""
    config = RateLimitConfig(
        buckets={"global": RateLimitBucket(capacity=20, refill_per_second=Decimal("20"))}
    )
    return TokenBucketRateLimiter(config=config, clock=clock_2026)


@pytest.fixture
def ig_general_limiter(clock_2026: SimClock) -> TokenBucketRateLimiter:
    """IG-style general bucket: 30 capacity, 0.5/s refill (per ADR-038 §"Decision")."""
    config = RateLimitConfig(
        buckets={"general": RateLimitBucket(capacity=30, refill_per_second=Decimal("0.5"))}
    )
    return TokenBucketRateLimiter(config=config, clock=clock_2026)


async def test_acquire_immediate_when_capacity_available(
    ib_global_limiter: TokenBucketRateLimiter, clock_2026: SimClock
) -> None:
    """First acquire on a fresh bucket returns immediately without sleeping."""
    start = clock_2026.now()
    await ib_global_limiter.acquire("global")
    assert clock_2026.now() == start  # No time elapsed.
    metrics = ib_global_limiter.metrics()
    # One token consumed; no time has elapsed so no refill yet → 19/20.
    assert metrics["global"].available == Decimal("19")


async def test_acquire_unknown_bucket_raises(ib_global_limiter: TokenBucketRateLimiter) -> None:
    with pytest.raises(UnknownBucket) as excinfo:
        await ib_global_limiter.acquire("trading")
    assert excinfo.value.bucket == "trading"


async def test_acquire_zero_tokens_raises(ib_global_limiter: TokenBucketRateLimiter) -> None:
    with pytest.raises(ValueError, match=r"tokens\) must be > 0"):
        await ib_global_limiter.acquire("global", tokens=0)


async def test_acquire_negative_tokens_raises(ib_global_limiter: TokenBucketRateLimiter) -> None:
    with pytest.raises(ValueError, match=r"tokens\) must be > 0"):
        await ib_global_limiter.acquire("global", tokens=-1)


async def test_acquire_more_than_capacity_raises(
    ib_global_limiter: TokenBucketRateLimiter,
) -> None:
    with pytest.raises(ValueError, match="exceeds bucket capacity"):
        await ib_global_limiter.acquire("global", tokens=21)


# --- Refill semantics --------------------------------------------------------


async def test_acquire_blocks_when_bucket_empty(
    ib_global_limiter: TokenBucketRateLimiter, clock_2026: SimClock
) -> None:
    """After draining capacity, the next acquire waits for refill."""
    # Drain all 20 tokens; clock unchanged.
    for _ in range(20):
        await ib_global_limiter.acquire("global")
    assert clock_2026.now() == datetime(2026, 4, 27, 13, 0, 0, tzinfo=timezone.utc)
    assert ib_global_limiter.metrics()["global"].available < Decimal("1")

    # The 21st acquire must wait ~50 ms (one token refilling at 20/s).
    before = clock_2026.now()
    await ib_global_limiter.acquire("global")
    after = clock_2026.now()
    elapsed = (after - before).total_seconds()
    # Allow generous slack for the 1-µs cushion.
    assert 0.04 < elapsed < 0.06, f"expected ~0.05s wait for one-token refill, got {elapsed}"


async def test_acquire_blocks_for_burst(
    ib_global_limiter: TokenBucketRateLimiter, clock_2026: SimClock
) -> None:
    """Acquiring 5 tokens after draining requires ~250 ms (5 / 20 per second)."""
    for _ in range(20):
        await ib_global_limiter.acquire("global")

    before = clock_2026.now()
    await ib_global_limiter.acquire("global", tokens=5)
    after = clock_2026.now()
    elapsed = (after - before).total_seconds()
    assert 0.24 < elapsed < 0.26, f"expected ~0.25s for 5-token refill, got {elapsed}"


async def test_metrics_reflect_consumption_and_refill(
    ib_global_limiter: TokenBucketRateLimiter, clock_2026: SimClock
) -> None:
    # Drain 10 tokens; bucket should report 10 available.
    for _ in range(10):
        await ib_global_limiter.acquire("global")
    metrics = ib_global_limiter.metrics()["global"]
    assert metrics.available == Decimal("10")
    assert metrics.bucket == "global"
    assert metrics.capacity == 20
    assert metrics.refill_per_second == Decimal("20")

    # Advance 0.5 s; bucket should refill by 10 (capped at capacity 20).
    clock_2026.tick(0.5)
    metrics_after = ib_global_limiter.metrics()["global"]
    assert metrics_after.available == Decimal("20"), "should be capped at capacity"


async def test_refill_capped_at_capacity(
    ib_global_limiter: TokenBucketRateLimiter, clock_2026: SimClock
) -> None:
    """Long idle should not over-fill the bucket beyond capacity."""
    for _ in range(20):
        await ib_global_limiter.acquire("global")
    clock_2026.tick(60.0)  # Way more time than needed for refill (1200 tokens-worth at 20/s).
    metrics = ib_global_limiter.metrics()["global"]
    assert metrics.available == Decimal("20")  # Capped, not 1220.


# --- Multi-bucket independence -----------------------------------------------


async def test_multiple_buckets_independent(clock_2026: SimClock) -> None:
    """Two buckets refill / drain independently."""
    config = RateLimitConfig(
        buckets={
            "general": RateLimitBucket(capacity=30, refill_per_second=Decimal("0.5")),
            "trading": RateLimitBucket(capacity=60, refill_per_second=Decimal("1")),
        }
    )
    limiter = TokenBucketRateLimiter(config=config, clock=clock_2026)

    # Drain trading; general should still be at 30.
    for _ in range(60):
        await limiter.acquire("trading")
    metrics = limiter.metrics()
    assert metrics["trading"].available < Decimal("1")
    assert metrics["general"].available == Decimal("30")

    # Acquire from general — should be immediate, even though trading is empty.
    before = clock_2026.now()
    await limiter.acquire("general")
    assert clock_2026.now() == before


# --- Headline G3 / G3-IG throttle test ---------------------------------------


async def test_g3_ib_throttle_60_per_second_into_20_per_second_sustained(
    clock_2026: SimClock,
) -> None:
    """[ADR-031] G3 throttle test: 60 calls/sec sustained outflow ≤ 20/sec.

    The test simulates a strategy emitting 60 calls in one second; the
    limiter throttles them to the IB-default 20/s bucket. Verifies that
    completing 60 acquires takes at least ~2 seconds (since the bucket
    holds 20, refilling at 20/s; first 20 are immediate, the next 40 must
    wait for refills).
    """
    config = RateLimitConfig(
        buckets={"global": RateLimitBucket(capacity=20, refill_per_second=Decimal("20"))}
    )
    limiter = TokenBucketRateLimiter(config=config, clock=clock_2026)

    start = clock_2026.now()
    for _ in range(60):
        await limiter.acquire("global")
    elapsed = (clock_2026.now() - start).total_seconds()

    # 60 acquires at 20/s sustained refill: first 20 immediate (capacity),
    # next 40 paced one-by-one. Strictly: 40 / 20 = 2.0 s minimum.
    assert elapsed >= 2.0, f"expected ≥ 2.0s for 60 acquires at 20/s, got {elapsed}"
    # Under perfect refill the bound is tight; allow small cushion.
    assert elapsed < 2.05, f"expected < 2.05s (no over-throttle), got {elapsed}"


async def test_g3_ig_throttle_100_per_minute_into_30_per_minute_sustained(
    clock_2026: SimClock,
) -> None:
    """[ADR-038] G3-IG throttle test: 100 calls/min sustained outflow ≤ 30/min.

    Simulates the IG `general` bucket (30 capacity, 0.5/s = 30/min refill);
    100 acquires must take at least 140 s (first 30 immediate, next 70 at
    0.5/s = 140 s).
    """
    config = RateLimitConfig(
        buckets={"general": RateLimitBucket(capacity=30, refill_per_second=Decimal("0.5"))}
    )
    limiter = TokenBucketRateLimiter(config=config, clock=clock_2026)

    start = clock_2026.now()
    for _ in range(100):
        await limiter.acquire("general")
    elapsed = (clock_2026.now() - start).total_seconds()

    # First 30 immediate (capacity), next 70 paced at 0.5/s: 70 / 0.5 = 140 s.
    assert elapsed >= 140.0, f"expected ≥ 140s for 100 acquires at 30/min, got {elapsed}"
    assert elapsed < 141.0, f"expected < 141s (no over-throttle), got {elapsed}"


async def test_metrics_returns_snapshot_with_all_buckets(clock_2026: SimClock) -> None:
    """`metrics()` returns one entry per bucket with correct identity fields."""
    config = RateLimitConfig(
        buckets={
            "general": RateLimitBucket(capacity=30, refill_per_second=Decimal("0.5")),
            "trading": RateLimitBucket(capacity=60, refill_per_second=Decimal("1")),
            "historical_prices": RateLimitBucket(
                capacity=40, refill_per_second=Decimal("0.6666666666666666")
            ),
        }
    )
    limiter = TokenBucketRateLimiter(config=config, clock=clock_2026)
    metrics = limiter.metrics()
    assert set(metrics.keys()) == {"general", "trading", "historical_prices"}
    for name, m in metrics.items():
        assert isinstance(m, BucketMetrics)
        assert m.bucket == name
        assert m.available == Decimal(config.buckets[name].capacity)
