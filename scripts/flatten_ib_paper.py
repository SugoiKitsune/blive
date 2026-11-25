"""Flatten accumulated paper positions in the M3.2 tradable universe.

The M2-IB.6 replay driver (`run_m2ib6_ib_paper.py`) starts each run from a
fresh local $100k view, so it re-buys the Treasury legs (IBTL / IBTM) every
run and the IB **paper** account accumulates real positions across runs.
This one-off operational utility flattens those back to zero so a capture
campaign can start (or resume) from a clean slate.

Scoped to the M3.2 tradables (``QQL3`` / ``IBTL`` / ``IBTM``) by default;
submits market orders during RTH. Not part of the trading engine — it talks
to ``ib_async`` directly (no blive FSM / RiskEngine) because flattening is
an operator cleanup, not strategy execution. Uses a distinct ``clientId``
(default ``creds.client_id + 90``) so it never clashes with a driver run.

Usage::

    flatten_ib_paper.py             # flatten QQL3/IBTL/IBTM (market SELL/BUY)
    flatten_ib_paper.py --dry-run   # just report the non-zero positions
    flatten_ib_paper.py --symbols QQL3,IBTL,IBTM,QQQ   # override the set

Exit codes: 0 success (or nothing to flatten); 2 credentials/args; 3 connect.
"""

from __future__ import annotations

import argparse
import sys

import ib_async

from blive.adapters.ib import IBConnectionError, IBCredentials
from blive.adapters.shared.credentials import CredentialsMissing

_DEFAULT_SYMBOLS = ("QQL3", "IBTL", "IBTM")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Flatten accumulated IB-paper positions.")
    parser.add_argument(
        "--symbols",
        default=",".join(_DEFAULT_SYMBOLS),
        help="Comma-separated symbols to flatten. Default: QQL3,IBTL,IBTM.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the non-zero positions in scope; submit nothing.",
    )
    parser.add_argument(
        "--client-id",
        type=int,
        default=None,
        help="Override the IB clientId. Default: credentials client_id + 90 (avoids driver clash).",
    )
    parser.add_argument(
        "--settle-seconds",
        type=float,
        default=8.0,
        help="Seconds to wait for the flatten fills before reporting. Default: 8.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    symbols = {s.strip().upper() for s in args.symbols.split(",") if s.strip()}

    try:
        creds = IBCredentials.load()
    except CredentialsMissing as exc:
        print(f"\nFAILED: {exc}")
        return 2
    except (ValueError, IBConnectionError) as exc:
        print(f"\nFAILED: invalid credentials -- {exc}")
        return 2

    client_id = args.client_id if args.client_id is not None else creds.client_id + 90
    print(f"flatten target symbols: {sorted(symbols)}")
    print(f"IB: host={creds.host} port={creds.port} client_id={client_id} account=[REDACTED]")

    ib = ib_async.IB()
    try:
        ib.connect(creds.host, creds.port, clientId=client_id, timeout=15)
    except Exception as exc:  # noqa: BLE001 — surface any connect failure as exit 3
        print(f"\nFAILED on connect: {type(exc).__name__}: {exc}")
        print("  - Confirm IB Gateway is running and no driver run is in flight.")
        return 3

    try:
        in_scope = [p for p in ib.positions() if p.contract.symbol in symbols and p.position != 0]
        if not in_scope:
            print("no non-zero positions in scope; nothing to flatten.")
            return 0

        print(f"\n{len(in_scope)} position(s) in scope:")
        for p in in_scope:
            print(
                f"  {p.contract.symbol} ({p.contract.currency}): "
                f"{p.position:+g} @ avgCost {p.avgCost:.4f}"
            )

        if args.dry_run:
            print("\n--dry-run: submitting nothing.")
            return 0

        print("\nsubmitting flatten market orders:")
        trades = []
        for p in in_scope:
            action = "SELL" if p.position > 0 else "BUY"
            qty = abs(p.position)
            order = ib_async.MarketOrder(action, totalQuantity=qty)
            trade = ib.placeOrder(p.contract, order)
            trades.append((p.contract.symbol, action, qty, trade))
            print(f"  -> {action} {qty:g} {p.contract.symbol}")

        ib.sleep(args.settle_seconds)

        print("\nresult:")
        all_filled = True
        for symbol, action, qty, trade in trades:
            status = trade.orderStatus.status
            filled = trade.orderStatus.filled
            avg = trade.orderStatus.avgFillPrice
            print(f"  {symbol}: {action} {qty:g} -> status={status} filled={filled:g} avg={avg}")
            if status != "Filled":
                all_filled = False
        if not all_filled:
            print(
                "\nNOTE: not all flatten orders filled within the settle window "
                "(market may be thin / closing). Re-run to confirm, or check TWS."
            )
        return 0
    finally:
        ib.disconnect()


if __name__ == "__main__":
    sys.exit(main())
