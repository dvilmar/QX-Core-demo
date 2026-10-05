from __future__ import annotations

import pandas as pd

_TIMEFRAME_FREQ = {"1m": "1min", "5m": "5min", "15m": "15min", "1h": "1h", "4h": "4h", "1d": "1D"}


def quality_report(frame: pd.DataFrame, timeframe: str) -> dict:
    if frame.empty:
        return {"status": "empty", "rows": 0}
    freq = pd.Timedelta(_TIMEFRAME_FREQ[timeframe])
    index = frame.index
    expected = pd.date_range(index.min(), index.max(), freq=freq)
    missing = expected.difference(index)
    bad_ohlc = (
        (frame["high"] < frame[["open", "close", "low"]].max(axis=1))
        | (frame["low"] > frame[["open", "close", "high"]].min(axis=1))
    ).sum()
    non_positive = (frame[["open", "high", "low", "close"]] <= 0).any(axis=1).sum()
    duplicates = int(index.duplicated().sum())
    ok = not (len(missing) or bad_ohlc or non_positive or duplicates)
    return {
        "status": "ok" if ok else "issues",
        "rows": len(frame),
        "start": index.min().isoformat(),
        "end": index.max().isoformat(),
        "duplicates": duplicates,
        "missing_bars": len(missing),
        "invalid_ohlc": int(bad_ohlc),
        "non_positive_prices": int(non_positive),
    }
