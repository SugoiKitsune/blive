"""Journal the paper account's REAL fills from IB into the shared trades feed.

blive submits orders but never recorded what filled — so there was no trade journal, and IB's API only
keeps ~24h of executions. This closes that gap: run it daily (STAGE 4 / run_daily --feeds) and it appends
any new fills (real price, commission, realized P&L) to ``trades_paper.csv``, de-duped by IB execId. Over
time that builds the true ledger — including rotations (closed lots) that ``averageCost`` alone can't show.

    uv run python scripts/pull_paper_fills.py

Note: only captures fills from the last ~24h (IB limit), so it must run within a day of each execution;
it can't recover fills older than that (those need a Flex Trades query). Idempotent — re-running is safe.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, "src")

from ib_async import ExecutionFilter

from blive.adapters.clock.wall import WallClock
from blive.adapters.ib import IB_DEFAULT_RATE_LIMITS, IBClient, IBCredentials, IBInstrumentResolver
from blive.adapters.ib.broker import IBBroker
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter

_TRADES = Path(__file__).resolve().parents[2] / "lab" / "reporting" / "nav" / "trades_paper.csv"


async def main() -> int:
    creds = IBCredentials.load()
    clock = WallClock()
    rl = TokenBucketRateLimiter(config=IB_DEFAULT_RATE_LIMITS, clock=clock)
    client = IBClient(credentials=creds, rate_limiter=rl, clock=clock)
    broker = IBBroker(client=client, resolver=IBInstrumentResolver(client), clock=clock)
    await broker.connect()
    fills = await client.ib.reqExecutionsAsync(ExecutionFilter())   # all fills, last ~24h, this account
    await broker.disconnect()

    book = f"PAPER:{creds.account_id}"
    rows = []
    for f in fills:
        ex, cr, c = f.execution, f.commissionReport, f.contract
        signed = float(ex.shares) * (1.0 if str(ex.side).upper().startswith("B") else -1.0)
        rows.append({
            "date": str(ex.time)[:10], "book": book, "symbol": c.symbol,
            "quantity": signed, "price": float(ex.price),
            "commission": round(float(getattr(cr, "commission", 0.0) or 0.0), 4),
            "side": str(ex.side), "proceeds": round(-signed * float(ex.price), 2),
            "realized_pnl": round(float(getattr(cr, "realizedPNL", 0.0) or 0.0), 2),
            "trade_id": ex.execId, "ccy": c.currency or "", "source": "ib"})

    df = pd.read_csv(_TRADES) if _TRADES.is_file() else pd.DataFrame()
    df = df[df.get("source", pd.Series(dtype=str)) != "SYNTH"] if not df.empty else df  # purge synthetic
    known = set(df["trade_id"].astype(str)) if "trade_id" in df.columns and not df.empty else set()
    fresh = [r for r in rows if r["trade_id"] not in known]
    if fresh:
        df = pd.concat([df, pd.DataFrame(fresh)], ignore_index=True)
        df = df.sort_values(["date", "symbol"]).reset_index(drop=True)
        df.to_csv(_TRADES, index=False)

    print(f"pulled {len(rows)} fill(s) from IB; {len(fresh)} new -> {_TRADES}")
    for r in fresh:
        print(f"    {r['date']} {r['symbol']:8} {r['side']:4} {r['quantity']:>8.0f} @ {r['price']:>10.4f} "
              f"{r['ccy']}  comm={r['commission']}")
    if not rows:
        print("  (no executions in IB's ~24h window — nothing to journal right now)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
