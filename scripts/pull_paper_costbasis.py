"""Pull the REAL execution prices for the paper account's open positions from IB.

IB carries each open position's actual blended fill price as ``averageCost`` (and its own
``unrealizedPNL``) — so for anything currently held we have the genuine entry price without Flex.
This prints entry (avgCost) vs mark and the real P&L per leg, and the account totals.

    uv run python scripts/pull_paper_costbasis.py
"""
from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, "src")

from blive.adapters.clock.wall import WallClock
from blive.adapters.ib import IB_DEFAULT_RATE_LIMITS, IBClient, IBCredentials, IBInstrumentResolver
from blive.adapters.ib.broker import IBBroker
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter


async def main() -> int:
    creds = IBCredentials.load()
    clock = WallClock()
    rl = TokenBucketRateLimiter(config=IB_DEFAULT_RATE_LIMITS, clock=clock)
    client = IBClient(credentials=creds, rate_limiter=rl, clock=clock)
    broker = IBBroker(client=client, resolver=IBInstrumentResolver(client), clock=clock)
    await broker.connect()
    portfolio = [it for it in client.ib.portfolio() if it.position]
    await broker.disconnect()

    print(f"{'symbol':10} {'ccy':4} {'qty':>8} {'avgCost':>12} {'mark':>10} "
          f"{'costBasis':>14} {'mktValue':>14} {'unrealPnL':>12}")
    tot_cost = tot_val = tot_pnl = 0.0
    for it in sorted(portfolio, key=lambda x: x.contract.symbol):
        c = it.contract
        qty = float(it.position)
        avg = float(it.averageCost)          # IB: blended fill price per share (contract ccy)
        mark = float(it.marketPrice)
        mv = float(it.marketValue)
        cost = avg * qty
        pnl = float(it.unrealizedPNL)
        tot_cost += cost; tot_val += mv; tot_pnl += pnl
        print(f"{c.symbol:10} {c.currency:4} {qty:>8.0f} {avg:>12.4f} {mark:>10.4f} "
              f"{cost:>14,.2f} {mv:>14,.2f} {pnl:>12,.2f}")
    print(f"\n  cost basis (mixed ccy): {tot_cost:,.2f}   mkt value: {tot_val:,.2f}   "
          f"unrealized PnL: {tot_pnl:,.2f}")
    print("  NOTE: avgCost = the REAL blended execution price IB recorded for each open lot.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
