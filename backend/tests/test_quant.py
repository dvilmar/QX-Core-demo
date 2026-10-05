import numpy as np
import pandas as pd
import pytest

from quant.metrics import drawdown_series, performance_report
from quant.monte_carlo import bootstrap_trades
from quant.statistics import deflated_sharpe_ratio
from quant.walkforward import WFAFold, walk_forward_analysis


def _equity(values, start="2024-01-01"):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="D", tz="UTC"), dtype=float)


def test_drawdown_series():
    dd = drawdown_series(_equity([100, 120, 90, 110]))
    assert dd.min() == pytest.approx(-0.25)


def test_performance_report_known_values():
    report = performance_report(_equity([100, 110, 99, 120]), 100.0)
    assert report["total_return_pct"] == pytest.approx(20.0)
    assert report["max_drawdown_pct"] == pytest.approx(10.0)
    assert report["days"] == 3


def test_performance_report_includes_trade_stats():
    trades = pd.DataFrame({"pnl": [10.0, -5.0, 20.0, -5.0]})
    report = performance_report(_equity(np.linspace(100, 120, 40)), 100.0, trades)
    assert report["trades"] == 4
    assert report["win_rate_pct"] == 50.0
    assert report["profit_factor"] == 3.0


def test_monte_carlo_is_reproducible_and_ordered():
    rets = [0.02, -0.01, 0.015, -0.02, 0.03, -0.005] * 5
    a = bootstrap_trades(rets, n_paths=500, seed=1)
    b = bootstrap_trades(rets, n_paths=500, seed=1)
    assert a == b
    assert a["final_return_pct"]["p5"] <= a["final_return_pct"]["p50"] <= a["final_return_pct"]["p95"]
    assert a["max_drawdown_pct"]["p5"] <= a["max_drawdown_pct"]["p95"]


def test_monte_carlo_all_winners_never_loses():
    result = bootstrap_trades([0.01] * 20, n_paths=200, seed=2)
    assert result["prob_loss_pct"] == 0.0
    assert result["max_drawdown_pct"]["p95"] == 0.0


def test_monte_carlo_needs_two_trades():
    with pytest.raises(ValueError):
        bootstrap_trades([0.01])


def test_dsr_penalises_more_trials():
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0.001, 0.01, 400))
    few = deflated_sharpe_ratio(r, n_trials=2)["dsr"]
    many = deflated_sharpe_ratio(r, n_trials=500)["dsr"]
    assert many < few


def test_dsr_requires_trials_and_enough_data():
    r = pd.Series([0.01, -0.01, 0.02, 0.0])
    with pytest.raises(ValueError):
        deflated_sharpe_ratio(r)
    with pytest.raises(ValueError):
        deflated_sharpe_ratio(r.iloc[:2], n_trials=3)


def _returns(drift, n=400, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2023-01-01", periods=n, freq="D", tz="UTC")
    return pd.Series(rng.normal(drift, 0.01, n), index=idx)


def test_walk_forward_selects_in_sample_and_scores_out_of_sample():
    series = {"good": _returns(0.003, seed=1), "bad": _returns(-0.003, seed=2)}

    def backtest_fn(params, data_end):
        s = series[params["name"]]
        return s[s.index <= pd.Timestamp(data_end, tz="UTC")]

    folds = [WFAFold("f1", "2023-08-01", "2023-08-02", "2023-10-01", embargo_days=1)]
    report = walk_forward_analysis(
        backtest_fn, [("good", {"name": "good"}), ("bad", {"name": "bad"})], folds, selection_metric="train_sharpe"
    )
    assert report.fold_results[0].winner_label == "good"
    assert report.to_dict()["folds"][0]["oos_days"] > 0


def test_walk_forward_embargo_shifts_test_window():
    s = _returns(0.001)

    def backtest_fn(params, data_end):
        return s[s.index <= pd.Timestamp(data_end, tz="UTC")]

    plain = walk_forward_analysis(
        backtest_fn, [("a", {})], [WFAFold("f", "2023-08-01", "2023-08-02", "2023-09-01", embargo_days=0)]
    )
    embargoed = walk_forward_analysis(
        backtest_fn, [("a", {})], [WFAFold("f", "2023-08-01", "2023-08-02", "2023-09-01", embargo_days=10)]
    )
    assert embargoed.fold_results[0].oos_n_days < plain.fold_results[0].oos_n_days


def test_walk_forward_rejects_unknown_metric():
    with pytest.raises(ValueError):
        walk_forward_analysis(lambda p, e: pd.Series(dtype=float), [("a", {})], [], selection_metric="nope")
