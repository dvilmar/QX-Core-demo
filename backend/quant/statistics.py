from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import norm

GAMMA_EULER = 0.5772156649015329


def deflated_sharpe_ratio(
    winner_returns: pd.Series,
    *,
    trial_sharpes: np.ndarray | None = None,
    n_trials: int | None = None,
    periods_per_year: int = 365,
) -> dict:
    """Probability that the winner's Sharpe beats the best Sharpe expected by luck over N trials."""
    if trial_sharpes is None and n_trials is None:
        raise ValueError("pass trial_sharpes (preferred) or n_trials (approximation)")

    r = winner_returns.dropna().to_numpy()
    t = len(r)
    if t < 3:
        raise ValueError(f"T={t} is too short for a DSR (need at least 3 observations)")

    sr_hat = r.mean() / r.std(ddof=1)
    skew = float(stats.skew(r))
    kurt = float(stats.kurtosis(r, fisher=False))

    if trial_sharpes is not None:
        n = len(trial_sharpes)
        sigma_sr = float(np.std(trial_sharpes, ddof=1))
        method = "empirical_sigma_sr"
    else:
        assert n_trials is not None
        n = n_trials
        sigma_sr = 1.0 / np.sqrt(max(t - 1, 1))
        method = "approx_sigma_sr_under_null"

    sr0 = sigma_sr * ((1 - GAMMA_EULER) * norm.ppf(1 - 1.0 / n) + GAMMA_EULER * norm.ppf(1 - 1.0 / (n * np.e)))
    denom = np.sqrt(max(1 - skew * sr_hat + ((kurt - 1) / 4) * sr_hat**2, 1e-12))
    dsr = float(norm.cdf((sr_hat - sr0) * np.sqrt(t - 1) / denom))
    return {
        "dsr": dsr,
        "sr_hat_annualized": float(sr_hat * np.sqrt(periods_per_year)),
        "sr0_benchmark_annualized": float(sr0 * np.sqrt(periods_per_year)),
        "n_trials": n,
        "method": method,
        "T": t,
    }
