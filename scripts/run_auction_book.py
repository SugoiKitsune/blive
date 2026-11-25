"""Run one phase of an auction book on the IB paper account.

An auction book buys in the closing auction and sells in the next opening
auction (:mod:`blive.runtime.auction_book`). The names and weights come from a
*targets file* written by whatever decides them; blive does not know or care
how they were chosen.

Two phases, each a separate invocation (e.g. from Windows Task Scheduler)::

    # shortly before the close, after the targets file has been written
    run_auction_book.py --phase enter --book my-book

    # next morning, before the open
    run_auction_book.py --phase exit --book my-book

**Shadow by default.** Without ``--send`` nothing is connected and nothing is
sent: the orders that would be placed are printed and logged, and a separate
shadow record of the book is kept so that the next morning's shadow exit has
something to show. With ``--send`` the orders go to IB Gateway, and only if the
configured account is a paper account.

Files, all under ``~/.blive/data/auction_book/<book>/``:

- ``settings.json`` — the book's budget, limits and order windows
  (:class:`blive.runtime.auction_book.BookSettings`). Optional; command-line
  options override it.
- ``targets.json`` — input for ``enter`` (override with ``--targets``).
- ``state.json`` — what the book bought and has not yet sold
  (``state.shadow.json`` for shadow runs).
- ``runs.jsonl`` — one line per invocation: orders, mode, broker responses.

Exit codes: 0 done; 1 refused by a safety rule; 2 credentials/arguments/files;
3 connect failure.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from blive.domain.events import OrderEvent
from blive.domain.types import Order
from blive.runtime import auction_book as ab

DONE, REFUSED, BAD_INPUT, NO_CONNECTION = 0, 1, 2, 3


@dataclass(frozen=True)
class Run:
    """One invocation: which book, in which mode, at what time, with which files and settings."""

    book: str
    send: bool
    skip_time_checks: bool
    now: datetime
    settings: ab.BookSettings
    targets_path: Path
    state_path: Path
    log_path: Path

    @property
    def mode(self) -> str:
        return "send" if self.send else "shadow"

    def record(self, phase: str) -> dict[str, Any]:
        return {
            "at_utc": self.now.isoformat(),
            "book": self.book,
            "phase": phase,
            "mode": self.mode,
        }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run one phase of an auction book (IB paper).")
    p.add_argument("--phase", choices=("enter", "exit"), required=True)
    p.add_argument(
        "--book", required=True, help="Book id; names the data directory and the strategy_id."
    )
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
    p.add_argument("--data-dir", default=None, help="Override ~/.blive/data/auction_book.")
    p.add_argument(
        "--settings", default=None, help="Settings file. Default: <book dir>/settings.json."
    )
    p.add_argument(
        "--targets", default=None, help="Targets file. Default: <book dir>/targets.json."
    )
    p.add_argument(
        "--budget-usd", type=Decimal, default=None, help="Override the settings' budget_usd."
    )
    p.add_argument("--max-names", type=int, default=None, help="Override the settings' max_names.")
    p.add_argument(
        "--settle-seconds",
        type=float,
        default=None,
        help="Override the settings' settle_seconds (how long broker responses are collected).",
    )
    return p.parse_args(argv)


def _build_run(args: argparse.Namespace, now: datetime) -> Run:
    base = (
        Path(args.data_dir) if args.data_dir else Path.home() / ".blive" / "data" / "auction_book"
    )
    book_dir = base / args.book
    settings = ab.load_settings(
        Path(args.settings) if args.settings else book_dir / "settings.json"
    )
    overrides = {
        name: value
        for name, value in (
            ("budget_usd", args.budget_usd),
            ("max_names", args.max_names),
            ("settle_seconds", args.settle_seconds),
        )
        if value is not None
    }
    return Run(
        book=args.book,
        send=args.send,
        skip_time_checks=args.skip_time_checks,
        now=now,
        settings=replace(settings, **overrides),
        targets_path=Path(args.targets) if args.targets else book_dir / "targets.json",
        state_path=book_dir / ("state.json" if args.send else "state.shadow.json"),
        log_path=book_dir / "runs.jsonl",
    )


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
        return BAD_INPUT, [], {}
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
        return NO_CONNECTION, [], {}

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
        return DONE, orders, details
    finally:
        await broker.disconnect()


def _report(orders: list[Order], details: dict[str, Any]) -> set[str]:
    """Print each order's last broker response; return the ids the broker rejected or never took."""
    bad: set[str] = set()
    print("\nbroker responses:")
    for o in orders:
        cid = str(o.client_order_id)
        err = details["submit_errors"].get(cid)
        resp = details["responses"].get(cid)
        kind = "SUBMIT_FAILED" if err else (resp["kind"] if resp else "NO_RESPONSE")
        reason = err or (resp["reason"] if resp else None)
        print(f"  {o.instrument.symbol:<6s} {kind}" + (f"  ({reason})" if reason else ""))
        if kind in ("SUBMIT_FAILED", "REJECTED", "CANCELED", "EXPIRED"):
            bad.add(cid)
    return bad


