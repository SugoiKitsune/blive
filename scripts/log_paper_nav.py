"""Snapshot the IB paper account NAV into the shared NAV feed.

Writes one row per (book, date) into ``derived_data/nav/paper_nav.csv`` per the
contract in ``derived_data/nav/README.md``. Run daily (idempotent — re-running
the same day overwrites that day's row). This is blive's half of the
theoretical-vs-paper-vs-actual reconciliation: it publishes the *paper* NAV feed;
lab computes *theoretical*; ForgeFolio will publish *actual*.

    uv run python scripts/log_paper_nav.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date

import pandas as pd

sys.path.insert(0, "src")

from pathlib import Path

from blive.adapters.clock.wall import WallClock
from blive.adapters.ib import IB_DEFAULT_RATE_LIMITS, IBClient, IBCredentials, IBInstrumentResolver
from blive.adapters.ib.broker import IBBroker
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter

_NAVDIR = Path(__file__).resolve().parents[2] / "lab" / "reporting" / "nav"
_FEED = _NAVDIR / "paper_nav.csv"
_POSFEED = _NAVDIR / "positions_paper.csv"


def _upsert(row: dict) -> None:
    """Replace today's row for this book in paper_nav.csv (account-level NAV)."""
    _FEED.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(_FEED) if _FEED.is_file() else pd.DataFrame()
    if not df.empty:
        df = df[~((df["book"] == row["book"]) & (df["date"].astype(str) == row["date"]))]
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df = df.sort_values(["book", "date"]).reset_index(drop=True)
    df.to_csv(_FEED, index=False)


def _upsert_positions(rows: list[dict], book: str, day: str) -> None:
    """Replace today's positions for this book in positions_paper.csv. This is what drives the
    PER-STRATEGY paper split (review._paper_strategy_curve attributes each holding to its strategy);
    without it the monitor's PAPER line has nothing per-strategy and flatlines on stale data."""
    _POSFEED.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(_POSFEED) if _POSFEED.is_file() else pd.DataFrame()
    if not df.empty:
        df = df[~((df["book"] == book) & (df["date"].astype(str) == day))]
    df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True) if rows else df
    df = df.sort_values(["book", "date", "symbol"]).reset_index(drop=True)
    df.to_csv(_POSFEED, index=False)


async def main() -> int:
    creds = IBCredentials.load()
    clock = WallClock()
    rl = TokenBucketRateLimiter(config=IB_DEFAULT_RATE_LIMITS, clock=clock)
    client = IBClient(credentials=creds, rate_limiter=rl, clock=clock)
    broker = IBBroker(client=client, resolver=IBInstrumentResolver(client), clock=clock)
    await broker.connect()
    snap = await broker.account_snapshot()
    portfolio = list(client.ib.portfolio())          # PortfolioItem: contract, position, marketPrice, marketValue
    await broker.disconnect()

    day = date.today().isoformat()
    book = f"PAPER:{creds.account_id}"

    # account-level NAV (unchanged)
    row = {"date": day, "book": book, "nav": round(float(snap.equity), 2),
           "gross_exposure": round(float(getattr(snap, "gross_exposure", 0) or 0), 2),
           "ccy": snap.base_currency or "", "source": "blive"}
    _upsert(row)

    # per-position snapshot — value + ccy are LOCAL (IB marketValue is in the contract currency);
    # review._paper_strategy_curve converts to USD by ccy before the per-strategy split.
    pos_rows = []
    for it in portfolio:
        if not it.position:
            continue
        c = it.contract
        pos_rows.append({"date": day, "book": book, "symbol": c.symbol,
                         "quantity": float(it.position), "mark_price": round(float(it.marketPrice), 6),
                         "value": round(float(it.marketValue), 2), "ccy": c.currency or "",
                         # avg_cost = the REAL blended fill price IB recorded for the open lot; unreal_pnl
                         # = IB's own (mark − avgCost)×qty in local ccy. This is the genuine execution
                         # record — real cost basis for true paper P&L, no Flex/journal needed.
                         "avg_cost": round(float(it.averageCost), 6),
                         "unreal_pnl": round(float(it.unrealizedPNL), 2),
                         "source": "blive"})
    _upsert_positions(pos_rows, book, day)

    print(f"logged paper NAV + {len(pos_rows)} positions -> {_NAVDIR}")
    print(f"  {day}  {book}  {row['ccy']} {row['nav']:,.2f}  (gross {row['gross_exposure']:,.2f})")
    for r in pos_rows:
        print(f"    {r['symbol']:8} {r['ccy']:4} qty={r['quantity']:>8.0f}  value={r['value']:>12,.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
