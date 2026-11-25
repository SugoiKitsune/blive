"""One-shot today's rebalance using sfera's triple leveraged ETF signal.

Reads the sfera ``leveraged_etf_trend_filter.parquet`` signal (long format),
pivots to wide, extracts the latest date's target weights, fetches current
prices from IB for sizing, and submits MKT orders against IB Paper.

No EODHD parquets or offline signal refresh required — sfera already
computed the signal for today.

Usage::

    uv run python scripts/run_today_sfera_signal.py
    uv run python scripts/run_today_sfera_signal.py --nav-slice 0.05
    uv run python scripts/run_today_sfera_signal.py --sfera-signals PATH

Exit codes:
    0  success
    2  credentials / data error
    3  IB connect failure
    5  pipeline / sizing error
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pandas as pd

sys.path.insert(0, "src")

from blive.adapters.clock.wall import WallClock
from blive.adapters.ib import (
    IB_DEFAULT_RATE_LIMITS,
    IBClient,
    IBConnectionError,
    IBCredentials,
    IBInstrumentResolver,
    IBMarketData,
)
from blive.adapters.ib.broker import IBBroker
from blive.adapters.shared.credentials import CredentialsMissing
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter
from blive.domain.types import (
    AssetClass,
    ClientOrderId,
    Instrument,
    Order,
    OrderSide,
    OrderState,
    OrderType,
    Position,
    TimeInForce,
)
from blive.runtime.ib_pipeline import _drain_order_lifecycle, _drain_startup_events  # noqa: PLC2701
from blive.sizing import SizerInput, size_orders

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger("run_today")

_DEFAULT_SFERA_SIGNALS = (
    Path(r"C:\Personal\Business & Investments\Python codes\sfera")
    / "data"
    / "signals"
    / "leveraged_etf_trend_filter.parquet"
)

_TRADABLES: list[Instrument] = [
    Instrument(
        symbol="TQQQ",
        venue="XNAS",
        currency="USD",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
        tradability="spot",
    ),
    Instrument(
        symbol="TMF",
        venue="ARCX",
        currency="USD",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
        tradability="spot",
    ),
    Instrument(
        symbol="IEF",
        venue="XNAS",
        currency="USD",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
        tradability="spot",
    ),
]
_INST_BY_SYMBOL: dict[str, Instrument] = {i.symbol: i for i in _TRADABLES}


def _load_today_weights(signals_path: Path) -> tuple[dict[str, Decimal], object]:
    """Read sfera long-format parquet, return latest date's weights."""
    df = pd.read_parquet(signals_path)
    # Expected columns: date, identifier, value, event
    df["date"] = pd.to_datetime(df["date"])
    latest_date = df["date"].max()
    today = df[df["date"] == latest_date]
    weights: dict[str, Decimal] = {}
    for _, row in today.iterrows():
        sym = str(row["identifier"])
        if sym in _INST_BY_SYMBOL:
            weights[sym] = Decimal(str(float(row["value"])))
    # Fill missing symbols with 0
    for inst in _TRADABLES:
        weights.setdefault(inst.symbol, Decimal("0"))
    return weights, latest_date


async def _fetch_latest_price(market_data: IBMarketData, inst: Instrument) -> Decimal:
    """Fetch the most recent daily close for an instrument via IB historical bars."""
    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=5)  # last 5 calendar days → enough for 1 trading day
    bars = await market_data.historical_bars(inst, freq="1d", start=start, end=end)
    if not bars:
        raise RuntimeError(f"No bars returned from IB for {inst.symbol}")
    return bars[-1].close


def _make_mkt_order(desired: Order) -> Order:
    """Convert a sized order to a MKT order for IB submission."""
    return Order(
        client_order_id=ClientOrderId(uuid4()),
        strategy_id=desired.strategy_id,
        instrument=desired.instrument,
        side=desired.side,
        quantity=desired.quantity,
        order_type=OrderType.MKT,
        time_in_force=TimeInForce.DAY,
        limit_price=None,
        stop_price=None,
        parent_id=None,
        tags={**desired.tags, "pipeline": "sfera-today"},
        created_at=desired.created_at,
    )


