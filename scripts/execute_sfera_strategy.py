"""Execute a sfera strategy's target weights on IB Paper — strategy-agnostic.

This generalises ``run_today_sfera_signal.py`` (which was hardcoded to the
``leveraged_etf_trend_filter`` *signal* parquet + TQQQ/TMF/IEF) to the
canonical sfera platform output: **``strategy.target_weights``** — the final
TARGET WEIGHTS PER STRATEGY (per ``sfera/run_daily.py``). Signals are an
intermediate layer; this reads the layer a book actually trades.

Weight sources (operator's "DB-primary, file-fallback" directive):
  * ``--source db``   (default) — read ``strategy.target_weights`` straight
    from the sfera Postgres for ``--strategy`` at ``--as-of`` (latest by
    default). Connection coords come from sfera's ``.env`` (``--sfera-root``)
    so blive does not import the sfera package (KB-13 boundary).
  * ``--source file`` — read a parquet/CSV snapshot. Accepts the long
    ``strategy.target_weights`` shape (date, strategy, identifier, weight)
    or the legacy signal shape (date, identifier, value).

Order semantics: MOO (market-on-open) by default — matches every sfera
strategy's spec ("decide close[T], fill next open"). On IB this is a MARKET
order with ``tif=OPG`` (no new OrderType needed). ``--order-type MKT`` submits
an immediate day market order instead.

CASH is the *residual* (1 - sum of stored leg weights); it is never an order.
A leg you currently hold that is not in today's target is sized down to zero
(full rebalance to target) by the sizer.

Safety: **dry-run by default.** Nothing is submitted unless ``--submit`` is
passed, and then only after an interactive confirm (skip with ``--yes``).
The connect step is also a *detect-at-connect* probe: it reports the account
base currency and which target instruments are actually tradable on this
account (a US-ETF universe is PRIIPs-blocked on a UK retail account).

Usage::

    # offline preview (no IB needed): what would R02 trade today?
    uv run python scripts/execute_sfera_strategy.py --offline

    # live dry-run (connects, detects eligibility, sizes — submits nothing)
    uv run python scripts/execute_sfera_strategy.py --strategy R02

    # actually place MOO orders on IB Paper (gated)
    uv run python scripts/execute_sfera_strategy.py --strategy R02 --submit

Exit codes:
    0  success (preview or submit)
    2  credentials / data error
    3  IB connect failure
    4  no target instrument tradable on this account (eligibility)
    5  pipeline / sizing error
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
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
from blive.adapters.ib.instrument_resolver import InstrumentNotResolvable
from blive.adapters.shared.credentials import CredentialsMissing
from blive.adapters.shared.rate_limiter import TokenBucketRateLimiter
from blive.domain.types import (
    AssetClass,
    Bar,
    ClientOrderId,
    Instrument,
    Order,
    OrderSide,
    OrderType,
    Position,
    TimeInForce,
)
from blive.runtime.ib_pipeline import _drain_order_lifecycle, _drain_startup_events  # noqa: PLC2701
from blive.sizing import SizerInput, size_orders

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger("execute_sfera")

# --- US-ETF instrument catalogue --------------------------------------------
# symbol -> (primary-exchange hint, currency). The IBInstrumentResolver routes
# US equities via SMART with this primary-exchange hint (ADR-046). Hints are
# best-effort and validated empirically by the detect-at-connect probe; a wrong
# hint surfaces IB error 200 and the symbol is reported blocked, not silently
# mis-sized. CASH/BIL: CASH is the residual (no instrument); BIL is a real ETF.
_CATALOGUE: dict[str, Instrument] = {
    sym: Instrument(
        symbol=sym,
        venue=venue,
        currency="USD",
        asset_class=AssetClass.ETF,
        multiplier=Decimal("1"),
        tradability="spot",
    )
    for sym, venue in {
        "TQQQ": "XNAS",
        "TECL": "ARCX",
        "TECS": "ARCX",
        "SPXL": "ARCX",
        "UVXY": "BATS",
        "VXX": "BATS",
        "IEF": "XNAS",
        "TMF": "ARCX",
        "BIL": "ARCX",
    }.items()
}

_NON_TRADABLE = {"CASH"}  # residual sleeve — never an order

# --- EU single-name equities (R05 dividend book): EODHD "TICKER.EXCH" -> IB Instrument ON DEMAND ------
# The static _CATALOGUE above is US ETFs. R05 holds EU stocks in LOCAL ccys, and its Top-15 composition
# rotates monthly — so rather than hardcode names, we build each Instrument from its EODHD ticker: the
# exchange suffix maps to a MIC venue (the IB resolver turns MIC -> IB exchange) + the venue's default ccy.
_EODHD_EU_EXCH: dict[str, tuple[str, str]] = {
    "OL":    ("XOSL", "NOK"),   # Oslo Børs
    "CO":    ("XCSE", "DKK"),   # Nasdaq Copenhagen
    "MC":    ("XMAD", "EUR"),   # Bolsa de Madrid
    "AS":    ("XAMS", "EUR"),   # Euronext Amsterdam
    "PA":    ("XPAR", "EUR"),   # Euronext Paris
    "XETRA": ("XETR", "EUR"),   # Xetra
    "LSE":   ("XLON", "GBP"),   # London main book (quoted GBX pence; IB contract ccy is GBP)
    "SW":    ("XSWX", "CHF"),   # SIX Swiss (future R05 names)
    "ST":    ("XSTO", "SEK"),   # Stockholm
    "HE":    ("XHEL", "EUR"),   # Helsinki
}


def _ensure_eu_instruments(symbols, sfera_root=None) -> None:
    """Register EU single-name equities in _CATALOGUE from eodhd.instruments: 'TICKER.EXCH' -> Instrument
    (bare ticker, MIC venue, ISIN + IB currency, EQUITY). Resolution is BY ISIN (robust vs guessing the IB
    wire symbol). Records each symbol's EODHD price currency in _PRICE_CCY (e.g. GBX pence) for price->USD."""
    todo = [s for s in symbols if s not in _CATALOGUE and s not in _NON_TRADABLE and "." in s
            and s.rpartition(".")[2] in _EODHD_EU_EXCH]
    if not todo:
        return
    meta: dict[str, tuple] = {}
    try:
        import psycopg
        with psycopg.connect(_pg_conn_str(sfera_root), connect_timeout=5) as conn, conn.cursor() as cur:
            for s in todo:
                tk, _, ex = s.rpartition(".")
                cur.execute("SELECT isin, currency FROM eodhd.instruments "
                            "WHERE ticker=%s AND exchange_code=%s LIMIT 1", (tk, ex))
                r = cur.fetchone()
                if r:
                    meta[s] = (r[0], r[1])
    except Exception:  # noqa: BLE001 - fall back to venue-default ccy, no ISIN (symbol resolution)
        pass
    for s in todo:
        tk, _, ex = s.rpartition(".")
        mic, default_ccy = _EODHD_EU_EXCH[ex]
        isin, eod_ccy = meta.get(s, (None, None))
        price_ccy = (eod_ccy or default_ccy or "EUR").upper()   # EODHD price currency (may be GBX = pence)
        _PRICE_CCY[s] = price_ccy
        ib_ccy = "GBP" if price_ccy == "GBX" else price_ccy     # IB contract ccy (GBX is not valid on the wire)
        _CATALOGUE[s] = Instrument(symbol=tk, venue=mic, currency=ib_ccy, isin=(isin or None),
                                   asset_class=AssetClass.EQUITY, multiplier=Decimal("1"),
                                   tradability="spot")

# --- Canonical strategy registry --------------------------------------------
# Naming convention (per operator):
#   * R-code (R01, R02, ...) = the research/strategy identity that lab + sfera
#     produce. This is the canonical id the operator types/sees.
#   * `slot` = the ForgeFolio PROD slot it's currently deployed into (S14, ...).
#     The R->S binding is a deployment decision and CAN change, so it lives as a
#     field here, not as the primary key.
#   * `db_key` = the *current* sfera DB key (``strategy.target_weights.strategy``)
#     — still ``r_lev_*`` until/unless that column is re-keyed. Kept in exactly
#     one place so the legacy name never leaks into the rest of the tool.
#
# (ForgeFolio's systematic_strategies.json S14 row is stale — it still lists the
# old vix_vxx_rotation signal + TQQQ/VXX/IEF; R02 is the qc_cash conditional-
# rotation tree on TQQQ/TECL/UVXY/TECS.)
_STRATEGIES: dict[str, dict] = {
    "R01": {"db_key": "r_lev_001", "slot": None,    "name": "SMA-200 trend (TQQQ/IEF)",             "status": "retired"},
    "R02": {"db_key": "r_lev_002", "slot": "S14",   "name": "Conditional rotation (qc_cash)",       "status": "live"},
    "R03": {"db_key": "r_lev_003", "slot": None,    "name": "Keeper (rotation + vol/chop overlays)", "status": "candidate"},
    "R04": {"db_key": "r_lev_004", "slot": "S14v2", "name": "Sized rotation (+iv9M/COT)",            "status": "candidate"},
    "R05": {"db_key": "eu_div_income", "slot": None, "name": "EU dividend income (treaty-0%, EU stocks)", "status": "candidate"},
}
_SLOT_TO_RCODE = {v["slot"]: k for k, v in _STRATEGIES.items() if v["slot"]}
_LEGACY_TO_RCODE = {v["db_key"]: k for k, v in _STRATEGIES.items()}


def _resolve_code(token: str) -> tuple[str, str]:
    """(R-code, sfera db_key) for an R-code, a prod slot (S14), or legacy r_lev_*."""
    if token in _STRATEGIES:
        return token, _STRATEGIES[token]["db_key"]
    if token in _SLOT_TO_RCODE:
        rc = _SLOT_TO_RCODE[token]
        return rc, _STRATEGIES[rc]["db_key"]
    if token in _LEGACY_TO_RCODE:
        rc = _LEGACY_TO_RCODE[token]
        return rc, _STRATEGIES[rc]["db_key"]
    raise WeightLoadError(f"unknown strategy {token!r}")


# --- Single-instance run lock (prevents concurrent double-fire) --------------
_LOCK_PATH = Path.home() / ".blive" / "execute.lock"
_LOCK_STALE_SEC = 600  # a lock older than this = a crashed run; overridable


