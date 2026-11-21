"""Tests for :mod:`blive.runtime.auction_book`: the targets file, the safety
rules (paper account, freshness, order window), sizing, the orders built for
each auction, and the book's own record of what it holds."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from blive.domain.types import OrderSide, OrderType, TimeInForce
from blive.runtime import auction_book as ab

# 2026-11-23 is a Monday; New York is UTC-5 in November.
DECIDED = datetime(2026, 11, 23, 20, 46, 0, tzinfo=timezone.utc)  # 15:46 New York
NOW = DECIDED + timedelta(seconds=30)


def _payload(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema": 1,
        "book_id": "book-a",
        "trade_date": "2026-11-23",
        "decided_at": DECIDED.isoformat(),
        "targets": [
            {"symbol": "aaa", "venue": "XNAS", "weight": 0.5, "reference_price": 100.0},
            {"symbol": "BBB", "venue": "XNYS", "weight": 0.5, "reference_price": 33.0},
        ],
    }
    base.update(over)
    return base


def test_parse_targets_normalises_and_types_the_file() -> None:
    t = ab.parse_targets(_payload())
    assert t.book_id == "book-a" and t.trade_date == date(2026, 11, 23)
    assert [line.symbol for line in t.lines] == ["AAA", "BBB"]
    assert t.lines[1].reference_price == Decimal("33.0")


@pytest.mark.parametrize(
    "over, message",
    [
        ({"schema": 2}, "schema"),
        ({"book_id": ""}, "book_id"),
        ({"trade_date": "yesterday"}, "malformed"),
        ({"decided_at": "2026-11-23T15:46:00"}, "timezone"),
        ({"targets": []}, "empty"),
        (
            {"targets": [{"symbol": "A", "venue": "XLON", "weight": 1, "reference_price": 1}]},
            "venue",
        ),
        (
            {"targets": [{"symbol": "A", "venue": "XNAS", "weight": 0, "reference_price": 1}]},
            "positive",
        ),
        (
            {"targets": [{"symbol": "A", "venue": "XNAS", "weight": "x", "reference_price": 1}]},
            "not a number",
        ),
        (
            {
                "targets": [
                    {"symbol": "A", "venue": "XNAS", "weight": 0.6, "reference_price": 1},
                    {"symbol": "B", "venue": "XNAS", "weight": 0.6, "reference_price": 1},
                ]
            },
            "above 1",
        ),
        (
            {
                "targets": [
                    {"symbol": "A", "venue": "XNAS", "weight": 0.1, "reference_price": 1},
                    {"symbol": "a", "venue": "XNAS", "weight": 0.1, "reference_price": 1},
                ]
            },
            "repeated",
        ),
    ],
)
def test_parse_targets_rejects_a_bad_file(over: dict[str, Any], message: str) -> None:
    with pytest.raises(ab.AuctionBookError, match=message):
        ab.parse_targets(_payload(**over))


def test_parse_targets_limits_the_number_of_names() -> None:
    with pytest.raises(ab.AuctionBookError, match="limit"):
        ab.parse_targets(_payload(), max_names=1)


def test_only_paper_accounts_are_accepted() -> None:
    ab.require_paper_account("DU1234567")
    ab.require_paper_account("dup000001")
    for live in ("U1234567", "F7654321", ""):
        with pytest.raises(ab.AuctionBookError, match="paper"):
            ab.require_paper_account(live)


def test_targets_must_be_for_today_and_recent() -> None:
    t = ab.parse_targets(_payload())
    ab.check_fresh(t, NOW)
    with pytest.raises(ab.AuctionBookError, match="old"):
        ab.check_fresh(t, DECIDED + timedelta(minutes=6))
    with pytest.raises(ab.AuctionBookError, match="future"):
        ab.check_fresh(t, DECIDED - timedelta(seconds=1))
    with pytest.raises(ab.AuctionBookError, match="today is"):
        ab.check_fresh(t, NOW + timedelta(days=1))


def test_order_windows_follow_new_york_time_and_skip_weekends() -> None:
    ab.require_window(NOW, ab.ENTRY_WINDOW, "entry")  # 15:46:30
    with pytest.raises(ab.AuctionBookError, match="outside"):
        ab.require_window(
            datetime(2026, 11, 23, 20, 49, 0, tzinfo=timezone.utc), ab.ENTRY_WINDOW, "entry"
        )  # 15:49
    with pytest.raises(ab.AuctionBookError, match="outside"):
        ab.require_window(NOW, ab.EXIT_WINDOW, "exit")
    ab.require_window(
        datetime(2026, 11, 24, 14, 0, 0, tzinfo=timezone.utc), ab.EXIT_WINDOW, "exit"
    )  # 09:00
    with pytest.raises(ab.AuctionBookError, match="Saturday"):
        ab.require_window(
            datetime(2026, 11, 21, 20, 46, 0, tzinfo=timezone.utc), ab.ENTRY_WINDOW, "entry"
        )
    # In summer New York is UTC-4: 15:46 local is 19:46 UTC.
    ab.require_window(
        datetime(2026, 7, 15, 19, 46, 0, tzinfo=timezone.utc), ab.ENTRY_WINDOW, "entry"
    )


def test_sizing_truncates_to_whole_shares_and_drops_empty_lines() -> None:
    t = ab.parse_targets(
        _payload(
            targets=[
                {"symbol": "AAA", "venue": "XNAS", "weight": 0.5, "reference_price": 100.0},
                {"symbol": "BBB", "venue": "XNYS", "weight": 0.4, "reference_price": 33.0},
                {"symbol": "CCC", "venue": "XNYS", "weight": 0.1, "reference_price": 5000.0},
            ]
        )
    )
    sized = ab.size_entries(t, Decimal("10000"))
    assert [(s.symbol, s.shares) for s in sized] == [
        ("AAA", 50),
        ("BBB", 121),
    ]  # 4000 / 33 = 121.2; CCC buys none
    assert sized[1].notional == Decimal("3993.0")
    assert sum((s.notional for s in sized), Decimal("0")) <= Decimal("10000")
    with pytest.raises(ab.AuctionBookError, match="budget"):
        ab.size_entries(t, Decimal("0"))


def test_entry_orders_are_market_on_close_buys() -> None:
    sized = ab.size_entries(ab.parse_targets(_payload()), Decimal("10000"))
    orders = ab.entry_orders(sized, "book-a", NOW)
    assert len(orders) == 2 and len({o.client_order_id for o in orders}) == 2
    for o, s in zip(orders, sized, strict=True):
        assert (o.side, o.order_type, o.time_in_force) == (
            OrderSide.BUY,
            OrderType.MOC,
            TimeInForce.DAY,
        )
        assert o.quantity == Decimal(s.shares) and o.instrument.symbol == s.symbol
        assert o.instrument.currency == "USD" and o.limit_price is None
    assert ab.describe(orders[0])["order_type"] == "MOC"


def test_exit_orders_never_sell_more_than_the_book_bought_or_the_broker_holds() -> None:
    sized = ab.size_entries(ab.parse_targets(_payload()), Decimal("10000"))  # AAA 50, BBB 151
    state = ab.state_from_entries("book-a", date(2026, 11, 23), sized)
    morning = datetime(2026, 11, 24, 14, 0, 0, tzinfo=timezone.utc)

    shadow = ab.exit_orders(state, None, "book-a", morning)
    assert [(o.instrument.symbol, int(o.quantity)) for o in shadow] == [("AAA", 50), ("BBB", 151)]
    for o in shadow:
        assert (o.side, o.order_type, o.time_in_force) == (
            OrderSide.SELL,
            OrderType.MKT,
            TimeInForce.OPG,
        )

    # AAA filled only 20 at the close; BBB sits in a larger position that is not all the book's; ZZZ is not the book's.
    held = {"AAA": Decimal("20"), "BBB": Decimal("500"), "ZZZ": Decimal("9")}
    live = ab.exit_orders(state, held, "book-a", morning)
    assert [(o.instrument.symbol, int(o.quantity)) for o in live] == [("AAA", 20), ("BBB", 151)]
    assert ab.exit_orders(state, {}, "book-a", morning) == []  # nothing filled: nothing to sell


def test_state_round_trip_and_cleared_state(tmp_path: Path) -> None:
    path = tmp_path / "book" / "state.json"
    assert ab.load_state(path) is None
    sized = ab.size_entries(ab.parse_targets(_payload()), Decimal("10000"))
    state = ab.state_from_entries("book-a", date(2026, 11, 23), sized)
    ab.save_state(path, state)
    assert ab.load_state(path) == state
    ab.save_state(path, None)
    assert ab.load_state(path) is None


def test_run_log_appends_one_json_line_per_record(tmp_path: Path) -> None:
    path = tmp_path / "runs.jsonl"
    ab.append_record(path, {"phase": "enter", "at": NOW})
    ab.append_record(path, {"phase": "exit", "n": 2})
    lines = path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["phase"] for line in lines] == ["enter", "exit"]


def test_load_targets_reads_a_file(tmp_path: Path) -> None:
    path = tmp_path / "targets.json"
    path.write_text(json.dumps(_payload()), encoding="utf-8")
    assert ab.load_targets(path).book_id == "book-a"
