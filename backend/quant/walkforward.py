from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class WFAFold:
    label: str
    train_end: str
    test_start: str
    test_end: str
    embargo_days: int = 0


@dataclass
class WFAFoldResult:
    fold_label: str
    winner_label: str
    train_metric: float
    oos_return_pct: float
    oos_sharpe_annualized: float
    oos_n_days: int
    oos_returns: pd.Series | None = field(default=None, repr=False)


@dataclass
class WFAReport:
    fold_results: list[WFAFoldResult]
    selection_metric: str

    def stitched_oos_returns(self) -> pd.Series:
        parts = [f.oos_returns for f in self.fold_results if f.oos_returns is not None]
        return pd.concat(parts).sort_index() if parts else pd.Series(dtype=float)

    @property
    def n_folds_oos_positive(self) -> int:
        return sum(1 for f in self.fold_results if f.oos_return_pct > 0)

    def winner_stability(self) -> dict:
        winners = [f.winner_label for f in self.fold_results]
        changes = sum(1 for a, b in zip(winners, winners[1:], strict=False) if a != b)
        return {"distinct_winners": len(set(winners)), "folds": len(winners), "changes_between_folds": changes}

    def to_dict(self) -> dict:
        return {
            "selection_metric": self.selection_metric,
            "folds_oos_positive": self.n_folds_oos_positive,
            "folds": [
                {
                    "label": f.fold_label,
                    "winner": f.winner_label,
                    "train_metric": round(f.train_metric, 3),
                    "oos_return_pct": round(f.oos_return_pct, 2),
                    "oos_sharpe": round(f.oos_sharpe_annualized, 3),
                    "oos_days": f.oos_n_days,
                }
                for f in self.fold_results
            ],
            "stability": self.winner_stability(),
        }


def _as_index_tz(value: str, index: pd.Index) -> pd.Timestamp:
    """Give naive dates the index's timezone."""
    ts = pd.Timestamp(value)
    tz = getattr(index, "tz", None)
    if tz is not None and ts.tzinfo is None:
        return ts.tz_localize(tz)
    if tz is None and ts.tzinfo is not None:
        return ts.tz_localize(None)
    return ts


def _window(returns: pd.Series, start: str | None, end: str) -> pd.Series:
    r = returns[returns.index <= _as_index_tz(end, returns.index)]
    return r if start is None else r[r.index >= _as_index_tz(start, r.index)]


def _sharpe(r: pd.Series, periods_per_year: int) -> float:
    std = float(r.std(ddof=1))
    return float(r.mean() / std * np.sqrt(periods_per_year)) if std > 0 else 0.0


def walk_forward_analysis(
    backtest_fn: Callable[[dict, str], pd.Series],
    param_grid: Sequence[tuple[str, dict]],
    folds: Sequence[WFAFold],
    *,
    selection_metric: str = "train_return",
    periods_per_year: int = 365,
) -> WFAReport:
    """`backtest_fn(params, data_end)` returns daily returns using data up to `data_end` only."""
    if selection_metric not in ("train_return", "train_sharpe"):
        raise ValueError("selection_metric must be 'train_return' or 'train_sharpe'")

    results: list[WFAFoldResult] = []
    for fold in folds:
        test_start = max(
            pd.Timestamp(fold.test_start), pd.Timestamp(fold.train_end) + pd.Timedelta(days=fold.embargo_days)
        ).strftime("%Y-%m-%d")

        candidates = []
        for label, params in param_grid:
            ret = backtest_fn(params, fold.test_end)
            train = _window(ret, None, fold.train_end)
            test = _window(ret, test_start, fold.test_end)
            if len(train) < 2 or len(test) < 2:
                continue
            metric = (
                float((1 + train).prod() - 1) * 100
                if selection_metric == "train_return"
                else _sharpe(train, periods_per_year)
            )
            candidates.append((metric, label, test))
        if not candidates:
            raise ValueError(f"{fold.label}: no candidate had enough data in train and test")

        metric, label, test = max(candidates, key=lambda c: c[0])
        results.append(
            WFAFoldResult(
                fold_label=fold.label,
                winner_label=label,
                train_metric=metric,
                oos_return_pct=float((1 + test).prod() - 1) * 100,
                oos_sharpe_annualized=_sharpe(test, periods_per_year),
                oos_n_days=len(test),
                oos_returns=test,
            )
        )
    return WFAReport(fold_results=results, selection_metric=selection_metric)
