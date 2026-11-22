"""Auction book: enter at the closing auction, leave at the next opening auction.

A strategy-agnostic execution shape. Something outside blive decides, shortly
before the close, which names to hold overnight and with what weights, and
writes them to a *targets file*. This module turns that file into
market-on-close BUY orders, remembers what the book bought, and the next
morning turns that memory into opening-auction SELL orders.

Everything here is pure: no broker, no clock, no network. The driver
(``scripts/run_auction_book.py``) supplies ``now``, the account id and the
broker's positions, and does the submitting. That keeps the rules below
unit-testable and keeps this module free of adapter imports (ADR-034).

Safety rules enforced here, not left to the caller:

- **Paper accounts only.** :func:`require_paper_account` refuses any account
  id that is not an IB paper id.
- **Fresh targets only.** A targets file is for one trading date and expires
  a few minutes after it was decided (:func:`check_fresh`).
- **Inside the auction's order window only.** Orders are built only while the
  auction still accepts them (:func:`require_entry_time`, :func:`require_window`).
- **Never sell what the book did not buy.** Exit quantities are capped by both
  the book's own record and the broker's position (:func:`exit_orders`).

Nothing about one book is fixed in code: its budget, its limits and its order
windows are :class:`BookSettings`, read from a file next to the book's state.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import ROUND_DOWN, Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from blive.domain.types import (
    AssetClass,
    Instrument,
    Order,
    OrderSide,
    OrderType,
    TimeInForce,
)

SCHEMA_VERSION = 1
EXCHANGE_TZ = ZoneInfo("America/New_York")
# Venues the IB resolver routes via SMART (ADR-046).
ALLOWED_VENUES: frozenset[str] = frozenset({"XNAS", "XNYS", "ARCX", "BATS"})
_WEIGHT_SUM_TOLERANCE = Decimal("0.000001")


class AuctionBookError(ValueError):
    """A targets file, a time window or an account failed a safety rule."""


@dataclass(frozen=True, slots=True)
class TargetLine:
    symbol: str
    venue: str
    weight: Decimal
    reference_price: Decimal


@dataclass(frozen=True, slots=True)
class Targets:
    book_id: str
    trade_date: date
    decided_at: datetime
    lines: tuple[TargetLine, ...]
    session_close: datetime | None = None  # the day's closing time, if the file states it


@dataclass(frozen=True, slots=True)
class SizedLine:
    symbol: str
    venue: str
    shares: int
    notional: Decimal


@dataclass(frozen=True, slots=True)
class Holding:
    symbol: str
    venue: str
    shares: int


@dataclass(frozen=True, slots=True)
class BookState:
    book_id: str
    entered_on: date
    holdings: tuple[Holding, ...]


@dataclass(frozen=True, slots=True)
class Window:
    """A weekday time window in exchange time, ``start`` inclusive, ``end`` exclusive."""

    start: time
    end: time


@dataclass(frozen=True, slots=True)
class BookSettings:
    """How one book is run. Every field has a default except the budget.

    The entry window is counted back from the session's close, so it follows an
    early close when the targets file states one. The defaults: the closing
    auction stops taking market-on-close orders 10 minutes before the close on
    NYSE and 5 minutes before on Nasdaq, and the opening auction stops at 09:28;
    both windows end early enough to leave the broker time to route.
    """

    budget_usd: Decimal | None = None
    max_names: int = 50
    regular_close: time = time(16, 0)  # used when the targets file states no close
    entry_opens_minutes_before_close: int = 20
    entry_closes_minutes_before_close: int = 11
    exit_window: Window = Window(start=time(4, 0), end=time(9, 25))
    max_targets_age_seconds: int = 300
    settle_seconds: float = 8.0

    def __post_init__(self) -> None:
        if self.budget_usd is not None and self.budget_usd <= 0:
            raise AuctionBookError("settings: budget_usd must be positive")
        if self.max_names <= 0:
            raise AuctionBookError("settings: max_names must be positive")
        if not self.entry_opens_minutes_before_close > self.entry_closes_minutes_before_close > 0:
            raise AuctionBookError(
                "settings: the entry window must open before it closes, and close before the session does"
            )
        if not self.exit_window.start < self.exit_window.end:
            raise AuctionBookError("settings: exit_window must start before it ends")
        if self.max_targets_age_seconds <= 0 or self.settle_seconds < 0:
            raise AuctionBookError(
                "settings: max_targets_age_seconds / settle_seconds out of range"
            )

    @property
    def max_targets_age(self) -> timedelta:
        return timedelta(seconds=self.max_targets_age_seconds)


SETTINGS_KEYS: frozenset[str] = frozenset(BookSettings.__dataclass_fields__)


def _clock_time(value: Any, name: str) -> time:
    try:
        return time.fromisoformat(str(value))
    except ValueError as exc:
        raise AuctionBookError(f"settings: {name} is not a time (HH:MM): {value!r}") from exc


def parse_settings(payload: Mapping[str, Any]) -> BookSettings:
    """Validate a settings file's content. Expected shape, every key optional::

        {"budget_usd": 50000, "max_names": 50, "regular_close": "16:00",
         "entry_opens_minutes_before_close": 20, "entry_closes_minutes_before_close": 11,
         "exit_window": ["04:00", "09:25"], "max_targets_age_seconds": 300, "settle_seconds": 8}

    An unknown key is an error: a misspelt setting must not fall back to its
    default silently.
    """
    unknown = sorted(set(payload) - SETTINGS_KEYS)
    if unknown:
        raise AuctionBookError(f"settings: unknown keys {unknown}; known: {sorted(SETTINGS_KEYS)}")
    values: dict[str, Any] = {}
    for key, raw in payload.items():
        if key == "budget_usd":
            values[key] = None if raw is None else _decimal(raw, "settings.budget_usd")
        elif key == "regular_close":
            values[key] = _clock_time(raw, key)
        elif key == "exit_window":
            if not isinstance(raw, list) or len(raw) != 2:
                raise AuctionBookError("settings: exit_window must be [start, end]")
            values[key] = Window(start=_clock_time(raw[0], key), end=_clock_time(raw[1], key))
        elif key == "settle_seconds":
            values[key] = float(_decimal(raw, "settings.settle_seconds"))
        else:
            if isinstance(raw, bool) or not isinstance(raw, int):
                raise AuctionBookError(f"settings: {key} must be a whole number: {raw!r}")
            values[key] = raw
    return BookSettings(**values)


def load_settings(path: Path) -> BookSettings:
    """The book's settings file, or the defaults if there is none."""
    if not path.exists():
        return BookSettings()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AuctionBookError("settings: the file must hold one JSON object")
    return parse_settings(payload)


