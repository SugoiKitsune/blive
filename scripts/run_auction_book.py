"""Run one phase of an auction book on the IB paper account.

An auction book buys in the closing auction and sells in the next opening
auction (:mod:`blive.runtime.auction_book`). The names and weights come from a
*targets file* written by whatever decides them; blive does not know or care
how they were chosen.

Two phases, each a separate invocation (e.g. from Windows Task Scheduler)::

    # shortly before the close, after the targets file has been written
    run_auction_book.py --phase enter --book my-book --budget-usd 50000

    # next morning, before the open
    run_auction_book.py --phase exit --book my-book

**Shadow by default.** Without ``--send`` nothing is connected and nothing is
sent: the orders that would be placed are printed and logged. With ``--send``
the orders go to IB Gateway, and only if the configured account is a paper
account.

Files, all under ``~/.blive/data/auction_book/<book>/``:

- ``targets.json`` — input for ``enter`` (override with ``--targets``).
- ``state.json`` — what the book bought and has not yet sold.
- ``runs.jsonl`` — one line per invocation: orders, mode, broker responses.

Exit codes: 0 done; 1 refused by a safety rule; 2 credentials/arguments;
3 connect failure.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from blive.domain.events import OrderEvent
from blive.domain.types import Order
from blive.runtime import auction_book as ab


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run one phase of an auction book (IB paper).")
    p.add_argument("--phase", choices=("enter", "exit"), required=True)
    p.add_argument(
        "--book", required=True, help="Book id; names the data directory and the strategy_id."
    )
    p.add_argument(
        "--targets",
        default=None,
        help="Targets file for --phase enter. Default: <book dir>/targets.json.",
    )
    p.add_argument(
        "--budget-usd", type=Decimal, default=None, help="USD to deploy on --phase enter."
    )
    p.add_argument("--max-names", type=int, default=50)
    p.add_argument(
        "--send",
        action="store_true",
        help="Send the orders to IB (paper account only). Default: shadow.",
    )
    p.add_argument(
        "--skip-time-checks",
        action="store_true",
        help="Shadow only: skip the freshness and order-window checks (for rehearsals outside market hours).",
    )
    p.add_argument(
        "--settle-seconds", type=float, default=8.0, help="Seconds to collect broker responses."
    )
    p.add_argument("--data-dir", default=None, help="Override ~/.blive/data/auction_book.")
    return p.parse_args(argv)


def _print_orders(title: str, orders: list[Order]) -> None:
    print(f"\n{title} ({len(orders)}):")
    for o in orders:
        d = ab.describe(o)
        print(
            f"  {d['side']:4s} {d['shares']:>6d} {d['symbol']:<6s} {d['order_type']}/{d['time_in_force']}  [{d['venue']}]"
        )


async def _send(
    build: Callable[[dict[str, Decimal] | None], list[Order]],
    settle_seconds: float,
    want_positions: bool,
) -> tuple[int, list[Order], dict[str, Any]]:
    """Connect once, optionally read positions, build the orders, submit, collect responses.

    ``build`` receives the broker's positions by symbol (or ``None``) and returns the orders to send.
    Returns (exit code, orders, details).
    """
    # Imported here so that shadow mode needs neither ib_async nor credentials.
    from blive.adapters.clock.wall import WallClock
    from blive.adapters.ib import (
        IB_DEFAULT_RATE_LIMITS,
        IBClient,
        IBConnectionError,
        IBCredentials,
        IBInstrumentResolver,
    )
    from blive.adapters.ib.broker import IBBroker
    from blive.adapters.shared.credentials import CredentialsMissing
    from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter

    try:
        creds = IBCredentials.load()
    except (CredentialsMissing, ValueError) as exc:
        print(f"\nFAILED: credentials -- {exc}")
        return 2, [], {}
    ab.require_paper_account(creds.account_id)
    print(
        f"IB: host={creds.host} port={creds.port} client_id={creds.client_id} account=[REDACTED, paper]"
    )

    clock = WallClock()
    client = IBClient(
        credentials=creds,
        rate_limiter=TokenBucketRateLimiter(config=IB_DEFAULT_RATE_LIMITS, clock=clock),
        clock=clock,
    )
    broker = IBBroker(client=client, resolver=IBInstrumentResolver(client), clock=clock)
    try:
        await broker.connect()
    except IBConnectionError as exc:
        print(f"\nFAILED on connect: {exc}")
        return 3, [], {}

    details: dict[str, Any] = {"responses": {}, "submit_errors": {}}
    try:
        positions = (
            {p.instrument.symbol: p.quantity for p in await broker.positions()}
            if want_positions
            else None
        )
        orders = build(positions)
        for o in orders:
            try:
                await broker.submit(o)
            except Exception as exc:  # noqa: BLE001 -- one bad order must not stop the others
                details["submit_errors"][str(o.client_order_id)] = f"{type(exc).__name__}: {exc}"
        latest: dict[UUID, tuple[str, str | None]] = {}
        events = broker.events()
        loop = asyncio.get_running_loop()
        deadline = loop.time() + settle_seconds
        while (left := deadline - loop.time()) > 0:
            try:
                ev = await asyncio.wait_for(events.__anext__(), timeout=left)
            except (TimeoutError, StopAsyncIteration):
                break
            if isinstance(ev, OrderEvent):
                latest[ev.client_order_id] = (ev.kind.value, ev.reason)
        details["responses"] = {str(k): {"kind": v[0], "reason": v[1]} for k, v in latest.items()}
        return 0, orders, details
    finally:
        await broker.disconnect()


def _report(orders: list[Order], details: dict[str, Any]) -> list[str]:
    """Print each order's last broker response; return the ids the broker rejected or never took."""
    bad: list[str] = []
    print("\nbroker responses:")
    for o in orders:
        cid = str(o.client_order_id)
        err = details["submit_errors"].get(cid)
        resp = details["responses"].get(cid)
        kind = "SUBMIT_FAILED" if err else (resp["kind"] if resp else "NO_RESPONSE")
        reason = err or (resp["reason"] if resp else None)
        print(f"  {o.instrument.symbol:<6s} {kind}" + (f"  ({reason})" if reason else ""))
        if kind in ("SUBMIT_FAILED", "REJECTED", "CANCELED", "EXPIRED"):
            bad.append(cid)
    return bad


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    if args.send and args.skip_time_checks:
        print("FAILED: --skip-time-checks is for shadow runs only.")
        return 2
    base = (
        Path(args.data_dir) if args.data_dir else Path.home() / ".blive" / "data" / "auction_book"
    )
    book_dir = base / args.book
    state_path, log_path = book_dir / "state.json", book_dir / "runs.jsonl"
    now = datetime.now(timezone.utc)
    mode = "send" if args.send else "shadow"
    record: dict[str, Any] = {
        "at_utc": now.isoformat(),
        "book": args.book,
        "phase": args.phase,
        "mode": mode,
    }
    print(f"auction book '{args.book}': phase={args.phase} mode={mode}")

    try:
        if args.phase == "enter":
            if args.budget_usd is None:
                print("FAILED: --budget-usd is required for --phase enter.")
                return 2
            if ab.load_state(state_path) is not None:
                raise ab.AuctionBookError(
                    "the book still holds yesterday's names; run --phase exit first"
                )
            targets = ab.load_targets(
                Path(args.targets) if args.targets else book_dir / "targets.json",
                max_names=args.max_names,
            )
            if targets.book_id != args.book:
                raise ab.AuctionBookError(
                    f"targets are for book {targets.book_id!r}, not {args.book!r}"
                )
            if not args.skip_time_checks:
                ab.check_fresh(targets, now)
                ab.require_window(now, ab.ENTRY_WINDOW, "entry")
            sized = ab.size_entries(targets, args.budget_usd)
            orders = ab.entry_orders(sized, args.book, now)
            _print_orders("closing-auction orders", orders)
            print(
                f"reference notional: {sum((s.notional for s in sized), Decimal('0')):,.2f} USD of {args.budget_usd:,.2f}"
            )
            record.update(
                trade_date=targets.trade_date.isoformat(),
                budget_usd=str(args.budget_usd),
                orders=[ab.describe(o) for o in orders],
            )
            if not args.send:
                print("\nshadow: nothing was sent and the book's state was not changed.")
                ab.append_record(log_path, record)
                return 0
            code, _, details = asyncio.run(
                _send(lambda _positions: orders, args.settle_seconds, want_positions=False)
            )
            if code != 0:
                return code
            bad = set(_report(orders, details))
            kept = [
                s for s, o in zip(sized, orders, strict=True) if str(o.client_order_id) not in bad
            ]
            ab.save_state(
                state_path,
                ab.state_from_entries(args.book, targets.trade_date, kept) if kept else None,
            )
            record.update(
                responses=details["responses"],
                submit_errors=details["submit_errors"],
                held=[s.symbol for s in kept],
            )
            ab.append_record(log_path, record)
            print(f"\nthe book now expects to hold {len(kept)} names; state: {state_path}")
            return 0

        # ---- exit
        state = ab.load_state(state_path)
        if state is None:
            print("the book holds nothing; nothing to sell.")
            ab.append_record(log_path, {**record, "orders": []})
            return 0
        if not args.skip_time_checks:
            ab.require_window(now, ab.EXIT_WINDOW, "exit")
        record.update(entered_on=state.entered_on.isoformat())
        if not args.send:
            orders = ab.exit_orders(state, None, args.book, now)
            _print_orders("opening-auction orders", orders)
            print("\nshadow: nothing was sent and the book's state was not changed.")
            ab.append_record(log_path, {**record, "orders": [ab.describe(o) for o in orders]})
            return 0
        code, orders, details = asyncio.run(
            _send(
                lambda positions: ab.exit_orders(state, positions, args.book, now),
                args.settle_seconds,
                want_positions=True,
            )
        )
        if code != 0:
            return code
        _print_orders("opening-auction orders", orders)
        record.update(orders=[ab.describe(o) for o in orders])
        bad = set(_report(orders, details))
        unsold = {o.instrument.symbol for o in orders if str(o.client_order_id) in bad}
        left = [h for h in state.holdings if h.symbol in unsold]
        ab.save_state(
            state_path,
            (
                ab.BookState(
                    book_id=state.book_id, entered_on=state.entered_on, holdings=tuple(left)
                )
                if left
                else None
            ),
        )
        record.update(
            responses=details["responses"],
            submit_errors=details["submit_errors"],
            unsold=[h.symbol for h in left],
        )
        ab.append_record(log_path, record)
        if left:
            print(
                f"\nWARNING: {len(left)} sell order(s) were not taken: {[h.symbol for h in left]}. They stay in the book's state."
            )
        return 0
    except ab.AuctionBookError as exc:
        print(f"\nREFUSED: {exc}")
        ab.append_record(log_path, {**record, "refused": str(exc)})
        return 1
    except FileNotFoundError as exc:
        print(f"\nFAILED: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
