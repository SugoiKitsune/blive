"""IG market-data adapter — :class:`MarketDataPort` implementation.

M2-IG.3 ships :meth:`historical_bars` over REST ``GET /prices/{epic}/...``
(rate-limited via the ``historical_prices`` bucket per
[ADR-038](../../../../docs/decisions/DECISIONS.md#adr-038--ig-rate-limit-defaults-parameterise-adr-031)).

M2-IG.3-followup ships :meth:`subscribe_bars` over Lightstreamer per
[ADR-036](../../../../docs/decisions/DECISIONS.md#adr-036--ig-wire-level-driver-roll-our-own-httpx--asyncio-lightstreamer)
via the :class:`blive.adapters.ig.lightstreamer.LightstreamerSource`
abstraction. The production wrapper around ``lightstreamer-client-lib``
is itself a follow-up commit (the abstraction lets the unit tests run
against :class:`FakeLightstreamerSource`); when no source is provided
to the constructor, :meth:`subscribe_bars` raises
:class:`NotImplementedError` pointing the operator at the production
wrapper landing.

:meth:`subscribe_trades` stays out of v1 — Phase 1 strategies use bars.

The historical endpoint returns OHLC as separate bid / ask prices. We
prefer ``lastTraded`` when IG includes it (real traded prices on cash
equities); otherwise we synthesise a mid from ``bid`` + ``ask``. This
matches what a strategy backtest would compare against — neutral mid
rather than directional bid/ask.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, AsyncIterator, Mapping

from blive.adapters.ig.client import IGClient
from blive.adapters.ig.instrument_resolver import IGInstrumentResolver
from blive.adapters.ig.lightstreamer import (
    LightstreamerSource,
    LightstreamerSubscription,
)
from blive.domain.ports import ClockPort
from blive.domain.types import Bar, BarFreq, Instrument, Trade

log = logging.getLogger(__name__)


# --- BarFreq → IG resolution mapping ----------------------------------------

# IG's REST `/prices` resolution enum (KB-16 §1 / IG Labs docs). We only map
# the BarFreq subset blive currently supports; if BarFreq widens, extend.
_BLIVE_FREQ_TO_IG_RESOLUTION: dict[BarFreq, str] = {
    "1m": "MINUTE",
    "5m": "MINUTE_5",
    "15m": "MINUTE_15",
    "1h": "HOUR",
    "1d": "DAY",
}

# IG Lightstreamer chart-subscription resolution enum (different from REST!).
# Per IG Streaming API docs: chart items are ``CHART:{epic}:{resolution}``
# where resolution is ``1MINUTE`` / ``5MINUTE`` / ``15MINUTE`` / ``HOUR`` /
# ``DAY``. Yes, the resolution token differs between REST and streaming;
# this is an IG quirk we have to track.
_BLIVE_FREQ_TO_LIGHTSTREAMER_RESOLUTION: dict[BarFreq, str] = {
    "1m": "1MINUTE",
    "5m": "5MINUTE",
    "15m": "15MINUTE",
    "1h": "HOUR",
    "1d": "DAY",
}

# Bar interval duration (used to compute close_time_utc from snapshotTime).
_BLIVE_FREQ_TO_TIMEDELTA: dict[BarFreq, timedelta] = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "1d": timedelta(days=1),
}


# Lightstreamer chart subscription field set we request for every bar
# subscription. Subset of IG's documented chart fields, sufficient to build
# a Bar at consolidation-end.
_LIGHTSTREAMER_CHART_FIELDS: tuple[str, ...] = (
    "UTM",  # update timestamp UTC millis
    "OFR_OPEN",
    "OFR_HIGH",
    "OFR_LOW",
    "OFR_CLOSE",
    "BID_OPEN",
    "BID_HIGH",
    "BID_LOW",
    "BID_CLOSE",
    "LTP_OPEN",
    "LTP_HIGH",
    "LTP_LOW",
    "LTP_CLOSE",
    "LTV",  # last traded volume in current bar
    "CONS_END",  # "1" → bar consolidation ended; emit Bar
)


def _freq_to_ig_resolution(freq: BarFreq) -> str:
    return _BLIVE_FREQ_TO_IG_RESOLUTION[freq]


def _freq_to_lightstreamer_resolution(freq: BarFreq) -> str:
    return _BLIVE_FREQ_TO_LIGHTSTREAMER_RESOLUTION[freq]


def _freq_to_timedelta(freq: BarFreq) -> timedelta:
    return _BLIVE_FREQ_TO_TIMEDELTA[freq]


def _lightstreamer_chart_item(epic: str, freq: BarFreq) -> str:
    """Build the Lightstreamer subscription item string for a chart bar feed."""
    return f"CHART:{epic}:{_freq_to_lightstreamer_resolution(freq)}"


def _format_ig_datetime(dt: datetime) -> str:
    """IG's ``GET /prices`` URL segments expect ``yyyy-MM-dd'T'HH:mm:ss`` (UTC)."""
    if dt.tzinfo is None:
        raise ValueError("IGMarketData expects timezone-aware datetimes")
    utc = dt.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%M:%S")