# --- Targets file -------------------------------------------------------------


def _decimal(value: Any, name: str) -> Decimal:
    try:
        out = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise AuctionBookError(f"{name} is not a number: {value!r}") from exc
    if not out.is_finite():
        raise AuctionBookError(f"{name} is not finite: {value!r}")
    return out


def parse_targets(payload: Mapping[str, Any], *, max_names: int = 50) -> Targets:
    """Validate a targets file's content and return it typed.

    Expected shape::

        {"schema": 1, "book_id": "...", "trade_date": "2026-11-23",
         "decided_at": "2026-11-23T20:46:02+00:00",
         "session_close": "2026-11-23T16:00:00-05:00",
         "targets": [{"symbol": "ABC", "venue": "XNAS", "weight": 0.1,
                      "reference_price": 123.45}, ...]}

    ``weight`` is the share of the book's budget. Weights are positive and sum
    to at most 1. ``reference_price`` is the price the decision saw; it sizes
    the order (the auction price is not known when the order is sent).
    ``session_close`` is optional: the day's closing time, for early closes.
    It must carry a timezone and fall on ``trade_date``.
    """
    if payload.get("schema") != SCHEMA_VERSION:
        raise AuctionBookError(f"unsupported targets schema: {payload.get('schema')!r}")
    book_id = str(payload.get("book_id") or "")
    if not book_id:
        raise AuctionBookError("book_id is missing")
    try:
        trade_date = date.fromisoformat(str(payload["trade_date"]))
        decided_at = datetime.fromisoformat(str(payload["decided_at"]))
    except (KeyError, ValueError) as exc:
        raise AuctionBookError(f"trade_date / decided_at missing or malformed: {exc}") from exc
    if decided_at.tzinfo is None:
        raise AuctionBookError("decided_at must carry a timezone")
    session_close: datetime | None = None
    if payload.get("session_close") is not None:
        try:
            session_close = datetime.fromisoformat(str(payload["session_close"]))
        except ValueError as exc:
            raise AuctionBookError(f"session_close is malformed: {exc}") from exc
        if session_close.tzinfo is None:
            raise AuctionBookError("session_close must carry a timezone")
        if session_close.astimezone(EXCHANGE_TZ).date() != trade_date:
            raise AuctionBookError(f"session_close {session_close} is not on {trade_date}")
    raw = payload.get("targets")
    if not isinstance(raw, list) or not raw:
        raise AuctionBookError("targets is missing or empty")
    if len(raw) > max_names:
        raise AuctionBookError(f"{len(raw)} names exceed the limit of {max_names}")
    lines: list[TargetLine] = []
    seen: set[str] = set()
    for row in raw:
        symbol = str(row.get("symbol") or "").strip().upper()
        venue = str(row.get("venue") or "").strip().upper()
        if not symbol or symbol in seen:
            raise AuctionBookError(f"symbol missing or repeated: {symbol!r}")
        if venue not in ALLOWED_VENUES:
            raise AuctionBookError(
                f"{symbol}: venue {venue!r} is not one of {sorted(ALLOWED_VENUES)}"
            )
        weight = _decimal(row.get("weight"), f"{symbol}.weight")
        price = _decimal(row.get("reference_price"), f"{symbol}.reference_price")
        if weight <= 0 or price <= 0:
            raise AuctionBookError(f"{symbol}: weight and reference_price must be positive")
        seen.add(symbol)
        lines.append(TargetLine(symbol=symbol, venue=venue, weight=weight, reference_price=price))
    total = sum((line.weight for line in lines), Decimal("0"))
    if total > Decimal("1") + _WEIGHT_SUM_TOLERANCE:
        raise AuctionBookError(f"weights sum to {total}, above 1")
    return Targets(
        book_id=book_id,
        trade_date=trade_date,
        decided_at=decided_at,
        lines=tuple(lines),
        session_close=session_close,
    )


