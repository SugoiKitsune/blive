"""IB disconnect/reconnect chaos drill (M3.5).

A controlled substitute for observing the daily 23:45 ET TWS restart
([ADR-040](../docs/decisions/DECISIONS.md)): connect to IB Paper, baseline the
positions, then monitor the connection for a fixed window while the operator
manually **STOPS** and then **RESTARTS** the IB Gateway. Each poll prints the
broker's cached flag against the real socket state; on a detected drop the drill
attempts recovery and re-fetches positions to reconcile against the baseline.

The drill OBSERVES + CATALOGUES blive's actual behaviour for KB-7
(`failure_modes`) — it is not a clean-pass assertion. The IB broker has **no**
``disconnectedEvent`` handler and **no** native auto-reconnect (continuous
reconciliation is M5 per [REQUIREMENTS §5.7](../REQUIREMENTS.md)), so:

- ``broker.is_connected`` (a cached bool) stays **stale-True** on an unexpected
  drop, while ``IBClient.is_connected`` (→ ``ib.isConnected()``) reflects the
  real socket;
- ``broker.connect()`` is a no-op while that cached flag is stale, so recovery
  must ``disconnect()`` first to reset it, then ``connect()``.

The recovery loop here is therefore an **external watchdog** standing in for
what M5 will move into the adapter. Read-only w.r.t. orders; no RTH needed.

Run, then stop + restart the Gateway during the window:

    <venv python> scripts/probe_ib_reconnect.py --window-seconds 180
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone

from blive.adapters.clock.wall import WallClock
from blive.adapters.ib import (
    IB_DEFAULT_RATE_LIMITS,
    IBClient,
    IBConnectionError,
    IBCredentials,
)
from blive.adapters.ib.broker import IBBroker, IBShapeError
from blive.adapters.ib.instrument_resolver import IBInstrumentResolver
from blive.adapters.shared.credentials import CredentialsMissing
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter
from blive.domain.types import Position


def _ts() -> str:
    return datetime.now(tz=timezone.utc).strftime("%H:%M:%S")


def _positions_key(positions: list[Position]) -> set[tuple[str, str]]:
    return {(p.instrument.symbol, str(p.quantity)) for p in positions}


async def _snapshot_positions(broker: IBBroker) -> set[tuple[str, str]]:
    try:
        positions = await broker.positions()
    except (IBShapeError, RuntimeError) as exc:
        print(f"    positions() failed: {exc}")
        return set()
    return _positions_key(positions)


async def _attempt_recovery(broker: IBBroker) -> bool:
    # broker.connect() is a no-op while the cached _connected flag is stale-True
    # (no disconnectedEvent handler — the M3.5 finding), so reset it via
    # disconnect() first, then connect().
    try:
        await broker.disconnect()
    except Exception as exc:  # noqa: BLE001 — best-effort on a dead socket
        print(f"    disconnect() during recovery raised (expected on a dead socket): {exc}")
    try:
        await asyncio.wait_for(broker.connect(), timeout=10.0)
        return True
    except Exception as exc:  # noqa: BLE001 — Gateway down / clientId-in-use transient
        print(f"    reconnect attempt failed (Gateway likely still down): {exc}")
        return False


async def _run(window_seconds: int, poll_seconds: int) -> int:
    try:
        credentials = IBCredentials.load()
    except (CredentialsMissing, ValueError) as exc:
        print(f"FAILED loading credentials: {exc}")
        return 2

    clock = WallClock()
    rate_limiter = TokenBucketRateLimiter(config=IB_DEFAULT_RATE_LIMITS, clock=clock)
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock)
    resolver = IBInstrumentResolver(client)
    broker = IBBroker(client=client, resolver=resolver, clock=clock)

    print(f"[{_ts()}] connecting to {credentials.host}:{credentials.port} ...")
    try:
        await broker.connect()
    except IBConnectionError as exc:
        print(f"FAILED on connect: {exc}")
        return 3

    baseline = await _snapshot_positions(broker)
    print(
        f"[{_ts()}] connected; broker.is_connected={broker.is_connected} "
        f"socket={client.is_connected}; baseline positions={sorted(baseline)}"
    )
    print(
        f"\n>>> Now STOP the IB Gateway, then RESTART it within the next "
        f"{window_seconds}s. <<<\n"
    )

    dropped = False
    recovered = False
    reconciled: bool | None = None
    iterations = max(1, window_seconds // poll_seconds)
    for i in range(iterations):
        await asyncio.sleep(poll_seconds)
        socket_up = client.is_connected
        cached = broker.is_connected
        print(
            f"[{_ts()}] poll {i + 1}/{iterations}: "
            f"broker.is_connected={cached} socket(ib.isConnected)={socket_up}"
        )
        if not socket_up:
            if not dropped:
                dropped = True
                stale = "STALE — no disconnectedEvent handler" if cached else "flag also cleared"
                print(f"    >>> DROP detected. broker.is_connected={cached} ({stale}).")
            print("    attempting recovery (disconnect()+connect())...")
            if await _attempt_recovery(broker):
                recovered = True
                after = await _snapshot_positions(broker)
                reconciled = after == baseline
                pos_msg = (
                    "positions reconcile with baseline (OK)"
                    if reconciled
                    else f"positions CHANGED: {sorted(after)}"
                )
                print(
                    f"[{_ts()}]    RECONNECTED. "
                    f"broker.is_connected={broker.is_connected}; {pos_msg}"
                )
        elif dropped and recovered:
            print("    stable after recovery — ending drill early.")
            break

    print("\n=== drill summary ===")
    print(f"  drop observed:        {dropped}")
    print(f"  recovered:            {recovered}")
    print(f"  positions reconciled: {reconciled}")
    print(
        "  note: recovery used an EXTERNAL disconnect()+connect() loop; the IB "
        "broker has no native disconnectedEvent handler / auto-reconnect "
        "(M5 / REQUIREMENTS §5.7). Catalogued in KB-7."
    )
    try:
        await broker.disconnect()
    except Exception as exc:  # noqa: BLE001 — best-effort teardown
        print(f"  final disconnect() raised (suppressed): {exc}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="IB disconnect/reconnect chaos drill (M3.5)")
    parser.add_argument("--window-seconds", type=int, default=180)
    parser.add_argument("--poll-seconds", type=int, default=5)
    args = parser.parse_args()
    try:
        return asyncio.run(_run(args.window_seconds, args.poll_seconds))
    except KeyboardInterrupt:
        print("\nINTERRUPTED.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
