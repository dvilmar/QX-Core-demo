from __future__ import annotations

import numpy as np
import pandas as pd

PERIODS_PER_YEAR = 365


def daily_equity(equity: pd.Series) -> pd.Series:
    return equity.resample("D").last().ffill().dropna()


def drawdown_series(equity: pd.Series) -> pd.Series:
    return equity / equity.cummax() - 1.0


def daily_returns(equity: pd.Series) -> pd.Series:
    return daily_equity(equity).pct_change().dropna()


def performance_report(
    equity: pd.Series,
    initial_capital: float,
    trades: pd.DataFrame | None = None,
    periods_per_year: int = PERIODS_PER_YEAR,
    var_level: float = 0.95,
) -> dict:
    """Sharpe/Sortino assume a zero risk-free rate and sample std (ddof=1); drawdown uses the raw curve."""
    eq = daily_equity(equity)
    rets = eq.pct_change().dropna()
    n_days = max((eq.index[-1] - eq.index[0]).days, 1)
    years = n_days / 365.25
    final = float(eq.iloc[-1])
    total_return = final / initial_capital - 1.0
    cagr = (final / initial_capital) ** (1.0 / years) - 1.0 if final > 0 and years > 0 else -1.0
    std = float(rets.std(ddof=1)) if len(rets) > 1 else 0.0
    mean = float(rets.mean()) if len(rets) else 0.0
    sharpe = mean / std * np.sqrt(periods_per_year) if std > 0 else 0.0
    downside_dev = float(np.sqrt((rets[rets < 0] ** 2).sum() / len(rets))) if len(rets) else 0.0
    sortino = mean / downside_dev * np.sqrt(periods_per_year) if downside_dev > 0 else 0.0

    raw = equity.sort_index().dropna()
    start_point = pd.Series([initial_capital], index=[raw.index[0] - pd.Timedelta(seconds=1)])
    max_dd = float(-drawdown_series(pd.concat([start_point, raw])).min())
    calmar = cagr / max_dd if max_dd > 0 else 0.0

    q = float(np.quantile(rets, 1.0 - var_level)) if len(rets) else 0.0
    tail = rets[rets <= q]
    pct = int(var_level * 100)
    report: dict = {
        "start": str(eq.index[0].date()),
        "end": str(eq.index[-1].date()),
        "days": n_days,
        "initial_capital": initial_capital,
        "final_equity": round(final, 2),
        "total_return_pct": round(total_return * 100, 2),
        "cagr_pct": round(cagr * 100, 2),
        "volatility_pct": round(std * np.sqrt(periods_per_year) * 100, 2),
        "sharpe": round(float(sharpe), 3),
        "sortino": round(float(sortino), 3),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "calmar": round(float(calmar), 3),
        f"var_{pct}_daily_pct": round(-q * 100, 3),
        f"cvar_{pct}_daily_pct": round(-float(tail.mean()) * 100, 3) if len(tail) else 0.0,
    }
    if trades is not None:
        report.update(trade_stats(trades, years))
    return report


def trade_stats(trades: pd.DataFrame, years: float) -> dict:
    n = len(trades)
    if n == 0:
        return {"trades": 0}
    pnl = trades["pnl"].astype(float)
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    gross_loss = float(-losses.sum())
    return {
        "trades": n,
        "win_rate_pct": round(len(wins) / n * 100, 2),
        "profit_factor": round(float(wins.sum()) / gross_loss, 3) if gross_loss > 0 else None,
        "avg_win": round(float(wins.mean()), 2) if len(wins) else 0.0,
        "avg_loss": round(float(losses.mean()), 2) if len(losses) else 0.0,
        "trades_per_year": round(n / years, 2) if years > 0 else None,
    }