def _acquire_run_lock() -> bool:
    """Acquire the submit-path lock so two executor runs can't double-fire (e.g.
    the GUI button AND run_daily --execute, or a double-click). Returns False if
    a fresh lock is already held. FS errors never block execution."""
    try:
        _LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        if _LOCK_PATH.exists() and (time.time() - _LOCK_PATH.stat().st_mtime) < _LOCK_STALE_SEC:
            return False
        _LOCK_PATH.write_text(f"{os.getpid()} {datetime.now(tz=timezone.utc).isoformat()}")
        return True
    except Exception:  # noqa: BLE001 - never block execution on a lock FS error
        return True


def _release_run_lock() -> None:
    try:
        _LOCK_PATH.unlink(missing_ok=True)
    except Exception:  # noqa: BLE001
        pass


# --- Once-per-day execution guard (per account) ------------------------------
_EXEC_STATE_PATH = Path.home() / ".blive" / "last_execution.json"


def _executed_today(account: str) -> str | None:
    """Return the recorded time if this account already SUBMITTED today, else None."""
    try:
        rec = json.loads(_EXEC_STATE_PATH.read_text()).get(account)
        if rec and rec.get("date") == date.today().isoformat():
            return rec.get("time", "earlier today")
    except Exception:  # noqa: BLE001
        return None
    return None


def _load_executed_targets(account: str) -> dict[str, dict]:
    """{sleeve code: {identifier: rounded weight}} — the target each sleeve was LAST REBALANCED TO on this
    account. What the account actually holds, as far as the executor knows. Empty when nothing was ever
    recorded (callers fall back to the day-over-day comparison, and the first submit seeds it)."""
    try:
        rec = json.loads(_EXEC_STATE_PATH.read_text()).get(account) or {}
        return {k: dict(v) for k, v in (rec.get("sleeves") or {}).items()}
    except Exception:  # noqa: BLE001
        return {}


def _record_execution(account: str, plan: str, sleeves: dict[str, dict] | None = None) -> None:
    """Stamp the submit — and, per sleeve, the target it is now rebalanced to.

    That per-sleeve map is what makes a flip robust to WHEN the executor runs. The day-over-day test
    ("does today's row differ from yesterday's?") is true on exactly one morning after a month-end; miss
    it — a dry-run first, a skipped day, a deliberate choice to trade on the 5th rather than the 1st —
    and every later day reads "unchanged", hold_drift keeps the OLD book, and the rebalance is lost until
    the next month-end. Comparing against what the sleeve was last EXECUTED to is true every day until the
    trade actually happens. Only a submit writes this; a dry-run must never claim the account moved."""
    try:
        _EXEC_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if _EXEC_STATE_PATH.exists():
            try:
                data = json.loads(_EXEC_STATE_PATH.read_text())
            except Exception:  # noqa: BLE001
                data = {}
        prev = data.get(account) or {}
        merged = dict(prev.get("sleeves") or {})
        if sleeves:
            merged.update(sleeves)
        data[account] = {"date": date.today().isoformat(), "plan": plan,
                         "time": datetime.now(tz=timezone.utc).isoformat(), "sleeves": merged}
        _EXEC_STATE_PATH.write_text(json.dumps(data, indent=2))
    except Exception:  # noqa: BLE001
        pass

_DEFAULT_SFERA_ROOT = Path(
    r"C:\Personal\Business & Investments\Python codes\sfera"
)


# --- Weight sources ----------------------------------------------------------


class WeightLoadError(RuntimeError):
    """Raised when target weights cannot be loaded from the chosen source."""


def _normalise_long(df: pd.DataFrame, strategy: str, as_of: date | None) -> tuple[dict[str, Decimal], date]:
    """Long frame (date, identifier, weight[, strategy]) -> latest-or-as_of weights."""
    df = df.copy()
    if "strategy" in df.columns:
        df = df[df["strategy"].astype(str) == strategy]
    weight_col = "weight" if "weight" in df.columns else "value"
    if weight_col not in df.columns or "identifier" not in df.columns or "date" not in df.columns:
        raise WeightLoadError(
            f"weights frame missing required columns; got {list(df.columns)}"
        )
    df["date"] = pd.to_datetime(df["date"])
    if df.empty:
        raise WeightLoadError(f"no rows for strategy {strategy!r}")
    target_date = pd.Timestamp(as_of) if as_of else df["date"].max()
    rows = df[df["date"] == target_date]
    if rows.empty:
        raise WeightLoadError(f"no rows for strategy {strategy!r} on {target_date.date()}")
    weights = {
        str(r["identifier"]): Decimal(str(float(r[weight_col]))) for _, r in rows.iterrows()
    }
    return weights, target_date.date()


def load_weights_db(
    strategy: str, *, sfera_root: Path, as_of: date | None
) -> tuple[dict[str, Decimal], date, str]:
    """Read ``strategy.target_weights`` straight from the sfera Postgres.

    Connection coords are loaded from ``<sfera_root>/.env`` (DB_HOST/PORT/
    NAME/USER/PASSWORD) — the same values sfera's ``database_config`` reads —
    without importing the sfera package.
    """
    try:
        import psycopg  # local import: only the DB source needs it
        from dotenv import load_dotenv
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise WeightLoadError(
            "DB source needs 'psycopg' + 'python-dotenv' in the blive venv "
            "(pip install 'psycopg[binary]' python-dotenv), or use --source file"
        ) from exc

    env_path = Path(sfera_root) / ".env"
    if env_path.is_file():
        load_dotenv(env_path)
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "sfera")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    conn_str = f"host={host} port={port} dbname={dbname} user={user} password={password}"

    sql = (
        "SELECT date, identifier, weight FROM strategy.target_weights "
        "WHERE strategy = %s AND deprecated_at IS NULL"      # active SCD2 version only (skip superseded)
        + (" AND date = %s" if as_of else "") + " ORDER BY identifier"
    )
    params: tuple = (strategy, as_of) if as_of else (strategy,)
    try:
        with psycopg.connect(conn_str, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                if not as_of:
                    cur.execute(
                        "SELECT MAX(date) FROM strategy.target_weights "
                        "WHERE strategy = %s AND deprecated_at IS NULL",
                        (strategy,),
                    )
                    latest = cur.fetchone()[0]
                    if latest is None:
                        raise WeightLoadError(f"no rows for strategy {strategy!r} in DB")
                    cur.execute(sql.replace("ORDER BY", "AND date = %s ORDER BY"), (strategy, latest))
                else:
                    cur.execute(sql, params)
                fetched = cur.fetchall()
                cols = [d[0] for d in cur.description]
    except WeightLoadError:
        raise
    except Exception as exc:  # connection / query failure
        raise WeightLoadError(f"sfera DB read failed: {exc}") from exc

    frame = pd.DataFrame(fetched, columns=cols)
    weights, target_date = _normalise_long(frame, strategy, None)
    return weights, target_date, f"sfera.strategy.target_weights@{host}:{port}/{dbname}"


def load_weights_file(
    path: Path, strategy: str, *, as_of: date | None
) -> tuple[dict[str, Decimal], date, str]:
    """Read target weights from a parquet/CSV snapshot (fallback source)."""
    if not path.is_file():
        raise WeightLoadError(f"weights file not found: {path}")
    df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)
    weights, target_date = _normalise_long(df, strategy, as_of)
    return weights, target_date, f"file:{path.name}"


# --- Order construction ------------------------------------------------------


def _make_order(desired: Order, *, order_type: OrderType, tif: TimeInForce,
                limit_price: Decimal | None, label: str) -> Order:
    """Re-stamp a sized order with the chosen execution order_type + tif (+ limit)."""
    return Order(
        client_order_id=ClientOrderId(uuid4()),
        strategy_id=desired.strategy_id,
        instrument=desired.instrument,
        side=desired.side,
        quantity=desired.quantity,
        order_type=order_type,
        time_in_force=tif,
        limit_price=limit_price,
        stop_price=None,
        parent_id=None,
        tags={**desired.tags, "pipeline": label},
        created_at=desired.created_at,
    )


def _print_weights(weights: dict[str, Decimal], as_of: date, source: str) -> tuple[dict[str, Decimal], Decimal]:
    """Print the weight table, return (tradable target weights, cash residual)."""
    invested = sum((w for w in weights.values()), Decimal("0"))
    cash_residual = max(Decimal("0"), Decimal("1") - invested)
    print(f"\n=== target weights  (as-of {as_of}, source={source}) ===")
    tradable: dict[str, Decimal] = {}
    for sym, w in sorted(weights.items()):
        if sym in _NON_TRADABLE:
            note = "  (residual -> no order)"
        elif sym not in _CATALOGUE:
            note = "  <-- NOT in catalogue (will be skipped)"
        else:
            inst = _CATALOGUE[sym]
            note = f"  {inst.venue}/{inst.currency}"
            tradable[sym] = w
        held = "  *** HELD ***" if w > 0 else ""
        print(f"  {sym:6} {float(w):8.2%}{note}{held}")
    if cash_residual > 0:
        print(f"  {'CASH':6} {float(cash_residual):8.2%}  (residual -> no order)")
    return tradable, cash_residual


def _order_summary_rows(target_weights, prices, positions, orders, sym_origin, *, limit_band, is_limit):
    """Per-symbol rows for the structured orders table the GUI renders (strategy, side, qty, limit, notional).
    Orders carry the IB Instrument (BARE symbol, e.g. 'AKAST') — map it back to the EODHD identifier
    ('AKAST.OL') so every row keys on the SAME id as target_weights/prices/sym_origin (no bare-vs-dotted
    duplicate rows, and the strategy code from sym_origin lands on the right row)."""
    id_by_inst = {v: k for k, v in _CATALOGUE.items()}
    order_by_id = {id_by_inst.get(o.instrument, o.instrument.symbol): o for o in orders}
    rows = []
    for s in sorted(set(target_weights) | set(positions) | set(order_by_id)):
        w = float(target_weights.get(s, 0) or 0)
        px = float(prices.get(s, 0) or 0)                # LOCAL ccy close — the order/limit UNIT (NOK/DKK/GBX/…)
        pccy = _PRICE_CCY.get(s, "USD")
        usd_px = px * _usd_per_unit(pccy)                # per-leg FX -> USD (cached from sizing) for the NOTIONAL
        pos = float(positions[s].quantity) if s in positions else 0.0
        o = order_by_id.get(s)
        if o is None and abs(w) < 1e-9 and abs(pos) < 1e-9:
            continue                                     # skip pure-zero universe-fill rows (no order, no hold)
        if o is not None:
            side = str(o.side.value).upper()
            qty = float(o.quantity)
            lim = (px * (1 + limit_band) if side == "BUY" else px * (1 - limit_band)) if is_limit else None
            notional = qty * usd_px                       # USD notional (local price × per-leg FX)
        else:
            side = "HOLD" if pos else "FLAT"
            qty, lim, notional = 0.0, None, pos * usd_px
        rows.append({
            "strategy": "+".join(sym_origin.get(s, [])) or "—",
            "symbol": s, "weight": round(w, 4), "position": round(pos, 2),
            "price": round(px, 4), "price_ccy": pccy,     # local price + its ccy (limit is in this unit)
            "side": side, "order_qty": round(qty, 2),
            "limit_price": (round(lim, 4) if lim is not None else None),
            "notional_usd": round(notional, 2),
        })
    return rows


