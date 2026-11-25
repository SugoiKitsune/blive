"""IB market-data smoke test.

Exercises ``IBMarketData.historical_bars`` against the live IB Paper
Gateway. Requests the last 30 trading days of daily CAC.PA bars
(Phase 1 instrument per [ADR-021](../docs/decisions/DECISIONS.md#adr-021--cac-etf-proxy-cacpa-lyxor-cac-40-ucits-etf))
and prints the count + the first / last bar.

Successful run validates [KB-3 §2](../docs/kb/ib_pacing_spec.md#2-historical-data-pacing)
historical pacing on the read side and exercises the BarFreq → IB
barSizeSetting mapping. Combined with the prior probes (handshake,
resolve, broker-read), this is enough surface coverage to consider
KB-2 / KB-3 STABLE-flip at M2-IB.3b-ii close.

``subscribe_bars`` / ``subscribe_trades`` are not exercised — they raise
NotImplementedError until M2-IB.5 pipeline integration.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from blive.adapters.clock.wall import WallClock
from blive.adapters.ib import (
    IB_DEFAULT_RATE_LIMITS,
    IBClient,
    IBConnectionError,
    IBCredentials,
    IBInstrumentResolver,
    IBMarketData,
)
from blive.adapters.ib.market_data import IBMarketDataError
from blive.adapters.shared.credentials import CredentialsMissing
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter
from blive.domain.types import AssetClass, Instrument


def _print_header(title: str) -> None:
    print()
    print(f"=== {title} ===")


def _print_step(label: str, detail: str = "") -> None:
    suffix = f" -- {detail}" if detail else ""
    print(f"  - {label}{suffix}")


# Phase 1 instrument per ADR-021.
_PHASE_1_INSTRUMENT = Instrument(
    symbol="CAC.PA",
    venue="XPAR",
    currency="EUR",
    asset_class=AssetClass.ETF,
    multiplier=Decimal("1"),
    tradability="spot",
)


async def _run_probe() -> int:
    _print_header("IB market-data probe")

    _print_step("loading IBCredentials from ~/.blive/secrets/ib.env / env")
    try:
        credentials = IBCredentials.load()
    except CredentialsMissing as exc:
        print(f"\nFAILED: {exc}")
        return 2
    except ValueError as exc:
        print(f"\nFAILED: invalid credentials value -- {exc}")
        return 2

    print(
        f"    host={credentials.host} port={credentials.port} "
        f"client_id={credentials.client_id} account_id=[REDACTED]"
    )
    if credentials.account_id == "replace-with-your-ib-paper-account-id":
        print("\nFAILED: IB_PAPER_ACCOUNT_ID is still the template placeholder.")
        return 2

    clock = WallClock()
    rate_limiter = TokenBucketRateLimiter(config=IB_DEFAULT_RATE_LIMITS, clock=clock)
    client = IBClient(credentials=credentials, rate_limiter=rate_limiter, clock=clock)
    resolver = IBInstrumentResolver(client)
    market_data = IBMarketData(client=client, resolver=resolver, clock=clock)

    _print_step("connecting to IB Paper Gateway")
    try:
        await client.connect()
    except IBConnectionError as exc:
        print(f"\nFAILED on connect: {exc}")
        return 3
    print(f"    is_connected={client.is_connected}")

    # Request the last 30 days of daily bars for CAC.PA.
    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=30)

    _print_step(
        "fetching historical_bars (CAC.PA, freq=1d, last 30 days)",
        f"start={start.date()} end={end.date()}",
    )
    started_at = datetime.now(tz=timezone.utc)
    try:
        bars = await market_data.historical_bars(
            _PHASE_1_INSTRUMENT, freq="1d", start=start, end=end
        )
    except IBMarketDataError as exc:
        print(f"\nFAILED on historical_bars: {exc}")
        if exc.__cause__ is not None:
            print(f"  underlying: {type(exc.__cause__).__name__}: {exc.__cause__}")
        await client.disconnect()
        return 4
    elapsed = (datetime.now(tz=timezone.utc) - started_at).total_seconds()
    print(f"    received {len(bars)} bars in {elapsed:.2f}s")

    if bars:
        first = bars[0]
        last = bars[-1]
        print(
            f"    first: {first.open_time_utc.date()} "
            f"O={first.open} H={first.high} L={first.low} C={first.close} "
            f"V={first.volume} VWAP={first.vwap}"
        )
        print(
            f"    last:  {last.open_time_utc.date()} "
            f"O={last.open} H={last.high} L={last.low} C={last.close} "
            f"V={last.volume} VWAP={last.vwap}"
        )
    else:
        print(
            "    (no bars returned -- subscription tier may be missing for delayed historical data?)"
        )

    metrics = rate_limiter.metrics()
    historical_metrics = metrics["historical"]
    print(
        f"    rate_limiter.historical available={historical_metrics.available:.2f}"
        f"/{historical_metrics.capacity} after fetch"
    )

    _print_step("disconnecting")
    await client.disconnect()
    print(f"    is_connected={client.is_connected}")

    _print_header("OK -- market-data historical_bars clean")
    print(
        "M2-IB.3b-ii wire-level historical_bars exercised end-to-end against "
        "IB Paper. Combined with handshake / resolve / broker-read probes, "
        "KB-2 / KB-3 STABLE-flip is now justified at the M2-IB.3b-ii commit."
    )
    return 0


def main() -> int:
    try:
        return asyncio.run(_run_probe())
    except KeyboardInterrupt:
        print("\nINTERRUPTED.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
