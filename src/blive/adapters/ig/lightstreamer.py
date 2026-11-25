"""Lightstreamer source abstraction.

Per [ADR-036](../../../../docs/decisions/DECISIONS.md#adr-036--ig-wire-level-driver-roll-our-own-httpx--asyncio-lightstreamer)
the IG streaming half uses Lightstreamer over HTTP. ``lightstreamer-client-lib``
is the official IG-recommended package (added as a runtime dep at M2-IG.3
follow-up); however its public surface is callback-driven (Java/JS style)
which fights blive's single-asyncio-loop kernel ([ADR-005](../../../../docs/decisions/DECISIONS.md#adr-005--single-process-single-asyncio-loop-kernel-for-v1)).

This module declares the **abstraction blive consumes** —
:class:`LightstreamerSource` and :class:`LightstreamerSubscription` —
so :class:`blive.adapters.ig.market_data.IGMarketData` can be unit-tested
against a fake source without spinning up a real Lightstreamer connection.
The production wrapper (``RealLightstreamerSource`` adapting
``lightstreamer.client.LightstreamerClient`` via a threading→asyncio bridge)
lands in a follow-up commit when the operator's IG demo credentials are
placed at ``~/.blive/secrets/ig.env`` and the live handshake confirms the
exact subscription parameters.

Concrete API the consumer expects:

```python
async with source.subscribe(item="CHART:IX.D.CAC40.CASH.IP:1MINUTE",
                             fields=["BID_CLOSE", ...],
                             mode="MERGE") as sub:
    async for update in sub.updates():
        # update is a dict[str, str | None] of changed fields
        ...
```

Per [KB-17 §3](../../../../docs/kb/ig_pacing_spec.md#3-lightstreamer-subscription-budget)
the IG account has a concurrent-subscription budget (~40 items); the
:class:`IGMarketData` enforces it via :class:`asyncio.Semaphore` outside
this module — sources don't need to know.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import AsyncIterator, Mapping, Protocol, runtime_checkable

# --- Public types -----------------------------------------------------------


@runtime_checkable
class LightstreamerSubscription(Protocol):
    """A single live Lightstreamer subscription.

    Yielded by :meth:`LightstreamerSource.subscribe`. The ``updates``
    method returns an async iterator of field-update dicts.
    """

    @property
    def item(self) -> str: ...

    @property
    def fields(self) -> tuple[str, ...]: ...

    def updates(self) -> AsyncIterator[Mapping[str, str | None]]: ...


@runtime_checkable
class LightstreamerSource(Protocol):
    """The transport abstraction `IGMarketData` consumes.

    Production implementation wraps ``lightstreamer-client-lib`` via a
    threading→asyncio bridge; tests use :class:`FakeLightstreamerSource`.
    """

    async def connect(self) -> None: ...

    async def disconnect(self) -> None: ...

    async def subscribe(
        self,
        *,
        item: str,
        fields: tuple[str, ...],
        mode: str = "MERGE",
    ) -> LightstreamerSubscription: ...

    async def unsubscribe(self, subscription: LightstreamerSubscription) -> None: ...


# --- Fake source for tests --------------------------------------------------


@dataclass
class _FakeSubscription:
    """In-memory subscription used by :class:`FakeLightstreamerSource`."""

    item: str
    fields: tuple[str, ...]
    mode: str
    _queue: asyncio.Queue[Mapping[str, str | None] | None] = field(default_factory=asyncio.Queue)
    _closed: bool = False

    def push(self, update: Mapping[str, str | None]) -> None:
        """Test-side: deliver a field-update to the consumer's iterator."""
        if self._closed:
            raise RuntimeError(f"FakeSubscription({self.item!r}) is closed")
        self._queue.put_nowait(dict(update))

    def close(self) -> None:
        """Test-side: signal end-of-stream by sending a sentinel."""
        if not self._closed:
            self._closed = True
            self._queue.put_nowait(None)

    async def updates(self) -> AsyncIterator[Mapping[str, str | None]]:
        while True:
            update = await self._queue.get()
            if update is None:
                return
            yield update


class FakeLightstreamerSource:
    """A pure in-memory :class:`LightstreamerSource` for unit tests.

    Supports the full Protocol surface; tracks active subscriptions so
    tests can verify subscribe/unsubscribe accounting without a real
    Lightstreamer server.
    """

    def __init__(self) -> None:
        self._subscriptions: list[_FakeSubscription] = []
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def subscriptions(self) -> tuple[_FakeSubscription, ...]:
        """Test-side accessor for inspection."""
        return tuple(self._subscriptions)

    def subscription_for(self, item: str) -> _FakeSubscription:
        """Test-side helper: return the active subscription for an item.

        Raises :class:`KeyError` if no active subscription matches.
        """
        for sub in self._subscriptions:
            if sub.item == item:
                return sub
        raise KeyError(f"no active FakeSubscription for item={item!r}")

    # --- LightstreamerSource Protocol ---------------------------------------

    async def connect(self) -> None:
        if self._connected:
            return
        self._connected = True

    async def disconnect(self) -> None:
        for sub in list(self._subscriptions):
            sub.close()
        self._subscriptions.clear()
        self._connected = False

    async def subscribe(
        self,
        *,
        item: str,
        fields: tuple[str, ...],
        mode: str = "MERGE",
    ) -> LightstreamerSubscription:
        if not self._connected:
            raise RuntimeError("FakeLightstreamerSource.subscribe before connect()")
        sub = _FakeSubscription(item=item, fields=fields, mode=mode)
        self._subscriptions.append(sub)
        return sub

    async def unsubscribe(self, subscription: LightstreamerSubscription) -> None:
        for sub in list(self._subscriptions):
            if sub is subscription:
                sub.close()
                self._subscriptions.remove(sub)
                return


__all__ = [
    "FakeLightstreamerSource",
    "LightstreamerSource",
    "LightstreamerSubscription",
]
