from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

import demo_engine as engine
from quant.adapters import equity_series
from quant.metrics import daily_returns, performance_report
from quant.monte_carlo import bootstrap_trades
from quant.statistics import deflated_sharpe_ratio
from quant.walkforward import WFAFold, walk_forward_analysis

FAST_GRID = (10, 20, 30)
SLOW_GRID = (50, 100)
N_FOLDS = 3


def _grid() -> list[tuple[str, dict]]:
    return [(f"ema{f}/{s}", {"ema_fast": f, "ema_slow": s}) for f, s in itertools.product(FAST_GRID, SLOW_GRID)]


def _folds(index: pd.DatetimeIndex, n_folds: int = N_FOLDS, train_share: float = 0.5) -> list[WFAFold]:
    start, end = index[0], index[-1]
    span = end - start
    test_len = span * (1 - train_share) / n_folds
    folds = []
    for k in range(n_folds):
        train_end = start + span * train_share + test_len * k
        test_end = train_end + test_len
        folds.append(
            WFAFold(
                label=f"fold{k + 1}",
                train_end=train_end.strftime("%Y-%m-%d"),
                test_start=(train_end + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                test_end=test_end.strftime("%Y-%m-%d"),
                embargo_days=1,
            )
        )
    return folds


def run_validation(
    candles: list[engine.Candle],
    *,
    capital: float = engine.DEFAULT_CAPITAL,
    risk_per_trade: float = engine.RISK_PER_TRADE,
    mc_paths: int = 2000,
    seed: int = 7,
) -> dict:
    grid = _grid()

    def backtest_fn(params: dict, data_end: str) -> pd.Series:
        cutoff = pd.Timestamp(data_end, tz="UTC") + pd.Timedelta(days=1)
        subset = [c for c in candles if pd.Timestamp(c.ts) < cutoff]
        result = engine.run_demo_backtest(subset, capital=capital, risk_per_trade=risk_per_trade, **params)
        return daily_returns(equity_series(result))

    index = pd.DatetimeIndex(pd.to_datetime([c.ts for c in candles], utc=True))
    report = walk_forward_analysis(backtest_fn, grid, _folds(index), selection_metric="train_sharpe")
    stitched = report.stitched_oos_returns()

    full = engine.run_demo_backtest(candles, capital=capital, risk_per_trade=risk_per_trade)
    equity = equity_series(full)
    perf = performance_report(equity, capital, pd.DataFrame([{"pnl": t.pnl} for t in full.trades]))

    trial_sharpes = np.array(
        [
            s
            for _, params in grid
            if (s := _daily_sharpe(backtest_fn(params, index[-1].strftime("%Y-%m-%d")))) is not None
        ]
    )
    dsr = (
        deflated_sharpe_ratio(stitched, trial_sharpes=trial_sharpes)
        if len(stitched) >= 3 and len(trial_sharpes) >= 2
        else None
    )

    trade_returns = [t.pnl / capital for t in full.trades]
    mc = bootstrap_trades(trade_returns, n_paths=mc_paths, seed=seed) if len(trade_returns) >= 2 else None

    return {
        "performance": perf,
        "walk_forward": report.to_dict(),
        "deflated_sharpe": dsr,
        "monte_carlo": mc,
        "candidates": [label for label, _ in grid],
    }


def _daily_sharpe(returns: pd.Series) -> float | None:
    std = float(returns.std(ddof=1)) if len(returns) > 1 else 0.0
    return float(returns.mean() / std) if std > 0 else None