# --- The adapter ------------------------------------------------------------


class IGMarketData:
    """`MarketDataPort` adapter for IG Markets.

    Constructed via :func:`blive.adapters.ig.create_ig_market_data`. The
    Lightstreamer ``source`` is optional at constructor time; if absent,
    :meth:`subscribe_bars` raises :class:`NotImplementedError` so the
    historical-only path remains usable while the production
    Lightstreamer wrapper is being wired.
    """

    def __init__(
        self,
        *,
        client: IGClient,
        resolver: IGInstrumentResolver,
        clock: ClockPort,
        lightstreamer_source: LightstreamerSource | None = None,
        max_concurrent_subscriptions: int = 40,
    ) -> None:
        self._client = client
        self._resolver = resolver
        self._clock = clock
        self._source = lightstreamer_source
        # KB-17 §3 concurrent-subscription budget. Tracked outside the
        # token-bucket rate limiter because Lightstreamer subscriptions
        # are a *budget* (no refill), not a refilling bucket.
        self._subscription_budget = asyncio.Semaphore(max_concurrent_subscriptions)
        self._max_subscriptions = max_concurrent_subscriptions
        # Map blive Instrument → live Lightstreamer subscription so
        # :meth:`unsubscribe` can find and release it.
        self._active: dict[Instrument, LightstreamerSubscription] = {}

    # --- MarketDataPort -----------------------------------------------------

    async def subscribe_bars(
        self,
        instrument: Instrument,
        freq: BarFreq,
    ) -> AsyncIterator[Bar]:
        if self._source is None:
            raise NotImplementedError(
                "IGMarketData.subscribe_bars requires a LightstreamerSource. "
                "The production wrapper around lightstreamer-client-lib lands "
                "in M2-IG.3 follow-up; until then, pass a LightstreamerSource "
                "(e.g. blive.adapters.ig.lightstreamer.FakeLightstreamerSource) "
                "to the IGMarketData constructor explicitly."
            )
        if instrument in self._active:
            raise RuntimeError(
                f"IGMarketData.subscribe_bars: already subscribed to {instrument!r}; "
                "call unsubscribe() before re-subscribing"
            )

        # Acquire the subscription-budget slot (KB-17 §3) BEFORE issuing
        # the wire-level subscribe so a budget-exhausted call waits rather
        # than racing the Lightstreamer server.
        await self._subscription_budget.acquire()
        try:
            epic = await self._resolver.resolve(instrument)
            item = _lightstreamer_chart_item(epic, freq)
            await self._source.connect()
            subscription = await self._source.subscribe(
                item=item,
                fields=_LIGHTSTREAMER_CHART_FIELDS,
                mode="MERGE",
            )
        except Exception:
            self._subscription_budget.release()
            raise

        self._active[instrument] = subscription
        bar_duration = _freq_to_timedelta(freq)
        return _bar_stream(
            subscription=subscription,
            instrument=instrument,
            bar_duration=bar_duration,
        )

    async def subscribe_trades(self, instrument: Instrument) -> AsyncIterator[Trade]:
        raise NotImplementedError(
            "IGMarketData.subscribe_trades is out of scope for v1 — Phase 1 "
            "strategies use bars only. IG market-tick streams (`MARKET:{epic}` "
            "items) are a future enhancement, not an M2-IG deliverable."
        )

    async def unsubscribe(self, instrument: Instrument) -> None:
        """Release the Lightstreamer subscription + budget slot for ``instrument``.

        Idempotent: unsubscribing an instrument that was never subscribed
        (or already unsubscribed) is a no-op.
        """
        subscription = self._active.pop(instrument, None)
        if subscription is None:
            return
        if self._source is None:
            # Defensive: source went away after subscribe (shouldn't happen
            # given the constructor invariant, but be safe).
            self._subscription_budget.release()
            return
        try:
            await self._source.unsubscribe(subscription)
        finally:
            self._subscription_budget.release()

    async def historical_bars(
        self,
        instrument: Instrument,
        freq: BarFreq,
        start: datetime,
        end: datetime,
    ) -> list[Bar]:
        """Fetch historical OHLCV bars from IG ``GET /prices/{epic}/{res}/{from}/{to}``.

        Rate-limited via the ``historical_prices`` bucket per ADR-038.
        Returns :class:`Bar` records sorted ascending by ``open_time_utc``.
        """
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("IGMarketData.historical_bars requires UTC-aware start / end")
        if start >= end:
            raise ValueError(f"IGMarketData.historical_bars: start ({start}) must be < end ({end})")

        epic = await self._resolver.resolve(instrument)
        resolution = _freq_to_ig_resolution(freq)
        bar_duration = _freq_to_timedelta(freq)
        path = (
            f"/prices/{epic}/{resolution}"
            f"/{_format_ig_datetime(start)}/{_format_ig_datetime(end)}"
        )

        body = await self._client.get(path, version=3, bucket="historical_prices")
        if not isinstance(body, dict):
            return []
        raw_prices = body.get("prices", [])
        if not isinstance(raw_prices, list):
            return []

        out: list[Bar] = []
        for entry in raw_prices:
            if not isinstance(entry, dict):
                continue
            try:
                bar = _parse_price_bar(entry, instrument=instrument, bar_duration=bar_duration)
            except (KeyError, ValueError, TypeError) as exc:
                log.warning("IG /prices entry skipped (parse failure): %s", exc)
                continue
            out.append(bar)
        # IG returns bars in ascending order normally; sort defensively.
        out.sort(key=lambda b: b.open_time_utc)
        return out


