"""Tests for :mod:`blive.runtime.auction_book`: the targets file, the safety
rules (paper account, freshness, order window), sizing, the orders built for
each auction, and the book's own record of what it holds."""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from blive.domain.types import OrderSide, OrderType, TimeInForce
from blive.runtime import auction_book as ab

# 2026-11-23 is a Monday; New York is UTC-5 in November.
DECIDED = datetime(2026, 11, 23, 20, 46, 0, tzinfo=timezone.utc)  # 15:46 New York
NOW = DECIDED + timedelta(seconds=30)
SETTINGS = ab.BookSettings()  # the defaults


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
    assert t.session_close is None
    stated = ab.parse_targets(_payload(session_close="2026-11-23T16:00:00-05:00"))
    assert stated.session_close == datetime(2026, 11, 23, 21, 0, 0, tzinfo=timezone.utc)


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
    max_age = SETTINGS.max_targets_age
    ab.check_fresh(t, NOW, max_age)
    with pytest.raises(ab.AuctionBookError, match="old"):
        ab.check_fresh(t, DECIDED + timedelta(minutes=6), max_age)
    ab.check_fresh(
        t, DECIDED + timedelta(minutes=6), timedelta(minutes=10)
    )  # the age limit is a setting
    with pytest.raises(ab.AuctionBookError, match="future"):
        ab.check_fresh(t, DECIDED - timedelta(seconds=1), max_age)
    with pytest.raises(ab.AuctionBookError, match="today is"):
        ab.check_fresh(t, NOW + timedelta(days=1), max_age)


def _utc(y: int, mo: int, d: int, h: int, mi: int) -> datetime:
    return datetime(y, mo, d, h, mi, 0, tzinfo=timezone.utc)


def test_entry_window_is_counted_back_from_the_close() -> None:
    t = ab.parse_targets(_payload())  # no session_close: the settings' regular close, 16:00
    assert ab.entry_window(t, SETTINGS) == (_utc(2026, 11, 23, 20, 40), _utc(2026, 11, 23, 20, 49))
    ab.require_entry_time(NOW, t, SETTINGS)  # 15:46:30
    for outside in (_utc(2026, 11, 23, 20, 39), _utc(2026, 11, 23, 20, 49)):  # 15:39, 15:49
        with pytest.raises(ab.AuctionBookError, match="outside 15:40-15:49"):
            ab.require_entry_time(outside, t, SETTINGS)
    with pytest.raises(ab.AuctionBookError, match="outside"):  # the right time on the wrong day
        ab.require_entry_time(NOW + timedelta(days=1), t, SETTINGS)
    # In summer New York is UTC-4: 15:46 local is 19:46 UTC.
    summer = ab.parse_targets(
        _payload(trade_date="2026-07-15", decided_at="2026-07-15T19:45:30+00:00")
    )
    ab.require_entry_time(_utc(2026, 7, 15, 19, 46), summer, SETTINGS)
    wider = ab.parse_settings(
        {"entry_opens_minutes_before_close": 30, "entry_closes_minutes_before_close": 6}
    )
    ab.require_entry_time(_utc(2026, 11, 23, 20, 53), t, wider)  # 15:53 is inside 15:30-15:54


def test_entry_window_follows_an_early_close_stated_by_the_targets() -> None:
    # The day after Thanksgiving closes at 13:00 New York (18:00 UTC).
    t = ab.parse_targets(
        _payload(
            trade_date="2026-11-27",
            decided_at="2026-11-27T17:45:10+00:00",
            session_close="2026-11-27T13:00:00-05:00",
        )
    )
    assert ab.entry_window(t, SETTINGS) == (_utc(2026, 11, 27, 17, 40), _utc(2026, 11, 27, 17, 49))
    ab.require_entry_time(_utc(2026, 11, 27, 17, 46), t, SETTINGS)  # 12:46
    with pytest.raises(ab.AuctionBookError, match="outside 12:40-12:49"):
        ab.require_entry_time(_utc(2026, 11, 27, 20, 46), t, SETTINGS)  # 15:46: the market is shut


@pytest.mark.parametrize(
    "close, message",
    [
        ("not a time", "malformed"),
        ("2026-11-23T16:00:00", "timezone"),
        ("2026-11-24T16:00:00-05:00", "is not on"),
    ],
)
def test_parse_targets_rejects_a_bad_session_close(close: str, message: str) -> None:
    with pytest.raises(ab.AuctionBookError, match=message):
        ab.parse_targets(_payload(session_close=close))


def test_exit_window_follows_new_york_time_and_skips_weekends() -> None:
    window = SETTINGS.exit_window
    ab.require_window(_utc(2026, 11, 24, 14, 0), window, "exit")  # 09:00
    with pytest.raises(ab.AuctionBookError, match="outside"):
        ab.require_window(_utc(2026, 11, 24, 14, 25), window, "exit")  # 09:25
    with pytest.raises(ab.AuctionBookError, match="outside"):
        ab.require_window(NOW, window, "exit")  # 15:46
    with pytest.raises(ab.AuctionBookError, match="Saturday"):
        ab.require_window(_utc(2026, 11, 21, 14, 0), window, "exit")


def test_settings_have_defaults_and_can_be_overridden_from_a_file(tmp_path: Path) -> None:
    assert ab.load_settings(tmp_path / "missing.json") == ab.BookSettings()
    assert SETTINGS.budget_usd is None and SETTINGS.max_names == 50
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "budget_usd": 50000,
                "max_names": 12,
                "regular_close": "16:00",
                "exit_window": ["07:00", "09:20"],
                "max_targets_age_seconds": 120,
                "settle_seconds": 3,
            }
        ),
        encoding="utf-8",
    )
    s = ab.load_settings(path)
    assert s.budget_usd == Decimal("50000") and s.max_names == 12
    assert s.exit_window == ab.Window(start=time(7, 0), end=time(9, 20))
    assert s.max_targets_age == timedelta(minutes=2) and s.settle_seconds == 3.0
    assert s.entry_opens_minutes_before_close == 20  # untouched keys keep their defaults


@pytest.mark.parametrize(
    "payload, message",
    [
        ({"budget": 50000}, "unknown keys"),
        ({"budget_usd": -1}, "positive"),
        ({"budget_usd": "lots"}, "not a number"),
        ({"max_names": 0}, "max_names"),
        ({"max_names": 2.5}, "whole number"),
        ({"regular_close": "4pm"}, "not a time"),
        ({"exit_window": ["09:25", "04:00"]}, "start before"),
        ({"exit_window": "04:00-09:25"}, r"\[start, end\]"),
        ({"entry_opens_minutes_before_close": 5}, "entry window"),
        ({"entry_closes_minutes_before_close": 0}, "entry window"),
        ({"max_targets_age_seconds": 0}, "out of range"),
    ],
)
def test_settings_reject_what_they_do_not_understand(payload: dict[str, Any], message: str) -> None:
    with pytest.raises(ab.AuctionBookError, match=message):
        ab.parse_settings(payload)


def test_settings_file_must_be_one_object(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ab.AuctionBookError, match="one JSON object"):
        ab.load_settings(path)


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