def load_targets(path: Path, *, max_names: int = 50) -> Targets:
    return parse_targets(json.loads(path.read_text(encoding="utf-8")), max_names=max_names)


# --- Safety rules -------------------------------------------------------------


def require_paper_account(account_id: str) -> None:
    """Refuse anything that is not an IB paper account (their ids start with ``DU``)."""
    if not account_id.upper().startswith("DU"):
        raise AuctionBookError(
            "the auction book runs on a paper account only; this account id is not one"
        )


def check_fresh(targets: Targets, now: datetime, max_age: timedelta) -> None:
    """The file must be for today (exchange date) and decided within ``max_age`` before ``now``."""
    today = now.astimezone(EXCHANGE_TZ).date()
    if targets.trade_date != today:
        raise AuctionBookError(f"targets are for {targets.trade_date}, today is {today}")
    age = now - targets.decided_at
    if age < timedelta(0):
        raise AuctionBookError("targets were decided in the future")
    if age > max_age:
        raise AuctionBookError(f"targets are {age} old, older than {max_age}")


def entry_window(targets: Targets, settings: BookSettings) -> tuple[datetime, datetime]:
    """When closing-auction orders may be sent for ``targets``: [opens, closes), counted back from the close."""
    close = targets.session_close or datetime.combine(
        targets.trade_date, settings.regular_close, tzinfo=EXCHANGE_TZ
    )
    return (
        close - timedelta(minutes=settings.entry_opens_minutes_before_close),
        close - timedelta(minutes=settings.entry_closes_minutes_before_close),
    )


def require_entry_time(now: datetime, targets: Targets, settings: BookSettings) -> None:
    """Refuse outside the entry window of the targets' own trading day."""
    opens, closes = entry_window(targets, settings)
    if not (opens <= now < closes):
        local = now.astimezone(EXCHANGE_TZ)
        raise AuctionBookError(
            f"entry: {local:%A %H:%M:%S} New York is outside "
            f"{opens.astimezone(EXCHANGE_TZ):%H:%M}-{closes.astimezone(EXCHANGE_TZ):%H:%M}"
            f" on {targets.trade_date}"
        )


def require_window(now: datetime, window: Window, what: str) -> None:
    local = now.astimezone(EXCHANGE_TZ)
    if local.weekday() >= 5:
        raise AuctionBookError(f"{what}: {local:%A} is not a trading day")
    if not (window.start <= local.time() < window.end):
        raise AuctionBookError(
            f"{what}: {local:%H:%M:%S} New York is outside {window.start:%H:%M}-{window.end:%H:%M}"
        )


# --- Sizing and orders --------------------------------------------------------


