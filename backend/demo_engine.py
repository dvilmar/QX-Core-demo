"""Synthetic data and a deliberately simple EMA/RSI demo signal; not a real strategy."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from quant import costs

BAR_HOURS = 1
DEFAULT_BARS = 24 * 365
DEFAULT_CAPITAL = 10_000.0
RISK_PER_TRADE = 0.02
FEE_RATE = costs.FEE_RATE
ATR_PERIOD = 14


@dataclass
class Candle:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Trade:
    entry_ts: datetime
    exit_ts: datetime
    side: str
    entry_price: float
    exit_price: float
    qty: float
    pnl: float
    reason: str


@dataclass
class BacktestResult:
    candles: list[Candle] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    equity_timestamps: list[datetime] = field(default_factory=list)


def generate_synthetic_candles(
    n_bars: int = DEFAULT_BARS,
    start_price: float = 100.0,
    seed: int | None = 42,
    annual_drift: float = 0.15,
    annual_vol: float = 0.55,
) -> list[Candle]:
    """Seeded GBM random walk resampled into hourly OHLC bars."""
    rng = random.Random(seed)
    dt = 1.0 / (24 * 365)
    mu = annual_drift
    sigma = annual_vol
    price = start_price
    start_ts = datetime.now(tz=UTC) - timedelta(hours=n_bars)

    candles: list[Candle] = []
    for i in range(n_bars):
        ts = start_ts + timedelta(hours=i)
        open_price = price

        sub_prices = [open_price]
        for _ in range(4):
            shock = rng.gauss(0, 1)
            step = math.exp((mu - 0.5 * sigma**2) * (dt / 4) + sigma * math.sqrt(dt / 4) * shock)
            sub_prices.append(sub_prices[-1] * step)
        close_price = sub_prices[-1]
        high_price = max(sub_prices)
        low_price = min(sub_prices)
        volume = abs(rng.gauss(1_000, 250))
        candles.append(Candle(ts, open_price, high_price, low_price, close_price, volume))
        price = close_price

    return candles


def _ema(values: list[float], period: int) -> list[float]:
    k = 2.0 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def _rsi(values: list[float], period: int = 14) -> list[float]:
    out = [50.0] * len(values)
    for i in range(period, len(values)):
        window = values[i - period : i + 1]
        deltas = [window[j] - window[j - 1] for j in range(1, len(window))]
        avg_gain = sum(d for d in deltas if d > 0) / period
        avg_loss = abs(sum(d for d in deltas if d < 0)) / period
        out[i] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    return out


def _atr(candles: list[Candle], period: int = ATR_PERIOD) -> list[float | None]:
    tr = [candles[0].high - candles[0].low]
    for prev, c in zip(candles, candles[1:], strict=False):
        tr.append(max(c.high - c.low, abs(c.high - prev.close), abs(c.low - prev.close)))
    out: list[float | None] = [None] * len(candles)
    for i in range(period - 1, len(candles)):
        out[i] = sum(tr[i - period + 1 : i + 1]) / period
    return out


def run_demo_backtest(
    candles: list[Candle],
    capital: float = DEFAULT_CAPITAL,
    risk_per_trade: float = RISK_PER_TRADE,
    ema_fast: int = 20,
    ema_slow: int = 50,
    rsi_period: int = 14,
) -> BacktestResult:
    """Long-only EMA crossover with RSI filter; fills at the open of t on signals from t-1, with costs."""
    closes = [c.close for c in candles]
    ema_f = _ema(closes, ema_fast)
    ema_s = _ema(closes, ema_slow)
    rsi = _rsi(closes, rsi_period)
    atr = _atr(candles)

    equity = capital
    position = 0
    qty = 0.0
    entry_price = 0.0
    entry_ts = candles[0].ts
    stop_price = 0.0

    trades: list[Trade] = []
    equity_curve: list[float] = []
    equity_ts: list[datetime] = []
    warmup = max(ema_slow, rsi_period) + 1

    for i, c in enumerate(candles):
        if i < warmup:
            equity_curve.append(equity)
            equity_ts.append(c.ts)
            continue

        if position == 1:
            exit_price = None
            reason = ""
            if c.low <= stop_price:
                exit_price, reason = stop_price, "stop"
            elif ema_f[i - 1] < ema_s[i - 1]:
                exit_price, reason = c.close, "crossunder"
            if exit_price is not None:
                fill = costs.sell_fill(exit_price, atr[i - 1], FEE_RATE)
                pnl = qty * (fill - entry_price)
                equity += pnl
                trades.append(Trade(entry_ts, c.ts, "LONG", entry_price, exit_price, qty, pnl, reason))
                position = 0

        if position == 0:
            crossed_up = ema_f[i - 1] > ema_s[i - 1] and ema_f[i - 2] <= ema_s[i - 2]
            if crossed_up and rsi[i - 1] > 50:
                entry_price = costs.buy_fill(c.open, atr[i - 1], FEE_RATE)
                stop_price = entry_price * 0.95
                risk_amount = equity * risk_per_trade
                per_unit_risk = entry_price - stop_price
                qty = risk_amount / per_unit_risk if per_unit_risk > 0 else 0.0
                if qty > 0:
                    position = 1
                    entry_ts = c.ts

        equity_curve.append(equity)
        equity_ts.append(c.ts)

    return BacktestResult(candles=candles, trades=trades, equity_curve=equity_curve, equity_timestamps=equity_ts)


def compute_metrics(result: BacktestResult, capital: float = DEFAULT_CAPITAL) -> dict:
    trades = result.trades
    if not trades:
        return {
            "total_trades": 0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "total_return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "final_equity": capital,
        }
    wins = [t.pnl for t in trades if t.pnl > 0]
    losses = [t.pnl for t in trades if t.pnl <= 0]
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else float("inf")
    final_equity = result.equity_curve[-1] if result.equity_curve else capital

    peak = capital
    max_dd = 0.0
    for v in result.equity_curve:
        peak = max(peak, v)
        max_dd = max(max_dd, (peak - v) / peak * 100 if peak > 0 else 0.0)

    return {
        "total_trades": len(trades),
        "win_rate_pct": round(len(wins) / len(trades) * 100, 1),
        "profit_factor": round(pf, 2) if pf != float("inf") else None,
        "total_return_pct": round((final_equity / capital - 1) * 100, 1),
        "max_drawdown_pct": round(max_dd, 1),
        "final_equity": round(final_equity, 2),
    }
