from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from marketdata.quality import _TIMEFRAME_FREQ


def _exchange(exchange_id: str):
    import ccxt

    return getattr(ccxt, exchange_id)({"enableRateLimit": True})


def fetch_ohlcv(
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime | None = None,
    *,
    exchange_id: str = "binance",
    exchange=None,
    limit: int = 1000,
) -> pd.DataFrame:
    """Closed candles in [start, end); the bar still forming at `end` is dropped."""
    ex = exchange or _exchange(exchange_id)
    end = end or datetime.now(UTC)
    bar = pd.Timedelta(_TIMEFRAME_FREQ[timeframe])
    since = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)

    rows: list[list[float]] = []
    while since < end_ms:
        batch = ex.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
        if not batch:
            break
        rows.extend(batch)
        next_since = batch[-1][0] + int(bar.total_seconds() * 1000)
        if next_since <= since:
            break
        since = next_since

    frame = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    if frame.empty:
        return frame.set_index(pd.DatetimeIndex([], name="ts", tz="UTC"))
    frame["ts"] = pd.to_datetime(frame["ts"], unit="ms", utc=True)
    frame = frame.drop_duplicates("ts").set_index("ts").sort_index()
    return frame[frame.index + bar <= pd.Timestamp(end)]
