"""Broker-agnostic token-bucket rate limiter.

Implements the algorithm from [ADR-031](../../../../docs/decisions/DECISIONS.md#adr-031--token-bucket-rate-limiter-shape-for-ib-adapters),
generalised per [ADR-034](../../../../docs/decisions/DECISIONS.md#adr-034--multi-broker-registry-pattern-extends-adr-004)
to live in the cross-broker shared package, and parameterised per
[ADR-038](../../../../docs/decisions/DECISIONS.md#adr-038--ig-rate-limit-defaults-parameterise-adr-031)
with named buckets.

A `TokenBucketRateLimiter` holds one bucket per declared name. Each call site
declares which bucket it draws from via :meth:`acquire`. Tokens refill linearly
with elapsed wall-clock time; capacity is the ceiling. ``acquire`` blocks (via
``ClockPort.sleep``) until enough tokens are available — back-pressure flows
through asyncio. Tests use :class:`blive.adapters.clock.sim.SimClock` for
deterministic time advancement.

The limiter does **not** model per-strategy sub-buckets at this stage; per-
[INV-4 RC-05/RC-06](../../../../docs/inv/risk_checks.md) those land at M4 alongside
the full RiskEngine. Callers that need per-strategy enforcement at M2 can
register dynamic buckets keyed by ``f"strategy_{strategy_id}"`` if needed.

Concurrent-budget resources (e.g. the IG Lightstreamer subscription cap per
[ADR-038](../../../../docs/decisions/DECISIONS.md#adr-038--ig-rate-limit-defaults-parameterise-adr-031)
§"Decision") are **not** modelled here — they're enforced as semaphores
inside the relevant adapter (e.g. ``IGMarketData``). The token-bucket
algorithm only handles refilling buckets.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Mapping

from blive.domain.ports import ClockPort

# --- Public dataclasses ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RateLimitBucket:
    """Configuration for one named bucket."""

    capacity: int
    """Max tokens the bucket holds. Must be strictly positive."""

    refill_per_second: Decimal
    """Tokens added per second of elapsed time. Must be strictly positive."""

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError(f"RateLimitBucket.capacity must be > 0, got {self.capacity}")
        if self.refill_per_second <= 0:
            raise ValueError(
                f"RateLimitBucket.refill_per_second must be > 0, got {self.refill_per_second}"
            )


@dataclass(frozen=True, slots=True)
class RateLimitConfig:
    """A complete bucket table for a rate limiter instance."""

    buckets: Mapping[str, RateLimitBucket]

    def __post_init__(self) -> None:
        if not self.buckets:
            raise ValueError("RateLimitConfig.buckets must declare at least one bucket")
        for name in self.buckets:
            if not name:
                raise ValueError("RateLimitConfig bucket names must be non-empty")


@dataclass(frozen=True, slots=True)
class BucketMetrics:
    """Snapshot of one bucket's state. Returned by :meth:`TokenBucketRateLimiter.metrics`."""

    bucket: str
    available: Decimal
    capacity: int
    refill_per_second: Decimal
    last_refill_utc: datetime


class UnknownBucket(KeyError):
    """Raised by :meth:`TokenBucketRateLimiter.acquire` when the bucket name is not registered."""

    def __init__(self, bucket: str) -> None:
        self.bucket = bucket
        super().__init__(f"unknown rate-limit bucket: {bucket!r}")


# --- The limiter -------------------------------------------------------------


class TokenBucketRateLimiter:
    """Two-mode token-bucket rate limiter with N independent named buckets.

    See module docstring for design context. Public methods:

    - :meth:`acquire` (async) — block until ``tokens`` are available in
      the named bucket, then consume them.
    - :meth:`metrics` — non-blocking snapshot of all buckets for
      observability ([REQUIREMENTS §5.9](../../../../REQUIREMENTS.md):
      Prometheus gauges).
    """

    def __init__(
        self,
        *,
        config: RateLimitConfig,
        clock: ClockPort,
    ) -> None:
        self._config = config
        self._clock = clock
        now = clock.now()
        self._available: dict[str, Decimal] = {
            name: Decimal(bucket.capacity) for name, bucket in config.buckets.items()
        }
        self._last_refill: dict[str, datetime] = {name: now for name in config.buckets}

    # --- Public surface -----------------------------------------------------

    async def acquire(self, bucket: str, tokens: int = 1) -> None:
        """Block until ``tokens`` are available in the named bucket; consume them.

        Raises :class:`UnknownBucket` if ``bucket`` is not in the config;
        :class:`ValueError` if ``tokens`` is non-positive or exceeds the
        bucket's capacity (an unreachable acquire — no amount of waiting
        would refill enough).
        """
        if bucket not in self._config.buckets:
            raise UnknownBucket(bucket)
        if tokens <= 0:
            raise ValueError(f"acquire(tokens) must be > 0, got {tokens}")
        bucket_cfg = self._config.buckets[bucket]
        if tokens > bucket_cfg.capacity:
            raise ValueError(
                f"acquire(bucket={bucket!r}, tokens={tokens}) exceeds bucket capacity "
                f"{bucket_cfg.capacity}; no amount of waiting can satisfy this request"
            )

        while True:
            now = self._clock.now()
            self._refill(bucket, now)
            if self._available[bucket] >= Decimal(tokens):
                self._available[bucket] -= Decimal(tokens)
                return
            deficit = Decimal(tokens) - self._available[bucket]
            wait_seconds = float(deficit / bucket_cfg.refill_per_second)
            # Round up tiny floating-point overshoots so the next refill
            # delivers at least the deficit. Using a 1-microsecond cushion
            # avoids a worst-case re-loop with sub-femtosecond residual.
            await self._clock.sleep(wait_seconds + 1e-6)

    def metrics(self) -> Mapping[str, BucketMetrics]:
        """Return a snapshot of all bucket states (after refilling to current time)."""
        now = self._clock.now()
        out: dict[str, BucketMetrics] = {}
        for name, bucket_cfg in self._config.buckets.items():
            self._refill(name, now)
            out[name] = BucketMetrics(
                bucket=name,
                available=self._available[name],
                capacity=bucket_cfg.capacity,
                refill_per_second=bucket_cfg.refill_per_second,
                last_refill_utc=self._last_refill[name],
            )
        return out

    # --- Internals ----------------------------------------------------------

    def _refill(self, bucket: str, now: datetime) -> None:
        bucket_cfg = self._config.buckets[bucket]
        last = self._last_refill[bucket]
        elapsed = (now - last).total_seconds()
        if elapsed <= 0:
            return
        added = bucket_cfg.refill_per_second * Decimal(str(elapsed))
        self._available[bucket] = min(
            Decimal(bucket_cfg.capacity),
            self._available[bucket] + added,
        )
        self._last_refill[bucket] = now


__all__ = [
    "BucketMetrics",
    "RateLimitBucket",
    "RateLimitConfig",
    "TokenBucketRateLimiter",
    "UnknownBucket",
]
