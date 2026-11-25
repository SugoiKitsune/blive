"""IB mixed-currency account-value dump (M3.4 diagnostic).

Connects to IB Paper and prints the raw per-currency account-value rows that
``IBBroker._build_account_snapshot`` consumes — ``NetLiquidationByCurrency``,
``TotalCashBalance``, ``GrossPositionValue``, ``MaintMarginReq``,
``ExchangeRate`` — for every currency incl. the ``BASE`` aggregate, so the
mixed-currency reconciliation can be checked against ``AccountSnapshot``.

Read-only; safe to run any time the Gateway is up (no RTH needed). Used to
confirm the M3.4 finding that ``AccountSnapshot.equity`` reads the
base-currency *sleeve* rather than the consolidated ``BASE`` total.

Run:

    <venv python> scripts/probe_ib_account_ccy.py
"""

from __future__ import annotations

import asyncio
import sys

from blive.adapters.clock.wall import WallClock
from blive.adapters.ib import (
    IB_DEFAULT_RATE_LIMITS,
    IBClient,
    IBConnectionError,
    IBCredentials,
)
from blive.adapters.shared.credentials import CredentialsMissing
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter

_TAGS = {
    "AccountCurrency",
    "NetLiquidation",
    "NetLiquidationByCurrency",
    "TotalCashBalance",
    "CashBalance",
    "GrossPositionValue",
    "MaintMarginReq",
    "BuyingPower",
    "ExchangeRate",
}


async def _run() -> int:
    try:
        credentials = IBCredentials.load()
    except (CredentialsMissing, ValueError) as exc:
        print(f"FAILED loading credentials: {exc}")
        return 2

    clock = WallClock()
    rate_limiter = TokenBucketRateLimiter(config=IB_DEFAULT_RATE_LIMITS, clock=clock)
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock)

    print(f"connecting to {credentials.host}:{credentials.port} client_id={credentials.client_id}")
    try:
        await client.connect()
    except IBConnectionError as exc:
        print(f"FAILED on connect: {exc}")
        return 3

    # The initial reqAccountUpdates batch is awaited inside connect(); give a
    # short beat for any trailing currency rows to land.
    await asyncio.sleep(0.5)

    account = credentials.account_id
    rows = client.ib.accountValues(account)
    by_tag: dict[str, list[tuple[str, str]]] = {}
    for av in rows:
        if av.tag in _TAGS:
            by_tag.setdefault(av.tag, []).append((av.currency or "(none)", av.value))

    print(f"=== raw account values (account {account[:4]}..., relevant tags) ===")
    for tag in sorted(by_tag):
        print(f"  {tag}:")
        for ccy, value in sorted(by_tag[tag]):
            print(f"      {ccy:>6} = {value}")

    await client.disconnect()
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except KeyboardInterrupt:
        print("\nINTERRUPTED.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