def _emit_orders_json(decision, reason, rows, **meta):
    """Print a machine-readable orders block the GUI parses into a table (harmless noise in the CLI)."""
    payload = {"decision": decision, "reason": reason, "rows": rows}
    payload.update(meta)
    print("\n===ORDERS_JSON===")
    print(json.dumps(payload, default=str))
    print("===END_ORDERS_JSON===")


# --- Detect-at-connect + execution ------------------------------------------


def _pg_conn_str(sfera_root: Path | None = None) -> str:
    """Postgres connection string for the shared sfera DB (env-driven)."""
    try:
        from dotenv import load_dotenv
        if sfera_root is not None:
            ep = Path(sfera_root) / ".env"
            if ep.is_file():
                load_dotenv(ep)
    except ImportError:  # pragma: no cover
        pass
    return (
        f"host={os.getenv('DB_HOST','localhost')} port={os.getenv('DB_PORT','5432')} "
        f"dbname={os.getenv('DB_NAME','sfera')} user={os.getenv('DB_USER','postgres')} "
        f"password={os.getenv('DB_PASSWORD','')}"
    )


def _sleeve_universe(db_key: str, sfera_root: Path | None = None) -> set[str]:
    """Every identifier this strategy has EVER targeted (its own asset universe), from strategy.target_weights.
    Used to attribute a HELD position on a shared/blended account back to the sleeve that owns it — so a held
    leg no longer in today's target (a rotated-away name) is still recognised as belonging to its sleeve, and
    the per-sleeve buy-and-hold decision is robust. CASH is not an asset. Empty on any DB error (safe fallback)."""
    try:
        import psycopg
        with psycopg.connect(_pg_conn_str(sfera_root), connect_timeout=5) as conn, conn.cursor() as cur:
            cur.execute("SELECT DISTINCT identifier FROM strategy.target_weights WHERE strategy=%s", (db_key,))
            return {r[0] for r in cur.fetchall() if r[0] and r[0] != "CASH"}
    except Exception:  # noqa: BLE001 - fall back to today's sym_origin attribution
        return set()


def _sleeve_prev_map(db_key: str, ref_date, sfera_root: Path | None = None) -> dict | None:
    """The strategy's OWN (identifier -> rounded weight) map on its most recent stored date BEFORE ref_date —
    i.e. what this sleeve was holding going into today. None when there is no prior history or the DB cannot
    be read (callers treat None as 'unknown', never as 'held nothing')."""
    try:
        import psycopg
        with psycopg.connect(_pg_conn_str(sfera_root), connect_timeout=5) as conn, conn.cursor() as cur:
            cur.execute("SELECT MAX(date) FROM strategy.target_weights "
                        "WHERE strategy=%s AND deprecated_at IS NULL AND date < %s", (db_key, ref_date))
            prev = cur.fetchone()[0]
            if prev is None:
                return None
            cur.execute("SELECT identifier, weight FROM strategy.target_weights "
                        "WHERE strategy=%s AND date=%s AND deprecated_at IS NULL AND weight<>0", (db_key, prev))
            return {r[0]: round(float(r[1]), 4) for r in cur.fetchall() if r[0] != "CASH"}
    except Exception:  # noqa: BLE001
        return None


def _sleeve_flipped(db_key: str, ref_date, today_map: dict, sfera_root: Path | None = None) -> bool:
    """Did THIS strategy's OWN target change vs its previous stored date? The robust per-sleeve flip signal:
    it compares the strategy's own (identifier -> rounded weight) map today against the most recent prior date
    in strategy.target_weights — completely independent of the shared/blended account (so R02 and R04 sharing a
    US-ETF universe is a non-issue). A stable single-asset sleeve (R02={TQQQ:1}, R04={BIL:1} every day) is NOT
    flipped -> HELD; a book whose composition/gate changed (R05) IS flipped -> rebalanced. No prior history ->
    not flipped (hold). DB error -> flipped (degrade to the old full-rebalance rather than freeze trading)."""
    prev_map = _sleeve_prev_map(db_key, ref_date, sfera_root)
    if prev_map is None:
        # distinguish "no history" (hold) from "DB error" (rebalance): re-probe cheaply
        try:
            import psycopg
            with psycopg.connect(_pg_conn_str(sfera_root), connect_timeout=5) as conn, conn.cursor() as cur:
                cur.execute("SELECT 1 FROM strategy.target_weights WHERE strategy=%s AND date < %s LIMIT 1",
                            (db_key, ref_date))
                return False if cur.fetchone() is None else True
        except Exception:  # noqa: BLE001 - can't compare -> don't silently freeze; fall back to rebalance
            return True
    return prev_map != today_map


# per-symbol EODHD price currency (e.g. GBX for LSE pence) — used to convert the sfera EOD close to USD.
_PRICE_CCY: dict[str, str] = {}
_FX_CACHE: dict[str, float] = {}


def _usd_per_unit(ccy: str, sfera_root: Path | None = None) -> float:
    """USD value of 1 unit of ``ccy`` from ``yfmktdt.fx_rates`` (USD-anchored legs). USD→1.0; GBX→GBP/100
    (LSE pence). Cached per process."""
    c = (ccy or "USD").upper()
    if c == "USD":
        return 1.0
    if c in _FX_CACHE:
        return _FX_CACHE[c]
    if c == "GBX":                                       # London pence -> pounds -> USD
        val = _usd_per_unit("GBP", sfera_root) / 100.0
        _FX_CACHE[c] = val
        return val
    val = 1.0
    try:
        import psycopg
        with psycopg.connect(_pg_conn_str(sfera_root), connect_timeout=5) as conn, conn.cursor() as cur:
            cur.execute("SELECT rate FROM yfmktdt.fx_rates WHERE pair=%s AND deprecated_at IS NULL "
                        "ORDER BY trade_date DESC LIMIT 1", (c + "USD",))
            r = cur.fetchone()
            if r and r[0]:
                val = float(r[0])                        # XXXUSD leg: rate = USD per 1 unit
            else:
                cur.execute("SELECT rate FROM yfmktdt.fx_rates WHERE pair=%s AND deprecated_at IS NULL "
                            "ORDER BY trade_date DESC LIMIT 1", ("USD" + c,))
                r = cur.fetchone()
                if r and r[0]:
                    val = 1.0 / float(r[0])              # USDXXX leg: rate = units per USD -> invert
    except Exception:  # noqa: BLE001
        pass
    _FX_CACHE[c] = val
    return val


def _sfera_last_close(symbols: list[str], sfera_root: Path) -> dict[str, Decimal]:
    """Latest EOD close from sfera (LOCAL ccy). US tickers → ``yfmktdt.stock_prices``; EU 'TICKER.EXCH'
    → ``eodhd.prices`` by (ticker, exchange). Used when IB market data isn't permitted (EU venues) so
    sizing + limit bands can still proceed off yesterday's close — never the execution price itself.
    """
    try:
        import psycopg
    except ImportError:  # pragma: no cover
        return {}
    out: dict[str, Decimal] = {}
    try:
        with psycopg.connect(_pg_conn_str(sfera_root), connect_timeout=5) as conn:
            with conn.cursor() as cur:
                for sym in symbols:
                    if "." in sym:                       # EU single-name: eodhd.prices (local ccy)
                        tk, _, ex = sym.rpartition(".")
                        cur.execute("SELECT close_price FROM eodhd.prices WHERE ticker=%s AND exchange=%s "
                                    "AND deprecated_at IS NULL ORDER BY trade_date DESC LIMIT 1", (tk, ex))
                    else:                                # US: yfmktdt.stock_prices
                        cur.execute("SELECT close_price FROM yfmktdt.stock_prices WHERE ticker=%s "
                                    "ORDER BY trade_date DESC LIMIT 1", (sym,))
                    row = cur.fetchone()
                    if row and row[0] is not None:
                        out[sym] = Decimal(str(float(row[0])))
    except Exception:  # noqa: BLE001 - fallback is best-effort
        return out
    return out


async def _probe_eligibility_and_price(
    market_data: IBMarketData,
    resolver: IBInstrumentResolver,
    symbols: list[str],
    sfera_root: Path,
) -> tuple[dict[str, Decimal], dict[str, str], dict[str, str], list[str]]:
    """Detect-at-connect, done right — eligibility separate from price.

    Eligibility = contract qualification (``resolver.resolve`` ->
    ``qualifyContractsAsync``), which is INDEPENDENT of market data. A symbol is
    BLOCKED only when IB cannot qualify the contract (genuinely unavailable /
    not permitted). The price is fetched separately: IB historical bars first,
    falling back to sfera's last close when IB market data is unavailable (e.g.
    error 162 session contention). This stops a market-data/session hiccup from
    masquerading as an eligibility block (the bug that flagged TQQQ/IEF — which
    the account demonstrably holds — as "BLOCKED").

    Returns (prices, price_source, blocked_reason, eligible_symbols).
    """
    blocked: dict[str, str] = {}
    eligible: list[str] = []
    for sym in symbols:
        try:
            await resolver.resolve(_CATALOGUE[sym])
            eligible.append(sym)
        except InstrumentNotResolvable as exc:
            blocked[sym] = f"contract not tradable: {str(exc).splitlines()[0][:120]}"
        except Exception as exc:  # noqa: BLE001 - surface any resolve failure
            blocked[sym] = f"resolve failed: {str(exc).splitlines()[0][:120]}"

    prices: dict[str, Decimal] = {}
    price_src: dict[str, str] = {}
    last_bars: dict[str, Bar] = {}
    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=7)
    need_fallback: list[str] = []
    for sym in eligible:
        # EU single-name equities: this account has no IB market-data permission for those venues, so an
        # IB historical_bars call just eats a ~15s timeout before failing. Skip IB entirely and price them
        # off sfera's eodhd EOD close (yesterday) — markets are closed anyway; the close is the right
        # reference for sizing + limit bands, and the fill happens at the next open.
        if sym in _PRICE_CCY:
            need_fallback.append(sym)
            continue
        try:
            bars = await market_data.historical_bars(_CATALOGUE[sym], freq="1d", start=start, end=end)
            if bars:
                prices[sym] = bars[-1].close
                price_src[sym] = "IB"
                last_bars[sym] = bars[-1]
            else:
                need_fallback.append(sym)
        except Exception:  # noqa: BLE001 - IB MD failure -> sfera fallback
            need_fallback.append(sym)
    if need_fallback:
        for sym, px in _sfera_last_close(need_fallback, sfera_root).items():
            prices[sym] = px
            price_src[sym] = "sfera-close"
            last_bars[sym] = Bar(instrument=_CATALOGUE[sym],
                                 open_time_utc=end - timedelta(days=1), close_time_utc=end,
                                 open=px, high=px, low=px, close=px, volume=Decimal("0"))
    return prices, price_src, blocked, eligible, last_bars