def _enter(run: Run) -> int:
    """Buy the targets in today's closing auction."""
    record = run.record("enter")
    budget = run.settings.budget_usd
    if budget is None:
        print(
            "FAILED: no budget -- set budget_usd in the book's settings.json or pass --budget-usd."
        )
        return BAD_INPUT
    held = ab.load_state(run.state_path)
    if held is not None and run.send:
        raise ab.AuctionBookError(
            f"the book still holds the names entered on {held.entered_on}; run --phase exit first"
        )
    targets = ab.load_targets(run.targets_path, max_names=run.settings.max_names)
    if targets.book_id != run.book:
        raise ab.AuctionBookError(f"targets are for book {targets.book_id!r}, not {run.book!r}")
    if not run.skip_time_checks:
        ab.check_fresh(targets, run.now, run.settings.max_targets_age)
        ab.require_entry_time(run.now, targets, run.settings)
    sized = ab.size_entries(targets, budget)
    orders = ab.entry_orders(sized, run.book, run.now)
    _print_orders("closing-auction orders", orders)
    notional = sum((s.notional for s in sized), Decimal("0"))
    print(f"reference notional: {notional:,.2f} USD of {budget:,.2f}")
    record.update(
        trade_date=targets.trade_date.isoformat(),
        budget_usd=str(budget),
        orders=[ab.describe(o) for o in orders],
    )
    if not run.send:
        ab.save_state(
            run.state_path,
            ab.state_from_entries(run.book, targets.trade_date, sized) if sized else None,
        )
        replaced = f" (replacing the one entered on {held.entered_on})" if held is not None else ""
        print(f"\nshadow: nothing was sent. The shadow book now holds these names{replaced}.")
        ab.append_record(run.log_path, record)
        return DONE

    code, _, details = asyncio.run(
        _send(lambda _positions: orders, run.settings.settle_seconds, want_positions=False)
    )
    if code != DONE:
        return code
    bad = _report(orders, details)
    kept = [s for s, o in zip(sized, orders, strict=True) if str(o.client_order_id) not in bad]
    ab.save_state(
        run.state_path,
        ab.state_from_entries(run.book, targets.trade_date, kept) if kept else None,
    )
    record.update(
        responses=details["responses"],
        submit_errors=details["submit_errors"],
        held=[s.symbol for s in kept],
    )
    ab.append_record(run.log_path, record)
    print(f"\nthe book now expects to hold {len(kept)} names; state: {run.state_path}")
    return DONE


def _exit(run: Run) -> int:
    """Sell what the book holds in the next opening auction."""
    record = run.record("exit")
    state = ab.load_state(run.state_path)
    if state is None:
        print("the book holds nothing; nothing to sell.")
        ab.append_record(run.log_path, {**record, "orders": []})
        return DONE
    if not run.skip_time_checks:
        ab.require_window(run.now, run.settings.exit_window, "exit")
    record.update(entered_on=state.entered_on.isoformat())
    if not run.send:
        orders = ab.exit_orders(state, None, run.book, run.now)
        _print_orders("opening-auction orders", orders)
        ab.save_state(run.state_path, None)
        print("\nshadow: nothing was sent. The shadow book is empty again.")
        ab.append_record(run.log_path, {**record, "orders": [ab.describe(o) for o in orders]})
        return DONE

    code, orders, details = asyncio.run(
        _send(
            lambda positions: ab.exit_orders(state, positions, run.book, run.now),
            run.settings.settle_seconds,
            want_positions=True,
        )
    )
    if code != DONE:
        return code
    _print_orders("opening-auction orders", orders)
    bad = _report(orders, details)
    unsold = {o.instrument.symbol for o in orders if str(o.client_order_id) in bad}
    left = tuple(h for h in state.holdings if h.symbol in unsold)
    ab.save_state(
        run.state_path,
        (
            ab.BookState(book_id=state.book_id, entered_on=state.entered_on, holdings=left)
            if left
            else None
        ),
    )
    record.update(
        orders=[ab.describe(o) for o in orders],
        responses=details["responses"],
        submit_errors=details["submit_errors"],
        unsold=[h.symbol for h in left],
    )
    ab.append_record(run.log_path, record)
    if left:
        print(
            f"\nWARNING: {len(left)} sell order(s) were not taken: {[h.symbol for h in left]}. They stay in the book's state."
        )
    return DONE


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    if args.send and args.skip_time_checks:
        print("FAILED: --skip-time-checks is for shadow runs only.")
        return BAD_INPUT
    try:
        run = _build_run(args, datetime.now(timezone.utc))
    except ab.AuctionBookError as exc:
        print(f"FAILED: {exc}")
        return BAD_INPUT
    print(f"auction book '{run.book}': phase={args.phase} mode={run.mode}")
    try:
        return _enter(run) if args.phase == "enter" else _exit(run)
    except ab.AuctionBookError as exc:
        print(f"\nREFUSED: {exc}")
        ab.append_record(run.log_path, {**run.record(args.phase), "refused": str(exc)})
        return REFUSED
    except FileNotFoundError as exc:
        print(f"\nFAILED: {exc}")
        return BAD_INPUT


if __name__ == "__main__":
    sys.exit(main())