# --- Streaming Bar pipeline -------------------------------------------------


async def _bar_stream(
    *,
    subscription: LightstreamerSubscription,
    instrument: Instrument,
    bar_duration: timedelta,
) -> AsyncIterator[Bar]:
    """Translate a stream of Lightstreamer field updates into :class:`Bar` events.

    IG chart items emit incremental field updates in MERGE mode. We
    accumulate the latest values for each OHLC field and emit a Bar
    whenever ``CONS_END == "1"`` (consolidation ended). On consolidation,
    state resets so the next bar starts fresh.

    Defensive against missing fields: if any required price field is
    absent at consolidation, the bar is skipped (logged).
    """
    state: dict[str, str] = {}
    async for update in subscription.updates():
        # Merge incoming fields into running state (None means "no change").
        for k, v in update.items():
            if v is not None:
                state[k] = v

        cons_end = state.get("CONS_END")
        if cons_end != "1":
            continue

        try:
            bar = _build_bar_from_state(state, instrument=instrument, bar_duration=bar_duration)
        except (KeyError, ValueError, TypeError) as exc:
            log.warning(
                "IG chart consolidation for %s skipped (parse failure): %s",
                instrument.symbol,
                exc,
            )
            # Reset state so next bar starts clean even if this one was malformed.
            state = {}
            continue

        # Reset state for the next bar but preserve the consolidation
        # marker explicitly so a stuck CONS_END doesn't infinitely emit.
        state = {}
        yield bar


def _build_bar_from_state(
    state: Mapping[str, str],
    *,
    instrument: Instrument,
    bar_duration: timedelta,
) -> Bar:
    """Build a :class:`Bar` from accumulated Lightstreamer chart state."""
    utm_raw = state.get("UTM")
    if not utm_raw:
        raise ValueError("Lightstreamer chart state missing UTM (update timestamp)")
    try:
        utm_ms = int(utm_raw)
    except ValueError as exc:
        raise ValueError(f"Lightstreamer UTM not an integer: {utm_raw!r}") from exc
    close_time = datetime.fromtimestamp(utm_ms / 1000.0, tz=timezone.utc)
    open_time = close_time - bar_duration

    # Prefer LTP (last traded) when available, fall back to bid/ask midpoint.
    open_price = _stream_ohlc(state, "OPEN")
    high_price = _stream_ohlc(state, "HIGH")
    low_price = _stream_ohlc(state, "LOW")
    close_price = _stream_ohlc(state, "CLOSE")

    volume_raw = state.get("LTV", "0")
    try:
        volume = Decimal(str(volume_raw))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Lightstreamer LTV not numeric: {volume_raw!r}") from exc
    if volume < 0:
        volume = Decimal("0")

    return Bar(
        instrument=instrument,
        open_time_utc=open_time,
        close_time_utc=close_time,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
        vwap=None,
    )