async def _run(args: argparse.Namespace) -> int:
    signals_path = Path(args.sfera_signals)
    if not signals_path.is_file():
        print(f"\nFAILED: sfera signals not found at {signals_path}")
        return 2

    # --- Load signal ---------------------------------------------------------
    try:
        target_weights, signal_date = _load_today_weights(signals_path)
    except Exception as exc:
        print(f"\nFAILED: could not load sfera signal: {exc}")
        return 2

    print(f"\n=== Today's target weights (sfera, {signal_date.date()}) ===")
    for sym, w in target_weights.items():
        print(f"  {sym}: {float(w):.2%}")

    # --- Connect to IB -------------------------------------------------------
    try:
        credentials = IBCredentials.load()
    except (CredentialsMissing, ValueError) as exc:
        print(f"\nFAILED: IB credentials: {exc}")
        return 2

    clock = WallClock()
    rate_limiter = TokenBucketRateLimiter(config=IB_DEFAULT_RATE_LIMITS, clock=clock)
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock)
    resolver = IBInstrumentResolver(client)
    market_data = IBMarketData(client=client, resolver=resolver, clock=clock)
    broker = IBBroker(client=client, resolver=resolver, clock=clock)

    print("\n=== Connecting to IB Paper ===")
    try:
        await broker.connect()
    except IBConnectionError as exc:
        print(f"\nFAILED on connect: {exc}")
        return 3
    print(f"  connected: {broker.is_connected}")

    # Drain any startup events before per-order loops.
    await _drain_startup_events(broker)

    # --- Account snapshot + positions ----------------------------------------
    snap = await broker.account_snapshot()
    equity = snap.equity
    print(f"\n=== Account snapshot ===")
    print(f"  Account:  {credentials.account_id}")
    print(f"  Currency: {snap.base_currency}")
    print(f"  Equity:   {snap.base_currency} {float(equity):,.2f}")

    ib_positions = await broker.positions()
    positions: dict[str, Position] = {p.instrument.symbol: p for p in ib_positions}
    print(f"  Open positions: {list(positions.keys()) or '(none)'}")

    # --- Fetch live prices from IB -------------------------------------------
    print("\n=== Fetching latest prices from IB ===")
    prices: dict[str, Decimal] = {}
    for inst in _TRADABLES:
        try:
            price = await _fetch_latest_price(market_data, inst)
            prices[inst.symbol] = price
            print(f"  {inst.symbol}: ${float(price):.4f}")
        except Exception as exc:
            print(f"\nFAILED: could not fetch price for {inst.symbol}: {exc}")
            await broker.disconnect()
            return 5

    # --- Size orders ----------------------------------------------------------
    nav_slice = Decimal(str(args.nav_slice))
    print(
        f"\n=== Sizing orders (nav_slice={float(nav_slice):.1%}, "
        f"equity={float(equity):,.2f} {snap.base_currency}) ==="
    )

    sizer_in = SizerInput(
        target_weights=target_weights,
        equity=equity,
        nav_slice=nav_slice,
        current_positions=positions,
        instrument_resolver=lambda sym: _INST_BY_SYMBOL[sym],
        price_lookup=lambda inst: prices[inst.symbol],
        strategy_id="triple_lev_sma_filter_dsl",
        now=datetime.now(tz=timezone.utc),
    )
    try:
        candidate_orders = size_orders(sizer_in)
    except Exception as exc:
        print(f"\nFAILED in sizer: {exc}")
        await broker.disconnect()
        return 5

    if not candidate_orders:
        print("  No orders to submit — already at target weights.")
        await broker.disconnect()
        return 0

    for o in candidate_orders:
        print(f"  → {o.side.value} {float(o.quantity):.0f} {o.instrument.symbol}")

    # --- Submit orders --------------------------------------------------------
    print("\n=== Submitting MKT orders ===")
    filled = canceled = rejected = 0
    for desired in candidate_orders:
        order = _make_mkt_order(desired)
        print(
            f"  Submitting {order.side.value} {float(order.quantity):.0f} "
            f"{order.instrument.symbol} MKT ..."
        )
        await broker.submit(order)
        terminal_state, _, _ = await _drain_order_lifecycle(
            broker=broker,
            target_id=ClientOrderId(order.client_order_id),
            timeout_s=args.event_wait_seconds,
        )
        print(f"    → {terminal_state}")
        if terminal_state == OrderState.FILLED:
            filled += 1
        elif terminal_state == OrderState.CANCELED:
            canceled += 1
        elif terminal_state == OrderState.REJECTED:
            rejected += 1

    print(f"\n=== Done: filled={filled}  canceled={canceled}  rejected={rejected} ===")
    await broker.disconnect()
    return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Today's rebalance from sfera signal → IB Paper")
    p.add_argument(
        "--sfera-signals",
        default=str(_DEFAULT_SFERA_SIGNALS),
        help="Path to sfera leveraged_etf_trend_filter.parquet",
    )
    p.add_argument("--nav-slice", type=float, default=0.05, help="NAV slice (default 0.05 = 5%%)")
    p.add_argument(
        "--event-wait-seconds", type=float, default=30.0, help="Per-order FSM drain timeout"
    )
    return p.parse_args(argv)


def main() -> int:
    args = _parse_args(sys.argv[1:])
    try:
        return asyncio.run(_run(args))
    except KeyboardInterrupt:
        print("\nINTERRUPTED.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
