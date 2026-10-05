from __future__ import annotations

import pandas as pd

from demo_engine import BacktestResult, Candle


def equity_series(result: BacktestResult) -> pd.Series:
    idx = pd.DatetimeIndex(pd.to_datetime(result.equity_timestamps, utc=True))
    return pd.Series(result.equity_curve, index=idx, dtype=float)


def trades_frame(result: BacktestResult) -> pd.DataFrame:
    return pd.DataFrame(
        [{"entry_ts": t.entry_ts, "exit_ts": t.exit_ts, "pnl": t.pnl, "reason": t.reason} for t in result.trades]
    )


def candles_to_frame(candles: list[Candle]) -> pd.DataFrame:
    return pd.DataFrame([vars(c) for c in candles]).set_index("ts")


def frame_to_candles(frame: pd.DataFrame) -> list[Candle]:
    return [
        Candle(ts=ts.to_pydatetime(), open=r.open, high=r.high, low=r.low, close=r.close, volume=r.volume)
        for ts, r in frame.iterrows()
    ]