def _stream_ohlc(state: Mapping[str, str], suffix: str) -> Decimal:
    """Extract one OHLC value (``OPEN`` / ``HIGH`` / ``LOW`` / ``CLOSE``) from
    Lightstreamer state.

    Prefers ``LTP_{suffix}`` (real traded prices on cash equities); falls
    back to ``(BID_{suffix} + OFR_{suffix}) / 2`` (typical for indices /
    FX where last-traded isn't meaningful).
    """
    ltp = state.get(f"LTP_{suffix}")
    if ltp is not None and ltp != "":
        try:
            return Decimal(ltp)
        except (TypeError, ValueError):
            pass
    bid = state.get(f"BID_{suffix}")
    ask = state.get(f"OFR_{suffix}")
    if bid is None or ask is None or bid == "" or ask == "":
        raise ValueError(
            f"Lightstreamer chart state missing BID_{suffix} / OFR_{suffix} "
            f"and no LTP_{suffix} fallback"
        )
    try:
        bid_d = Decimal(bid)
        ask_d = Decimal(ask)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Lightstreamer BID_{suffix} / OFR_{suffix} not numeric: bid={bid!r}, ask={ask!r}"
        ) from exc
    return (bid_d + ask_d) / Decimal("2")


# --- Historical-bar parser (module-level, unit-testable) -------------------


def _parse_price_bar(
    entry: Mapping[str, Any],
    *,
    instrument: Instrument,
    bar_duration: timedelta,
) -> Bar:
    """Translate one IG /prices entry into a :class:`Bar`.

    IG fields used (KB-16 / IG Labs `/prices` reference):
    - ``snapshotTimeUTC`` (preferred) or ``snapshotTime`` — start of bar.
    - ``openPrice``, ``highPrice``, ``lowPrice``, ``closePrice`` — OHLC,
      each a dict with ``bid``, ``ask``, optional ``lastTraded``.
    - ``lastTradedVolume`` — bar volume.
    """
    snapshot = entry.get("snapshotTimeUTC") or entry.get("snapshotTime")
    if not isinstance(snapshot, str) or not snapshot:
        raise ValueError("IG /prices entry missing snapshotTime[UTC]")
    open_time = _parse_ig_snapshot(snapshot)
    close_time = open_time + bar_duration

    open_price = _ohlc_value(entry, "openPrice")
    high_price = _ohlc_value(entry, "highPrice")
    low_price = _ohlc_value(entry, "lowPrice")
    close_price = _ohlc_value(entry, "closePrice")

    volume_raw = entry.get("lastTradedVolume", 0)
    try:
        volume = Decimal(str(volume_raw))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"IG /prices lastTradedVolume not numeric: {volume_raw!r}") from exc
    if volume < 0:
        volume = Decimal("0")

    return Bar(
        instrument=instrument,
        open_time_utc=open_time,
        close_time_utc=close_time,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
        vwap=None,  # IG's /prices doesn't return VWAP
    )


def _ohlc_value(entry: Mapping[str, Any], field: str) -> Decimal:
    """Extract a single OHLC value from an IG price entry.

    Prefers ``lastTraded`` (real trades on cash equities); falls back to
    the bid/ask midpoint (typical for indices / FX where lastTraded is
    not meaningful).
    """
    obj = entry.get(field)
    if not isinstance(obj, dict):
        raise ValueError(f"IG /prices entry missing {field!r} dict")
    last_traded = obj.get("lastTraded")
    if last_traded is not None:
        try:
            return Decimal(str(last_traded))
        except (TypeError, ValueError):
            pass  # fall through to mid
    bid = obj.get("bid")
    ask = obj.get("ask")
    if bid is None or ask is None:
        raise ValueError(f"IG /prices {field!r} missing bid / ask: {obj!r}")
    try:
        bid_d = Decimal(str(bid))
        ask_d = Decimal(str(ask))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"IG /prices {field!r} bid / ask not numeric: {obj!r}") from exc
    return (bid_d + ask_d) / Decimal("2")


def _parse_ig_snapshot(s: str) -> datetime:
    """Parse IG's snapshotTime[UTC] field. Same shape as the order-side
    timestamp helper but kept here to avoid an inter-module dependency."""
    s = s.strip()
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s[:-1]).replace(tzinfo=timezone.utc)
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass
    try:
        return datetime.strptime(s, "%Y/%m/%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"unrecognised IG snapshot timestamp: {s!r}") from exc


__all__ = ["IGMarketData"]