async def _fx_base_to_usd(broker: IBBroker, base_ccy: str) -> tuple[Decimal, str]:
    """Rate to convert the account base currency into USD (the instrument ccy).

    All sfera legs are USD ETFs; the account may be GBP-denominated, so a budget
    (or nav-slice of equity) expressed in the base currency must be converted to
    USD before sizing — otherwise positions come out ~1/fx undersized. Primary
    source is IB's reported ``ExchangeRate`` account value (currency -> base);
    falls back to a GBPUSD forex spot, then to 1.0 with a loud warning.
    """
    if base_ccy.upper() == "USD":
        return Decimal("1"), "base=USD"
    try:
        for av in broker._client.ib.accountValues():  # noqa: SLF001 - script-level access
            if av.tag == "ExchangeRate" and av.currency == "USD":
                rate = Decimal(str(av.value))  # GBP per 1 USD (USD -> base)
                if rate > 0:
                    return (Decimal("1") / rate), f"IB ExchangeRate(USD)={rate}"
    except Exception:  # noqa: BLE001 - best-effort
        pass
    if base_ccy.upper() == "GBP":
        try:
            import ib_async

            bars = await broker._client.ib.reqHistoricalDataAsync(  # noqa: SLF001
                ib_async.Forex("GBPUSD"), endDateTime="", durationStr="3 D",
                barSizeSetting="1 day", whatToShow="MIDPOINT", useRTH=False,
            )
            if bars:
                return Decimal(str(bars[-1].close)), "IB GBPUSD spot"
        except Exception:  # noqa: BLE001
            pass
    return Decimal("1"), "FX UNAVAILABLE -> treating budget as USD (CALIBRATE!)"


