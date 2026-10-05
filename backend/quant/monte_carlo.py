from __future__ import annotations

import numpy as np


def bootstrap_trades(
    trade_returns: list[float] | np.ndarray,
    *,
    n_paths: int = 2000,
    seed: int | None = 7,
    ruin_drawdown: float = 0.5,
) -> dict:
    """Bootstrap per-trade returns (fraction of equity) into final-return and drawdown percentiles."""
    r = np.asarray(trade_returns, dtype=float)
    if r.size < 2:
        raise ValueError("need at least 2 trades to resample")

    rng = np.random.default_rng(seed)
    draws = rng.choice(r, size=(n_paths, r.size), replace=True)
    curves = np.cumprod(1.0 + draws, axis=1)
    final = curves[:, -1] - 1.0
    peaks = np.maximum.accumulate(np.concatenate([np.ones((n_paths, 1)), curves], axis=1), axis=1)[:, 1:]
    max_dd = (1.0 - curves / peaks).max(axis=1)

    def pct(a: np.ndarray, q: float) -> float:
        return round(float(np.percentile(a, q)) * 100, 2)

    return {
        "n_paths": n_paths,
        "n_trades": int(r.size),
        "final_return_pct": {"p5": pct(final, 5), "p50": pct(final, 50), "p95": pct(final, 95)},
        "max_drawdown_pct": {"p5": pct(max_dd, 5), "p50": pct(max_dd, 50), "p95": pct(max_dd, 95)},
        "prob_loss_pct": round(float((final < 0).mean()) * 100, 2),
        "prob_drawdown_over_pct": round(float((max_dd > ruin_drawdown).mean()) * 100, 2),
        "ruin_drawdown_pct": ruin_drawdown * 100,
    }