def size_entries(targets: Targets, budget: Decimal) -> list[SizedLine]:
    """Whole shares per name: ``floor(budget * weight / reference_price)`` (ADR-027). Zero-share names are dropped."""
    if budget <= 0:
        raise AuctionBookError("budget must be positive")
    out: list[SizedLine] = []
    for line in targets.lines:
        shares = int(
            (budget * line.weight / line.reference_price).to_integral_value(rounding=ROUND_DOWN)
        )
        if shares > 0:
            out.append(
                SizedLine(
                    symbol=line.symbol,
                    venue=line.venue,
                    shares=shares,
                    notional=line.reference_price * shares,
                )
            )
    return out


def _instrument(symbol: str, venue: str) -> Instrument:
    return Instrument(symbol=symbol, venue=venue, currency="USD", asset_class=AssetClass.EQUITY)


def _order(
    strategy_id: str,
    symbol: str,
    venue: str,
    side: OrderSide,
    shares: int,
    order_type: OrderType,
    tif: TimeInForce,
    now: datetime,
    phase: str,
) -> Order:
    return Order(
        client_order_id=uuid4(),
        strategy_id=strategy_id,
        instrument=_instrument(symbol, venue),
        side=side,
        quantity=Decimal(shares),
        order_type=order_type,
        time_in_force=tif,
        limit_price=None,
        stop_price=None,
        parent_id=None,
        tags={"auction_book": phase},
        created_at=now,
    )


def entry_orders(sized: Sequence[SizedLine], strategy_id: str, now: datetime) -> list[Order]:
    """One market-on-close BUY per sized line."""
    return [
        _order(
            strategy_id,
            s.symbol,
            s.venue,
            OrderSide.BUY,
            s.shares,
            OrderType.MOC,
            TimeInForce.DAY,
            now,
            "enter",
        )
        for s in sized
    ]


def exit_orders(
    state: BookState,
    broker_positions: Mapping[str, Decimal] | None,
    strategy_id: str,
    now: datetime,
) -> list[Order]:
    """One opening-auction SELL (market order, ``OPG``) per holding.

    The quantity is the smaller of what the book recorded and what the broker
    holds, so a partial or missing entry fill is never oversold. With
    ``broker_positions=None`` (shadow mode, no broker) the book's record is used.
    """
    out: list[Order] = []
    for h in state.holdings:
        shares = h.shares
        if broker_positions is not None:
            held = broker_positions.get(h.symbol, Decimal("0"))
            shares = min(shares, int(held.to_integral_value(rounding=ROUND_DOWN)))
        if shares > 0:
            out.append(
                _order(
                    strategy_id,
                    h.symbol,
                    h.venue,
                    OrderSide.SELL,
                    shares,
                    OrderType.MKT,
                    TimeInForce.OPG,
                    now,
                    "exit",
                )
            )
    return out


# --- The book's own record ----------------------------------------------------


def state_from_entries(book_id: str, entered_on: date, sized: Sequence[SizedLine]) -> BookState:
    return BookState(
        book_id=book_id,
        entered_on=entered_on,
        holdings=tuple(Holding(symbol=s.symbol, venue=s.venue, shares=s.shares) for s in sized),
    )


def save_state(path: Path, state: BookState | None) -> None:
    """Write the book's holdings, or an empty record once it has left."""
    payload: dict[str, Any] = {
        "schema": SCHEMA_VERSION,
        "book_id": None,
        "entered_on": None,
        "holdings": [],
    }
    if state is not None:
        payload = {
            "schema": SCHEMA_VERSION,
            "book_id": state.book_id,
            "entered_on": state.entered_on.isoformat(),
            "holdings": [
                {"symbol": h.symbol, "venue": h.venue, "shares": h.shares} for h in state.holdings
            ],
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1), encoding="utf-8")


def load_state(path: Path) -> BookState | None:
    """The book's holdings, or ``None`` if it holds nothing."""
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not payload.get("holdings"):
        return None
    return BookState(
        book_id=str(payload["book_id"]),
        entered_on=date.fromisoformat(str(payload["entered_on"])),
        holdings=tuple(
            Holding(symbol=str(h["symbol"]), venue=str(h["venue"]), shares=int(h["shares"]))
            for h in payload["holdings"]
        ),
    )


def append_record(path: Path, record: Mapping[str, Any]) -> None:
    """Append one JSON line to the run log."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, default=str) + "\n")


def describe(order: Order) -> dict[str, Any]:
    """An order as a plain record for the run log and the console."""
    return {
        "client_order_id": str(order.client_order_id),
        "symbol": order.instrument.symbol,
        "venue": order.instrument.venue,
        "side": order.side.value,
        "shares": int(order.quantity),
        "order_type": order.order_type.value,
        "time_in_force": order.time_in_force.value,
    }
