"""Tests for the :mod:`blive.adapters.ig.lightstreamer` abstraction.

These exercise the :class:`FakeLightstreamerSource` which both provides
test infrastructure for downstream :class:`IGMarketData` tests AND
self-tests the Protocol shape — if the fake matches the
:class:`LightstreamerSource` Protocol cleanly, then any test using the
fake is implicitly testing the contract `IGMarketData` consumes.

The production wrapper around ``lightstreamer-client-lib`` is a
follow-up commit and gets its own integration tests against IG demo
when the operator's credentials are wired.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from blive.adapters.ig.lightstreamer import (
    FakeLightstreamerSource,
    LightstreamerSource,
    LightstreamerSubscription,
)

# --- Protocol conformance ---------------------------------------------------


def test_fake_source_satisfies_lightstreamer_source_protocol() -> None:
    """The fake must satisfy the Protocol so production substitution works."""
    source = FakeLightstreamerSource()
    assert isinstance(source, LightstreamerSource)


# --- Lifecycle --------------------------------------------------------------


async def test_connect_disconnect_lifecycle() -> None:
    source = FakeLightstreamerSource()
    assert source.is_connected is False
    await source.connect()
    assert source.is_connected is True
    await source.disconnect()
    assert source.is_connected is False


async def test_connect_idempotent() -> None:
    source = FakeLightstreamerSource()
    await source.connect()
    await source.connect()
    assert source.is_connected is True


async def test_subscribe_before_connect_raises() -> None:
    source = FakeLightstreamerSource()
    with pytest.raises(RuntimeError, match="before connect"):
        await source.subscribe(item="ANY", fields=("A",))


# --- Subscribe / push / iterate --------------------------------------------


async def test_subscribe_yields_pushed_updates() -> None:
    source = FakeLightstreamerSource()
    await source.connect()
    sub = await source.subscribe(item="CHART:IX.D.CAC40.CASH.IP:1MINUTE", fields=("BID_CLOSE",))
    assert isinstance(sub, LightstreamerSubscription)

    fake_sub = source.subscription_for("CHART:IX.D.CAC40.CASH.IP:1MINUTE")
    fake_sub.push({"BID_CLOSE": "7000.0"})
    fake_sub.push({"BID_CLOSE": "7050.0"})
    fake_sub.close()

    received: list[Any] = []
    async for update in sub.updates():
        received.append(update)
    assert received == [{"BID_CLOSE": "7000.0"}, {"BID_CLOSE": "7050.0"}]


async def test_subscription_carries_item_and_fields_metadata() -> None:
    source = FakeLightstreamerSource()
    await source.connect()
    sub = await source.subscribe(
        item="CHART:IX.D.CAC40.CASH.IP:1MINUTE",
        fields=("BID_CLOSE", "OFR_CLOSE", "CONS_END"),
        mode="MERGE",
    )
    assert sub.item == "CHART:IX.D.CAC40.CASH.IP:1MINUTE"
    assert sub.fields == ("BID_CLOSE", "OFR_CLOSE", "CONS_END")


async def test_multiple_subscriptions_independent() -> None:
    source = FakeLightstreamerSource()
    await source.connect()
    sub_a = await source.subscribe(item="CHART:A:1MINUTE", fields=("BID_CLOSE",))
    sub_b = await source.subscribe(item="CHART:B:1MINUTE", fields=("BID_CLOSE",))

    source.subscription_for("CHART:A:1MINUTE").push({"BID_CLOSE": "1.0"})
    source.subscription_for("CHART:B:1MINUTE").push({"BID_CLOSE": "2.0"})
    source.subscription_for("CHART:A:1MINUTE").close()
    source.subscription_for("CHART:B:1MINUTE").close()

    a_updates = [u async for u in sub_a.updates()]
    b_updates = [u async for u in sub_b.updates()]
    assert a_updates == [{"BID_CLOSE": "1.0"}]
    assert b_updates == [{"BID_CLOSE": "2.0"}]


# --- Unsubscribe / disconnect ----------------------------------------------


async def test_unsubscribe_removes_from_active_set_and_closes_stream() -> None:
    source = FakeLightstreamerSource()
    await source.connect()
    sub = await source.subscribe(item="CHART:X:1MINUTE", fields=("A",))
    assert len(source.subscriptions) == 1

    await source.unsubscribe(sub)
    assert len(source.subscriptions) == 0

    # The subscription's stream should now end.
    received = [u async for u in sub.updates()]
    assert received == []


async def test_disconnect_closes_all_subscriptions() -> None:
    source = FakeLightstreamerSource()
    await source.connect()
    sub_a = await source.subscribe(item="CHART:A:1MINUTE", fields=("X",))
    sub_b = await source.subscribe(item="CHART:B:1MINUTE", fields=("X",))
    assert len(source.subscriptions) == 2

    await source.disconnect()
    assert len(source.subscriptions) == 0

    a = [u async for u in sub_a.updates()]
    b = [u async for u in sub_b.updates()]
    assert a == [] and b == []


async def test_push_after_close_raises() -> None:
    source = FakeLightstreamerSource()
    await source.connect()
    await source.subscribe(item="CHART:Z:1MINUTE", fields=("X",))
    fake_sub = source.subscription_for("CHART:Z:1MINUTE")
    fake_sub.close()
    with pytest.raises(RuntimeError, match="closed"):
        fake_sub.push({"X": "1"})


async def test_subscription_for_missing_item_raises_key_error() -> None:
    source = FakeLightstreamerSource()
    await source.connect()
    with pytest.raises(KeyError, match="no active FakeSubscription"):
        source.subscription_for("CHART:NONEXISTENT:1MINUTE")


# --- Concurrent push + iterate (deterministic; no thread races) ------------


async def test_iterator_blocks_until_push() -> None:
    """Update iterator yields control back to the event loop while waiting,
    then resumes when push() lands a new update."""
    source = FakeLightstreamerSource()
    await source.connect()
    sub = await source.subscribe(item="CHART:X:1MINUTE", fields=("V",))
    received: list[Any] = []

    async def consumer() -> None:
        async for update in sub.updates():
            received.append(update)

    consumer_task = asyncio.create_task(consumer())
    # Yield once so the consumer reaches the queue.get()
    await asyncio.sleep(0)
    assert received == []  # blocked on get
    source.subscription_for("CHART:X:1MINUTE").push({"V": "1"})
    await asyncio.sleep(0)
    source.subscription_for("CHART:X:1MINUTE").push({"V": "2"})
    source.subscription_for("CHART:X:1MINUTE").close()
    await consumer_task
    assert received == [{"V": "1"}, {"V": "2"}]