async def _run(args: argparse.Namespace) -> int:
    # --- 1. Load target weights (single strategy OR blended portfolio) ------
    as_of = date.fromisoformat(args.as_of) if args.as_of else None

    def _load_one(dbk: str):
        if args.source == "file":
            return load_weights_file(Path(args.weights_path), dbk, as_of=as_of)
        return load_weights_db(dbk, sfera_root=Path(args.sfera_root), as_of=as_of)

    if args.portfolio:
        # Blend MULTIPLE strategies on ONE account into a combined target. The
        # weight blend is budget-weighted and FX-independent:
        #   combined_weight[i] = sum_s(budget_s * weight_s[i]) / sum_s budget_s ;
        #   total pot = sum_s budget_s.
        # This is the correct way to run >1 strategy on a single account that
        # shares instruments — a per-strategy delta-sizer would otherwise fight
        # over the shared position. (Per-strategy P&L attribution needs a
        # separate ledger — future.)
        try:
            plan = json.loads(args.portfolio)
            combined: dict[str, Decimal] = {}
            sym_origin: dict[str, list[str]] = {}   # which strategy contributed each symbol (per-order attribution)
            sleeve_universes: dict[str, set] = {}   # code -> assets it has EVER targeted (held-leg attribution)
            sleeve_flip: dict[str, bool] = {}       # code -> did ITS OWN target change vs prev date (per-sleeve flip)
            # code -> drift tolerance for THAT sleeve (weight points of the book), overriding --rebalance-band.
            # One band cannot serve every sleeve: R05 is 14 small low-vol legs where 0.5pp cleanly separates
            # "never established" from "drifted", but R02 is ONE leg at 25% of the book in a 3x-levered ETF whose
            # ordinary 3% day is already 0.75pp — so a global 0.5pp band had it buying every dip and selling
            # every rally, a contrarian overlay the backtest never had. A hold-until-flip sleeve wants a band so
            # wide that only a signal flip or an empty position can move it.
            sleeve_band: dict[str, float] = {}
            # Sleeves that NEVER trade on drift: a single-asset hold-until-flip book (R02 in TQQQ, R04 in BIL)
            # rides its asset until its own signal flips. Price and FX moving its value are the strategy's
            # return, not deviation. Only an EMPTY position (establishment) or a flip can move it. This is a
            # rule, not a very wide band — "within ±100% of book weight" would be the same behaviour wearing
            # a ridiculous number.
            sleeve_hold_drift: set[str] = set()
            # Kept for the ROTATION re-blend below (after positions and prices are known): each sleeve's
            # allocated budget, today's own weights, and what it was holding going into today. A sleeve that
            # flips is re-sized to the market value of what it HELD, not to its original budget — so it
            # carries its own P&L and FX into the next asset instead of resetting to the allocation.
            sleeve_budget: dict[str, Decimal] = {}
            sleeve_weights: dict[str, dict] = {}
            sleeve_prev: dict[str, dict | None] = {}
            sleeve_today: dict[str, dict] = {}         # code -> today's rounded map (for the executed-state flip test)
            total_budget = Decimal("0")
            oldest: date | None = None
            labels: list[str] = []
            for item in plan:
                code_i, dbk_i = _resolve_code(str(item["strategy"]))
                b = Decimal(str(item["budget"]))
                if item.get("band") is not None:
                    sleeve_band[code_i] = float(item["band"])
                if item.get("hold_drift"):
                    sleeve_hold_drift.add(code_i)
                w_i, d_i, _ = _load_one(dbk_i)
                _tmap = {s: round(float(wt), 4) for s, wt in w_i.items() if wt != 0 and s != "CASH"}
                sleeve_universes[code_i] = _sleeve_universe(dbk_i, Path(args.sfera_root)) or set(_tmap)
                sleeve_flip[code_i] = _sleeve_flipped(dbk_i, d_i, _tmap, Path(args.sfera_root))
                sleeve_budget[code_i] = b
                sleeve_weights[code_i] = {s: wt for s, wt in w_i.items() if s != "CASH"}
                sleeve_prev[code_i] = _sleeve_prev_map(dbk_i, d_i, Path(args.sfera_root))
                sleeve_today[code_i] = _tmap
                for sym, wt in w_i.items():
                    combined[sym] = combined.get(sym, Decimal("0")) + b * wt
                    if wt != 0 and code_i not in sym_origin.get(sym, []):
                        sym_origin.setdefault(sym, []).append(code_i)
                total_budget += b
                oldest = d_i if oldest is None else min(oldest, d_i)
                labels.append(f"{code_i} {float(b):,.0f}")
            if total_budget <= 0:
                print("\nFAILED: portfolio total budget must be > 0")
                return 2
            weights = {sym: (notional / total_budget) for sym, notional in combined.items()}
            signal_date = oldest  # type: ignore[assignment]
            source = "portfolio[" + " + ".join(labels) + "]"
            code, db_key = "PORTFOLIO", "portfolio"
            args.budget = float(total_budget)
            print(f"  PORTFOLIO: {' + '.join(labels)}  (total budget {float(total_budget):,.0f})")
        except WeightLoadError as exc:
            print(f"\nFAILED building portfolio: {exc}")
            return 2
        except Exception as exc:  # noqa: BLE001 - bad JSON / keys
            print(f"\nFAILED parsing --portfolio: {exc}")
            return 2
    else:
        try:
            code, db_key = _resolve_code(args.strategy)
        except WeightLoadError:
            print(f"\nFAILED: unknown strategy {args.strategy!r}; known: {', '.join(sorted(_STRATEGIES))}")
            return 2
        meta = _STRATEGIES[code]
        slot = f" (slot {meta['slot']})" if meta["slot"] else ""
        print(f"  strategy: {code}{slot} - {meta['name']}  (sfera key: {db_key})")
        try:
            weights, signal_date, source = _load_one(db_key)
        except WeightLoadError as exc:
            print(f"\nFAILED: {exc}")
            return 2
        sym_origin = {s: [code] for s in weights}   # single strategy -> every symbol attributes to it
        _tmap = {s: round(float(w), 4) for s, w in weights.items() if w != 0 and s != "CASH"}
        sleeve_universes = {code: (_sleeve_universe(db_key, Path(args.sfera_root)) or set(_tmap))}
        sleeve_flip = {code: _sleeve_flipped(db_key, signal_date, _tmap, Path(args.sfera_root))}
        sleeve_band = {}                              # single-strategy run: --rebalance-band applies as-is
        sleeve_hold_drift = set()
        sleeve_budget, sleeve_weights, sleeve_prev = {}, {}, {}   # rotation re-blend is portfolio-mode only
        sleeve_today = {code: _tmap}

    _ensure_eu_instruments(weights, Path(args.sfera_root))   # register EU equities (R05) in _CATALOGUE before sizing
    tradable_targets, cash_residual = _print_weights(weights, signal_date, source)
    if not tradable_targets:
        print("\nNo tradable (catalogued) legs in today's target — fully CASH / out-of-universe.")
        # Still meaningful: a live run would flatten held legs. Offline, nothing to do.

    # Freshness guard — don't act on stale weights (e.g. today's pipeline hasn't run).
    today = datetime.now(tz=timezone.utc).date()
    staleness = (today - signal_date).days
    stale = staleness > args.max_staleness_days
    if stale:
        print(f"\n  WARNING STALE: weights are {staleness}d old (as-of {signal_date}; "
              f"max {args.max_staleness_days}d). Compute today's signals first — "
              f"--submit will refuse unless --force-stale.")

    # Execution policy. MOO/MKT = market orders (always fill, NO price protection).
    # LOO/LMT = LIMIT orders with a band around the reference price: LOO fills at
    # the open within the band else cancels; LMT works the day and STAYS PENDING
    # if the price never enters the band. Both stop a runaway open from filling
    # at an absurd price.
    _POLICY = {
        "MOO": (OrderType.MKT, TimeInForce.OPG, False),
        "MKT": (OrderType.MKT, TimeInForce.DAY, False),
        "LOO": (OrderType.LMT, TimeInForce.OPG, True),
        "LMT": (OrderType.LMT, TimeInForce.DAY, True),
    }
    order_type, tif, is_limit = _POLICY[args.order_type]
    band = Decimal(str(args.limit_band))
    print(f"\n  order plan: {args.order_type}  (IB {order_type.value} tif={tif.value}"
          + (f", limit band ±{float(band):.1%}" if is_limit else "") + ")")

    # --- 2. Offline preview short-circuit -----------------------------------
    if args.offline:
        pot = args.budget if args.budget > 0 else args.example_equity * args.nav_slice
        basis = (f"budget ${args.budget:,.0f}" if args.budget > 0
                 else f"nav_slice {args.nav_slice:.0%} x example equity ${args.example_equity:,.0f}")
        print(f"\n=== OFFLINE preview (no IB) - {basis} -> ${pot:,.0f} deployable ===")
        for sym, w in tradable_targets.items():
            if w > 0:
                print(f"    {sym}: target ${float(w) * pot:,.0f}  (shares at execution from live IB price)")
        print("\n  (offline: FX, live equity, eligibility, prices and orders require IB Gateway up)")
        return 0

    # --- 3. Connect to IB (detect-at-connect) -------------------------------
    try:
        credentials = IBCredentials.load()
    except (CredentialsMissing, ValueError) as exc:
        print(f"\nFAILED: IB credentials: {exc}")
        return 2

    # --- FLIP = "target differs from what this sleeve was LAST REBALANCED TO on this account" ---------------
    # The day-over-day test above is only a fallback. It is true on exactly one morning after a month-end;
    # if the executor does not SUBMIT that morning (dry-run first, skipped day, a deliberate choice to
    # trade on the 5th rather than the 1st) every later day reads "unchanged", hold_drift keeps the OLD
    # book — dropped names never sold, resized names never resized — and the rebalance is lost until the
    # next month-end. Against the last-executed target the flip stays true every day until it is actually
    # traded. The same map is what the sleeve HOLDS going into today, so the rotation re-blend values the
    # right positions even when execution is late (yesterday's ROW is already the new target by then).
    _executed = _load_executed_targets(credentials.account_id)
    for _c, _tm in sleeve_today.items():
        if _c in _executed:
            _was = sleeve_flip.get(_c)
            sleeve_flip[_c] = (_tm != _executed[_c])
            if _c in sleeve_prev:
                sleeve_prev[_c] = dict(_executed[_c])
            if sleeve_flip[_c] != _was:
                print(f"  FLIP {_c}: {'PENDING — target differs from the last EXECUTED book (not yet traded)' if sleeve_flip[_c] else 'cleared — target already executed'}"
                      f"{'' if sleeve_flip[_c] else ' (day-over-day test disagreed; executed state wins)'}")
    if not _executed:
        print("  (no executed-target state for this account yet — flips judged day-over-day; "
              "the first submit records every sleeve's book)")

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
        print("  (is IB Gateway running on the configured host/port, paper, API enabled?)")
        return 3
    print(f"  connected: {broker.is_connected}")
    await _drain_startup_events(broker)

    snap = await broker.account_snapshot()
    equity = snap.equity
    print("\n=== Account snapshot (detect-at-connect) ===")
    print(f"  Account:  {credentials.account_id}")
    print(f"  Currency: {snap.base_currency}")
    print(f"  Equity:   {snap.base_currency} {float(equity):,.2f}")
    if snap.base_currency and snap.base_currency.upper() != "USD":
        print(
            f"  NOTE: base currency is {snap.base_currency}, not USD. The sfera universe is "
            "US ETFs — check the eligibility report below for PRIIPs/permission blocks."
        )

    ib_positions = await broker.positions()
    # Re-key held positions by OUR ticker via IB conId. IB reports EU holdings under its OWN symbols
    # (AKAST.OL -> "AKAST", BP.LSE -> "BP.", TRMD-A.CO -> "TRMD.A") which DON'T match our target tickers,
    # so a raw-symbol key makes the sizer think the book is unheld and DOUBLE-BUYS it. conId is the stable
    # identity (the same one that opened the position), so each held leg maps back onto its target.
    _sym_conid = {getattr(rp.contract, "symbol", ""): int(getattr(rp.contract, "conId", 0) or 0)
                  for rp in client.ib.positions() if getattr(rp.contract, "conId", 0)}
    _conid_ticker: dict[int, str] = {}
    for _s in weights:
        _inst = _CATALOGUE.get(_s)
        if _inst is None:
            continue
        try:
            _conid_ticker[await resolver.resolve(_inst)] = _s   # cached; the eligibility probe reuses it
        except Exception:  # noqa: BLE001 - an unresolved leg just stays under its IB symbol
            pass
    positions: dict[str, Position] = {}
    for p in ib_positions:
        _cid = _sym_conid.get(p.instrument.symbol)
        positions[(_conid_ticker.get(_cid) if _cid else None) or p.instrument.symbol] = p
    print(f"  Open positions: {list(positions.keys()) or '(none)'}")

    # PENDING orders too — fold into the effective current state so sizing validates against positions
    # PLUS in-flight orders (else a not-yet-filled order is ignored and re-issued). Key by IB *conId*,
    # NOT the ticker string: IB names some contracts differently from our EODHD ticker (BP.LSE -> "BP.",
    # TRMD-A.CO -> "TRMD.A"), so a symbol match silently misses them and DOUBLE-orders on a re-run. conId
    # is the stable identity the resolver already resolves/caches to, so pending + candidates net on it.
    await client.rate_limiter.acquire("global")                 # mirror broker.open_orders() throttle
    pending_net: dict[int, Decimal] = {}
    pending_disp: dict[int, str] = {}
    for t in await client.ib.reqAllOpenOrdersAsync():           # raw IB trades carry conId; domain Order does not
        if t is None or getattr(t, "contract", None) is None:
            continue
        conid = int(getattr(t.contract, "conId", 0) or 0)
        if not conid:
            continue
        rem = getattr(t.orderStatus, "remaining", None)
        qty = Decimal(str(rem if rem else (getattr(t.order, "totalQuantity", 0) or 0)))
        signed = qty if str(getattr(t.order, "action", "")).upper() == "BUY" else -qty
        pending_net[conid] = pending_net.get(conid, Decimal("0")) + signed
        pending_disp[conid] = getattr(t.contract, "symbol", "") or str(conid)
    if pending_net:
        print("  Pending orders (net qty): "
              + ", ".join(f"{pending_disp[c]} {float(q):+.0f}"
                          for c, q in sorted(pending_net.items(), key=lambda kv: pending_disp[kv[0]])))

    # Probe the union of today's tradable targets and any held catalogue legs
    # (held-but-not-target legs must be price-known so the sizer can flatten them).
    probe_syms = sorted(set(tradable_targets) | (set(positions) & set(_CATALOGUE)))
    print("\n=== Instrument eligibility + prices ===")
    prices, price_src, blocked, eligible, last_bars = await _probe_eligibility_and_price(
        market_data, resolver, probe_syms, Path(args.sfera_root)
    )
    for sym in probe_syms:
        if sym in prices:
            print(f"  {sym:6} ELIGIBLE   ${float(prices[sym]):>9.4f}  (price: {price_src[sym]})")
        elif sym in eligible:
            print(f"  {sym:6} ELIGIBLE   (no price: IB MD + sfera fallback both unavailable — can't size)")
        else:
            print(f"  {sym:6} BLOCKED    {blocked.get(sym, 'unknown')}")

    eligible_target_syms = [s for s in tradable_targets if s in eligible]
    priced_targets = {s: w for s, w in tradable_targets.items() if s in prices}
    if tradable_targets and not eligible_target_syms:
        print(
            "\nFAILED: none of today's target instruments can be qualified on this account "
            "(contract qualify failed) — a genuine availability / jurisdiction block."
        )
        await broker.disconnect()
        return 4
    if tradable_targets and not priced_targets:
        print(
            "\nFAILED: targets are tradable but no price is available (IB market data down "
            "and sfera fallback empty) — cannot size. Fix the IB session/MD or the sfera price feed."
        )
        await broker.disconnect()
        return 5

    # --- 4. Size orders (full rebalance to target) --------------------------
    # Build a target over the full eligible universe (held legs not in target -> 0).
    target_weights: dict[str, Decimal] = {s: Decimal("0") for s in prices}
    target_weights.update({s: w for s, w in priced_targets.items()})

    base_ccy = snap.base_currency or "USD"
    fx, fx_src = await _fx_base_to_usd(broker, base_ccy)
    bccy = str(getattr(args, "budget_ccy", "base")).lower()
    sroot = Path(args.sfera_root)
    _id_by_inst = {v: k for k, v in _CATALOGUE.items()}      # Instrument -> its EODHD identifier (prices key)

    def _px_usd(sym: str) -> Decimal:
        """A leg's price in USD via PER-LEG FX: local EOD close (in _PRICE_CCY[sym], incl. GBX pence) ×
        USD-per-unit from yfmktdt.fx_rates. R05 is multi-ccy (NOK/DKK/EUR/GBP); US legs stay USD (×1)."""
        pc = _PRICE_CCY.get(sym) or getattr(_CATALOGUE.get(sym, None), "currency", "USD")
        return prices[sym] * Decimal(str(_usd_per_unit(pc, sroot)))

    # --- ROTATION RE-BLEND: a sleeve that flips is sized to what it HELD, not to its original budget ----------
    # Capital is committed to a sleeve once and then RIDES: its value floats with its asset's price and, for a
    # USD holding in a GBP account, with GBPUSD. Between flips the drift band keeps that untouched. At a FLIP the
    # question is "how much does this sleeve have to put into the new asset?" — and the honest answer is the
    # market value of what it is rotating OUT of, valued now with per-leg FX. Sizing the new asset to the fixed
    # budget instead threw the sleeve's own P&L away every rotation: a sleeve that had grown to GBP 58k bought
    # GBP 50k of the new asset and dumped 8k to cash; one that had shrunk was topped up from nowhere. Neither is
    # the backtest, which compounds.
    # So for each flipped sleeve, value yesterday's holdings (its prev weights say what was its; a leg two
    # sleeves both held is split pro-rata by budget x prev weight) and use that as its budget in the blend.
    # STAGE 1 LIMIT: a sleeve that was sitting in CASH yesterday (an empty prev map) has no holdings to value
    # and keeps its budget — sleeve cash is not attributed yet (that is the per-sleeve NAV ledger, stage 2).
    if sleeve_prev and any(sleeve_flip.get(c) for c in sleeve_prev):
        def _sleeve_mv_usd(code_x: str) -> Decimal:
            prev_x = sleeve_prev.get(code_x) or {}
            mv = Decimal("0")
            for sym, pw in prev_x.items():
                if sym not in positions or not pw:
                    continue
                claims = {c: sleeve_budget[c] * Decimal(str(abs(sleeve_prev[c].get(sym, 0.0))))
                          for c in sleeve_prev if sleeve_prev[c] and sleeve_prev[c].get(sym)}
                den = sum(claims.values(), Decimal("0"))
                frac = (claims[code_x] / den) if den > 0 else Decimal("1")
                try:
                    mv += positions[sym].quantity * _px_usd(sym) * frac
                except Exception:  # noqa: BLE001 - an unpriceable leg contributes nothing, never blocks
                    pass
            return mv
        new_budget = dict(sleeve_budget)
        for code_x, flipped in sleeve_flip.items():
            if not flipped or code_x not in sleeve_budget:
                continue
            mv_usd = _sleeve_mv_usd(code_x)
            if mv_usd <= 0:
                print(f"  ROTATION {code_x}: no valued holdings going into today (was in cash?) -> "
                      f"sizing to its budget {float(sleeve_budget[code_x]):,.0f} {base_ccy}")
                continue
            mv_base = (mv_usd / fx).quantize(Decimal("0.01")) if fx else mv_usd
            print(f"  ROTATION {code_x}: sizing the new book to what it HELD — ${float(mv_usd):,.0f} = "
                  f"{float(mv_base):,.0f} {base_ccy} (budget was {float(sleeve_budget[code_x]):,.0f}, "
                  f"{float(mv_base / sleeve_budget[code_x] - 1):+.1%})")
            new_budget[code_x] = mv_base
        if new_budget != sleeve_budget:
            new_total = sum(new_budget.values(), Decimal("0"))
            if new_total > 0:
                for sym in list(target_weights):
                    target_weights[sym] = sum((new_budget[c] * Decimal(str(sleeve_weights[c].get(sym, 0)))
                                               for c in new_budget), Decimal("0")) / new_total
                args.budget = float(new_total)
                print(f"  ROTATION: blended pot {float(sum(sleeve_budget.values())):,.0f} -> "
                      f"{float(new_total):,.0f} {base_ccy}; blend weights re-derived")

    # HOLDINGS basis: size against the current market value of what you ALREADY HOLD (mark-to-market, USD).
    size_basis = str(getattr(args, "size_basis", "budget")).lower()
    held_mv_usd = sum((positions[s].quantity * _px_usd(s)                      # THIS strategy's own sleeve only
                       for s in prices if s in positions and s in weights), Decimal("0"))
    fx_applied = False    # does the pot->USD sizing multiply by FX? (per-leg prices are ALWAYS USD-normalised)
    if size_basis == "holdings" and held_mv_usd > 0:
        pot_base = held_mv_usd
        pot_usd = held_mv_usd.quantize(Decimal("0.01"))          # holdings MV, per-leg FX already applied
        pot_label = f"holdings MV ${float(pot_usd):,.0f} USD (mark-to-market, per-leg FX)"
    elif args.budget and args.budget > 0:
        pot_base = Decimal(str(args.budget))
        if bccy == "usd":
            pot_usd = pot_base.quantize(Decimal("0.01"))          # budget already USD
            pot_label = f"budget ${float(pot_base):,.0f} USD (source-ccy)"
        elif bccy == "base":
            pot_usd = (pot_base * fx).quantize(Decimal("0.01")); fx_applied = True
            pot_label = f"budget {float(pot_base):,.0f} {base_ccy} x FX {float(fx):.4f}"
        else:                                                     # explicit budget ccy (e.g. EUR) via fx_rates
            u = Decimal(str(_usd_per_unit(bccy.upper(), sroot)))
            pot_usd = (pot_base * u).quantize(Decimal("0.01")); fx_applied = True
            pot_label = f"budget {float(pot_base):,.0f} {bccy.upper()} x {float(u):.4f}->USD"
    else:
        pot_base = equity * Decimal(str(args.nav_slice))
        pot_usd = (pot_base * fx).quantize(Decimal("0.01")); fx_applied = True
        pot_label = f"nav_slice {args.nav_slice:.1%} x {float(equity):,.0f} {base_ccy} = {float(pot_base):,.0f} {base_ccy}"
        fx_applied = True
    # AUM model: budget = allocated AUM; weights deploy within it. Strategies may
    # LEVER beyond AUM (e.g. R04 COT washout -> leg weight up to 1.5x, BIL floored
    # at 0) so a weight can exceed 1.0. The pure sizer caps |weight| <= 1, so we
    # pre-scale: inflate the pot by the max leg weight and normalise weights into
    # [-1, 1]. Per-leg notional (pot_usd * weight) is preserved exactly, and
    # sum(weight) > 1 then deploys > AUM on margin — the intended leverage.
    max_w = max((abs(w) for w in target_weights.values()), default=Decimal("1"))
    lev = max(Decimal("1"), max_w)
    size_equity = (pot_usd * lev).quantize(Decimal("0.01"))
    size_weights = (
        {k: (w / lev) for k, w in target_weights.items()} if lev > 1 else target_weights
    )
    lev_note = f";  leverage {float(lev):.2f}x (deploys > AUM on margin)" if lev > 1 else ""
    fx_note = (f"FX {base_ccy}->USD {float(fx):.4f} [{fx_src}] APPLIED" if fx_applied
               else f"FX {base_ccy}->USD {float(fx):.4f} [{fx_src}] — REF ONLY, NOT applied (pure USD sizing)")
    print(
        f"\n=== Sizing ({pot_label};  {fx_note};  "
        f"AUM ${float(pot_usd):,.2f}{lev_note}) ==="
    )
    sizer_in = SizerInput(
        target_weights=size_weights,
        equity=size_equity,
        nav_slice=Decimal("1"),
        # ONLY this strategy's OWN sleeve: manage positions it actually targets (s in weights). On a SHARED
        # paper account, a position outside this strategy's book (e.g. R02's TQQQ, R04's BIL when running R05)
        # is INVISIBLE — never flattened. Each strategy sizes against ITS allocated AUM, not a % of the whole
        # account (ForgeFolio model). Foreign holdings are left exactly as-is.
        current_positions={s: positions[s] for s in positions if s in prices and s in weights},
        instrument_resolver=lambda sym: _CATALOGUE[sym],
        price_lookup=lambda inst: _px_usd(_id_by_inst.get(inst, inst.symbol)),   # USD (per-leg FX) for sizing
        strategy_id=code,
        now=datetime.now(tz=timezone.utc),
    )
    try:
        candidate_orders = size_orders(sizer_in)
    except Exception as exc:
        print(f"\nFAILED in sizer: {exc}")
        await broker.disconnect()
        return 5

    # Net each sized delta against in-flight pending orders: residual = what is
    # still needed after what is already working. An order already covering the
    # gap drops to zero. This is the "positions + pending" validation.
    if pending_net:
        import dataclasses
        netted: list[Order] = []
        for o in candidate_orders:
            try:
                conid = await resolver.resolve(o.instrument)   # cached from the eligibility probe — no extra IB call
            except Exception:  # noqa: BLE001 - unresolved -> no pending offset, treat as fresh order
                conid = 0
            need = o.quantity if o.side == OrderSide.BUY else -o.quantity
            rq = int(need - pending_net.get(conid, Decimal("0")))
            if rq == 0:
                print(f"  = {o.instrument.symbol}: already covered by pending — no new order")
                continue
            side = OrderSide.BUY if rq > 0 else OrderSide.SELL
            netted.append(dataclasses.replace(o, side=side, quantity=Decimal(abs(rq))))
        candidate_orders = netted

    # --- Buy-and-hold guard: allocated ONCE (USD), ride the positions; trade ONLY on a signal flip -------
    # Each strategy sleeve allocates its USD AUM ONCE and then HOLDS (essentially one asset per sleeve). The
    # sizer's job is "true the book back to target weights" — but BETWEEN signal changes that is spurious
    # CROSS-SLEEVE churn: when one leg (e.g. TQQQ) outperforms, the re-marked combined book drifts off its
    # blended weights and the sizer wants to sell the winner to top up the laggard. The strategies do NOT do
    # that — they hold. So in holdings (USD buy-and-hold) mode, if the target ASSET SET is unchanged (no flip)
    # we HOLD, full stop — no drift rebalance, no band. Sizing is pure USD holdings MV; FX is never applied
    # here and is managed separately at the account level. (Asset-set proxy fits R02/R04, which rotate between
    # distinct single assets — a same-asset-set, weight-only change is not treated as a flip.)
    broker_label = getattr(broker, "name", None) or type(broker).__name__.replace("Broker", "") or "IB"
    _emeta = dict(as_of=str(signal_date), source=source, account=credentials.account_id,
                  broker=broker_label, base_ccy=base_ccy, mode=("submit" if args.submit else "dry-run"),
                  order_type=args.order_type, limit_band=float(args.limit_band),
                  aum_usd=float(pot_usd), fx_rate=float(fx), fx_applied=bool(fx_applied))
    # Per-sleeve buy-and-hold (ALWAYS ON): each ALLOCATED strategy sleeve holds its positions and trades ONLY
    # when ITS OWN asset set flips. On a shared/blended account, one sleeve flipping (R05's monthly rotation)
    # must NOT drag an UNCHANGED sleeve (R02/R04) into a drift rebalance — that was the phantom-churn bug (the
    # old guard compared the WHOLE blended book, so any single flip rebalanced everything, exceeding each
    # sleeve's fixed allocation). We attribute every held leg + every candidate order to its sleeve (by that
    # sleeve's ever-targeted universe), then DROP orders that belong ONLY to sleeves whose asset set is
    # unchanged. Invariant: an allocated sleeve never rebalances on price drift — its capital is fixed; the
    # position rides the market until a genuine signal flip. --no-sleeve-hold opts out (full true-up each run).
    def _sleeves_of(sym: str) -> set:
        # attribute an ORDER to its sleeve: today's target (sym_origin) is unambiguous (one strategy targets a
        # given asset today, so a held+targeted TQQQ is R02's, not R04's); fall back to the ever-traded universe
        # only for a rotated-away leg that no sleeve targets today.
        hit = set(sym_origin.get(sym, []))
        return hit or {c for c, u in sleeve_universes.items() if sym in u}
    flipped = {c for c, f in sleeve_flip.items() if f}            # sleeves whose OWN target changed vs prev date
    hold_sleeves = set(sleeve_flip) - flipped
    # HOLD must MEAN "the account already matches the target", not merely "the signal didn't flip". Those are
    # only the same thing if the sleeve was ever fully ESTABLISHED. R05 never was: SWED-A.ST was BLOCKED at the
    # resolver from day one and AKRBP/TTE/HFD were never (re)bought, so ~26% of a 150% target gross has been
    # missing since inception — and because the target never flipped, the sizer computed the catch-up BUY every
    # single day and this guard threw it away every single day. The book can never converge.
    # --rebalance-band (a fraction of AUM) is the discriminator the help text always promised but which was
    # never actually read anywhere: hold the TINY moves (price drift — the cross-sleeve churn this guard exists
    # to stop), trade the material ones (an unestablished or badly-off leg). band<=0 keeps the previous
    # drop-everything behaviour so nothing changes for callers that don't opt in.
    # The band is a WEIGHT-POINT tolerance: how far a position may sit from its target as a fraction of the
    # book. An order's notional ÷ AUM IS that weight deviation, so `move_usd >= band × AUM` reads directly as
    # "this leg is more than `band` of the book away from where it should be". Sensible values are SMALL —
    # 0.005 = half a percentage point of weight. (0.05 would be five points, larger than the entire target
    # position in most R05 names — AKRBP 7.4%, TTE 4.4%, HFD 2.8% — and would go on suppressing exactly the
    # establishment orders this fix exists to release.)
    _band = float(getattr(args, "rebalance_band", 0.0) or 0.0)
    _sizing_usd = float(size_equity) if size_equity else float(pot_usd)
    _band_usd = _sizing_usd * _band

    def _band_for(sym: str) -> float:
        """The drift tolerance that applies to this leg: its sleeve's own band if the plan set one, else the
        run-wide --rebalance-band. A leg shared by several sleeves takes the TIGHTEST, so a shared ETF is
        never held looser than the most demanding book that targets it."""
        bands = [sleeve_band[c] for c in (_sleeves_of(sym) or ()) if c in sleeve_band]
        return min(bands) if bands else _band

    def _is_material(sym: str, order) -> bool:
        """True if this order CORRECTS a real gap vs target (trade it) rather than trimming drift (hold).

        An EMPTY position that the target wants held is never drift — it is a leg that was never
        established (SWED-A.ST sat unbought for months behind a resolver gap) — so it always trades.
        A leg of a HOLD-UNTIL-FLIP sleeve is never traded on drift at all: its value moving with price
        and FX is the strategy's return. Everything else is drift judged against the leg's own band."""
        try:
            held = abs(float(positions[sym].quantity)) if sym in positions else 0.0
            tgt = abs(float(target_weights.get(sym, 0) or 0))
            if held < 1e-9 and tgt > 1e-9:
                return True                                       # establishment, not drift
            if (_sleeves_of(sym) or set()) & sleeve_hold_drift:
                return False                                      # hold-until-flip: drift is the return
            move_usd = abs(float(order.quantity) * float(_px_usd(sym)))
        except Exception:
            return True                                           # unpriceable -> never silently skip
        return move_usd >= _sizing_usd * _band_for(sym)

    def _why_held(sym: str) -> str:
        """The rule that held this leg, in words the log can be read by."""
        if (_sleeves_of(sym) or set()) & sleeve_hold_drift:
            return "hold-until-flip sleeve: price/FX drift is the strategy's return, not traded"
        b = _band_for(sym)
        return (f"within ±{b:.2%} of book weight (${_sizing_usd * b:,.0f})" if b > 0
                else "no drift band set (drop-everything mode)")
    if candidate_orders and hold_sleeves and not getattr(args, "no_sleeve_hold", False):
        kept: list[Order] = []
        dropped: list = []
        for o in candidate_orders:
            osym = _id_by_inst.get(o.instrument, o.instrument.symbol)
            osl = _sleeves_of(osym)
            if osl and osl <= hold_sleeves:                       # order belongs ONLY to unchanged sleeve(s)
                if (_band > 0 or sleeve_band or sleeve_hold_drift) and _is_material(osym, o):   # a real gap -> TRADE
                    kept.append(o)
                    continue
                dropped.append((osym, o))                         # drift (or no band) -> genuine buy-and-hold
            else:
                kept.append(o)
        _bandtxt = (f"within ±{_band:.2%} of book weight (${_band_usd:,.0f})" if _band > 0
                    else "no --rebalance-band set (drop-everything mode)")
        for osym, o in dropped:
            print(f"  HOLD {osym} [{'/'.join(sorted(_sleeves_of(osym))) or '?'}]: sleeve unchanged, "
                  f"{_why_held(osym)} -> {o.side.value} {float(o.quantity):.0f} NOT placed.")
        if _band > 0 or sleeve_band:
            for o in kept:
                ksym = _id_by_inst.get(o.instrument, o.instrument.symbol)
                ksl = _sleeves_of(ksym)
                if ksl and ksl <= hold_sleeves:
                    kh = abs(float(positions[ksym].quantity)) if ksym in positions else 0.0
                    why = ("position is EMPTY and the target wants it held (establish)" if kh < 1e-9
                           else f"position is off target by more than ±{_band_for(ksym):.2%} of book weight")
                    print(f"  TRUE-UP {ksym} [{'/'.join(sorted(ksl))}]: sleeve unchanged BUT {why} "
                          f"-> {o.side.value} {float(o.quantity):.0f} PLACED.")
        candidate_orders = kept
        if dropped and not candidate_orders:                      # everything held -> emit a clean HOLD decision
            print(f"\n  HOLDING — sleeves {sorted(hold_sleeves)} unchanged AND every position {_bandtxt} "
                  f"-> account is in line with target, NO rebalance.")
            _emit_orders_json("HOLD", f"per-sleeve buy-and-hold: {sorted(hold_sleeves)} unchanged, "
                                      f"all positions {_bandtxt}",
                              _order_summary_rows(target_weights, prices, positions, [], sym_origin,
                                                  limit_band=float(args.limit_band), is_limit=is_limit), **_emeta)
            if args.submit:
                # Everything held on a SUBMIT run = the account is at today's target for every sleeve.
                # Record it, so the executed-target state exists even before the first flip is traded.
                _record_execution(credentials.account_id, code, sleeves=sleeve_today)
            await broker.disconnect()
            return 0
    if flipped:
        print(f"\n  Rebalancing (signal flip): {sorted(flipped)}"
              + (f";  holding {sorted(hold_sleeves)}" if hold_sleeves else "") + ".")

    if not candidate_orders:
        print("  No orders — already at target (positions + pending).")
        _emit_orders_json("NO_ORDERS", "already at target (positions + pending)",
                          _order_summary_rows(target_weights, prices, positions, [], sym_origin,
                                              limit_band=float(args.limit_band), is_limit=is_limit), **_emeta)
        await broker.disconnect()
        return 0
    for o in candidate_orders:
        print(f"  -> {o.side.value} {float(o.quantity):.0f} {o.instrument.symbol}")
    _emit_orders_json("ORDERS", "signal flip / rebalance to target",
                      _order_summary_rows(target_weights, prices, positions, candidate_orders, sym_origin,
                                          limit_band=float(args.limit_band), is_limit=is_limit), **_emeta)

    # --- 5. Dry-run vs submit ------------------------------------------------
    if not args.submit:
        print("\n=== DRY-RUN — nothing submitted. Re-run with --submit to place these orders. ===")
        await broker.disconnect()
        return 0

    if stale and not args.force_stale:
        print("\nFAILED: refusing to submit STALE signals — run today's signal pipeline first, "
              "or pass --force-stale to override.")
        await broker.disconnect()
        return 2

    if not args.yes:
        prompt = (
            f"\nSubmit {len(candidate_orders)} {args.order_type} order(s) "
            f"for {code} to account {credentials.account_id}? [y/N] "
        )
        if input(prompt).strip().lower() not in ("y", "yes"):
            print("Aborted by operator.")
            await broker.disconnect()
            return 0

    # Optional RiskEngine (RC-13 kill-switch / RC-08 stale / RC-09 hours / RC-10
    # price sanity). RC-10 only bites on LIMIT orders (LOO/LMT) — it checks the
    # limit is within ±50% of the reference, catching gross sizing/price bugs.
    # outside_rth_allowed=True since MOO/LOO intentionally submit at the open.
    engine = None
    if args.risk_checks or args.kill_switch:
        from blive.risk.checks import KillSwitch, RiskEngine, RiskEngineConfig, RiskInputs
        ks = KillSwitch()
        if args.kill_switch:
            ks.arm("operator --kill-switch")
        engine = RiskEngine(
            config=RiskEngineConfig(outside_rth_allowed=True,
                                    max_data_staleness_daily_sec=5 * 86400,
                                    max_price_deviation_pct=Decimal("0.5")),
            kill_switch=ks, strategy_id=code)
        print(f"  risk engine ON (price-sanity ±50%; kill-switch="
              f"{'ARMED — all orders blocked' if args.kill_switch else 'clear'})")

    if not _acquire_run_lock():
        print("\nFAILED: another execution appears to be in progress (run-lock held) — "
              f"aborting to avoid duplicate orders. If stale, delete {_LOCK_PATH}.")
        await broker.disconnect()
        return 2

    prev = _executed_today(credentials.account_id)
    if prev and not args.force:
        print(f"\nFAILED: account {credentials.account_id} already executed today ({prev}). "
              "Re-running would re-trade the day's target — pass --force to override.")
        _release_run_lock()
        await broker.disconnect()
        return 2

    print(f"\n=== Submitting {args.order_type} orders ===")
    filled = canceled = rejected = risk_blocked = 0
    submitted_any = False
    now_utc = datetime.now(tz=timezone.utc)

    # Capture IB's per-order error(s) so a REJECT/Cancel shows WHY (110 tick, 10311 direct-route, 201, …)
    # instead of a bare "REJECTED". Cleared before each submit → only that order's errors are attributed.
    _ib_errs: list[tuple[int, str]] = []
    _BENIGN_CODES = {2100, 2103, 2104, 2105, 2106, 2107, 2108, 2110, 2119, 2150, 2158, 162, 366}
    def _capture_err(reqId, errorCode, errorString, *rest):   # ib_async errorEvent handler
        try:
            _ib_errs.append((int(errorCode), str(errorString)))
        except Exception:  # noqa: BLE001
            pass
    try:
        client.ib.errorEvent += _capture_err   # noqa: SLF001 - script-level access
    except Exception:  # noqa: BLE001
        pass

    # Round a limit to the contract's minimum price variation (fixes IB error 110). EU venues use TIERED
    # ticks (the increment grows with price), so plain minTick (the smallest tier) is wrong — we pull the
    # market-rule increment table and round to the increment for THIS price's band. Cached per instrument.
    _tickrule: dict = {}
    async def _round_to_tick(instrument, price: Decimal) -> Decimal:
        rule = _tickrule.get(instrument)
        if rule is None:
            rule = [(Decimal("0"), Decimal("0.01"))]                          # fallback
            try:
                cds = await client.ib.reqContractDetailsAsync(resolver.to_contract(instrument))  # noqa: SLF001
                if cds:
                    d = cds[0]
                    incs = None
                    rids = str(getattr(d, "marketRuleIds", "") or "")
                    if rids:
                        try:
                            incs = await client.ib.reqMarketRuleAsync(int(rids.split(",")[0]))  # noqa: SLF001
                        except Exception:  # noqa: BLE001
                            incs = None
                    if incs:
                        rule = sorted((Decimal(str(x.lowEdge)), Decimal(str(x.increment))) for x in incs)
                    elif getattr(d, "minTick", None):
                        rule = [(Decimal("0"), Decimal(str(d.minTick)))]
            except Exception:  # noqa: BLE001
                pass
            _tickrule[instrument] = rule
        inc = rule[0][1]                                                      # increment for this price's tier
        for low, i in rule:
            if price >= low:
                inc = i
            else:
                break
        return (price / inc).quantize(Decimal("1")) * inc

    for desired in candidate_orders:
        lp: Decimal | None = None
        if is_limit:
            ref = prices[_id_by_inst.get(desired.instrument, desired.instrument.symbol)]   # LOCAL ccy for the order
            mult = (Decimal("1") + band) if desired.side == OrderSide.BUY else (Decimal("1") - band)
            lp = await _round_to_tick(desired.instrument, ref * mult)   # round to venue minTick (fixes IB error 110)
        # OPG (opening-auction) tif is US-only — EU venues (Euronext/LSE/XETRA/BM/Copenhagen) reject it
        # (IB-201). For EU single-name equities send a plain DAY limit instead; US ETFs keep the OPG tif.
        _is_eu = _id_by_inst.get(desired.instrument, desired.instrument.symbol) in _PRICE_CCY
        _tif = TimeInForce.DAY if (_is_eu and tif == TimeInForce.OPG) else tif
        order = _make_order(desired, order_type=order_type, tif=_tif, limit_price=lp, label=f"sfera-{code}")

        if engine is not None:
            _rid = _id_by_inst.get(desired.instrument, desired.instrument.symbol)   # EODHD id (bars/prices key)
            approved, breaches = engine.approve(
                order,
                inputs=RiskInputs(last_bar=last_bars.get(_rid),
                                  is_market_open=True,
                                  reference_price=prices.get(_rid)),
                now=now_utc)
            for b in breaches:
                chk = b.check.value if hasattr(b.check, "value") else b.check
                print(f"    risk {chk}: {b.detail}")
            if approved is None:
                print(f"    BLOCKED by risk engine — skipping {order.instrument.symbol}")
                risk_blocked += 1
                continue

        px_str = f" @ {float(lp):.2f}" if lp is not None else ""
        print(f"  Submitting {order.side.value} {float(order.quantity):.0f} "
              f"{order.instrument.symbol} {args.order_type}{px_str} ...")
        _ib_errs.clear()
        await broker.submit(order)
        submitted_any = True
        terminal_state, _ = await _drain_order_lifecycle(
            broker=broker,
            target_id=ClientOrderId(order.client_order_id),
            timeout_s=args.event_wait_seconds,
            settle_on_accepted=True,   # LOO/DAY: return once IB confirms the order working — don't idle for a
        )                              # fill that can't happen until the open (was 30s x N orders = GUI timeout)
        reason = "; ".join(f"IB-{c}: {m}" for c, m in _ib_errs if c not in _BENIGN_CODES)
        print(f"    -> {terminal_state}" + (f"   [{reason}]" if reason else ""))
        state_name = getattr(terminal_state, "name", str(terminal_state))
        if state_name == "FILLED":
            filled += 1
        elif state_name == "CANCELED":
            canceled += 1
        elif state_name == "REJECTED":
            rejected += 1

    if filled or canceled or rejected or submitted_any:
        # A submit with NO rejections is the account moving to today's target: record every sleeve's book
        # as executed, so tomorrow's run sees "already traded" and holds. A rejected leg means the book is
        # NOT where the target says — leave the state alone and the flip stays pending for the next run.
        # KNOWN LIMIT: an ACCEPTED LOO counts as executed here (it fills at the next open, or does not);
        # there is no fill reconciliation, so a resize that never fills is not retried until the next
        # month-end. A leg that is still EMPTY is — the establishment rule trades it regardless of state.
        _record_execution(credentials.account_id, code,
                          sleeves=(sleeve_today if rejected == 0 else None))
    _release_run_lock()
    print(f"\n=== Done: filled={filled}  canceled={canceled}  rejected={rejected}  risk-blocked={risk_blocked} ===")
    await broker.disconnect()
    return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Execute a sfera strategy's target weights on IB Paper")
    p.add_argument("--strategy", default="R02", help="strategy R-code e.g. R02 (also accepts slot S14 or legacy r_lev_*); default R02")
    p.add_argument("--portfolio", default="",
                   help='blend multiple strategies on ONE account, JSON: '
                        '[{"strategy":"R02","budget":50000},{"strategy":"R04","budget":50000}]')
    p.add_argument("--source", choices=("db", "file"), default="db", help="weight source (default db)")
    p.add_argument("--weights-path", default="", help="parquet/CSV path for --source file")
    p.add_argument("--sfera-root", default=str(_DEFAULT_SFERA_ROOT), help="sfera root (for DB .env)")
    p.add_argument("--as-of", default="", help="weights date YYYY-MM-DD (default latest)")
    p.add_argument("--nav-slice", type=float, default=0.05, help="NAV slice fraction of equity (default 0.05) if --budget unset")
    p.add_argument("--budget", type=float, default=0.0, help="absolute strategy budget (overrides --nav-slice); denominated per --budget-ccy")
    p.add_argument("--budget-ccy", default="base",
                   help="currency --budget is in: 'base' (account ccy, FX-converted to USD each run — default, back-compat), "
                        "'usd' (fixed USD notional = source-ccy sizing), or an ISO ccy code (e.g. 'eur' for R05) "
                        "converted to USD via yfmktdt.fx_rates")
    p.add_argument("--size-basis", choices=["budget", "holdings"], default="budget",
                   help="AUM basis: 'budget' (default — from --budget/--nav-slice) or 'holdings' (mark-to-market USD "
                        "value of CURRENT positions → target=held, so unchanged weights yield NO orders and the sleeve "
                        "rides the market; buy-and-hold. Pair with --rebalance-band. Falls back to budget if flat.)")
    p.add_argument("--rebalance-band", type=float, default=0.0,
                   help="position tolerance in WEIGHT POINTS of the book, as a fraction (0.005 = half a percentage "
                        "point). When >0, a sleeve whose signal has not flipped still TRUES UP any leg sitting more "
                        "than the band away from its target weight (an unestablished or badly-off position), while "
                        "smaller moves are held as drift. Keep it small: 0.05 would be FIVE weight points, more than "
                        "the whole target position in most single names. 0 (default) = hold everything on an "
                        "unchanged sleeve (back-compat).")
    p.add_argument("--no-sleeve-hold", action="store_true",
                   help="disable the PER-SLEEVE buy-and-hold guard (default ON): normally an allocated sleeve whose own "
                        "asset set is unchanged is HELD (no drift rebalance) even when another sleeve on the same blended "
                        "account flips; this flag forces a full true-up of every sleeve to target on this run.")
    p.add_argument("--max-staleness-days", type=int, default=4, help="refuse --submit if weights older than N days (default 4)")
    p.add_argument("--force-stale", action="store_true", help="override the staleness guard on --submit")
    p.add_argument("--order-type", choices=("MOO", "MKT", "LOO", "LMT"), default="MOO",
                   help="MOO/MKT=market (no price protection); LOO/LMT=limit at +/-band "
                        "(LOO fills at open else cancels; LMT works the day & stays pending)")
    p.add_argument("--limit-band", type=float, default=0.03, help="price band for LOO/LMT (default 0.03 = 3%%)")
    p.add_argument("--risk-checks", action="store_true",
                   help="run blive RiskEngine (RC-10 price sanity etc.) before each submit")
    p.add_argument("--kill-switch", action="store_true", help="arm RC-13 kill-switch — blocks ALL orders")
    p.add_argument("--force", action="store_true", help="override the once-per-day execution guard")
    p.add_argument("--offline", action="store_true", help="no IB; print target preview only")
    p.add_argument("--submit", action="store_true", help="actually place orders (default dry-run)")
    p.add_argument("--yes", action="store_true", help="skip interactive submit confirmation")
    p.add_argument("--example-equity", type=float, default=100_000.0, help="equity for --offline preview")
    p.add_argument("--event-wait-seconds", type=float, default=5.0,
                   help="per-order FSM drain HARD CAP (s). With settle_on_accepted the order returns as soon "
                        "as IB confirms it working; this is only the ceiling for a stuck/unacknowledged order.")
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
