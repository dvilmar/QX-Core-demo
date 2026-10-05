"use client";

import { useState } from "react";
import { startValidation, fetchValidationStatus, type ValidationResult } from "@/lib/api";
import Kpi from "@/components/Kpi";

const PARAMS = { capital: 10_000, risk_per_trade: 0.02, ema_fast: 20, ema_slow: 50, rsi_period: 14 };

export default function ValidationLab() {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const { job_id } = await startValidation(PARAMS);
      for (let i = 0; i < 60; i++) {
        await new Promise((r) => setTimeout(r, 500));
        const status = await fetchValidationStatus(job_id);
        if (status.status === "done" && status.result) {
          setResult(status.result);
          return;
        }
        if (status.status === "error") {
          setError(status.error ?? "Unknown error");
          return;
        }
      }
      setError("Validation timed out");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  const mc = result?.monte_carlo;
  const dsr = result?.deflated_sharpe;

  return (
    <div className="panel p-4 space-y-4">
      <div className="eyebrow">Validation — walk-forward, deflated Sharpe and Monte Carlo on the demo signal</div>
      <p className="text-sm text-[var(--text-dim)] max-w-2xl">
        Picks the best EMA pair on each in-sample window and scores it on the unseen window that follows. On random
        data the out-of-sample results should be unimpressive — that is the point of the check.
      </p>
      <button
        onClick={run}
        disabled={running}
        className="bg-[var(--accent-bg)] text-[var(--accent-strong)] border border-[var(--accent)]/30 rounded-lg px-4 py-2 text-sm font-semibold hover:bg-[var(--accent)]/20 transition-colors disabled:opacity-50"
      >
        {running ? "Running…" : "Run validation"}
      </button>

      {error && <div className="text-sm text-[var(--red)]">{error}</div>}

      {result && (
        <div className="space-y-4 pt-2">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Kpi
              label="OOS folds positive"
              value={`${result.walk_forward.folds_oos_positive}/${result.walk_forward.folds.length}`}
            />
            {dsr && (
              <Kpi label="Deflated Sharpe" value={dsr.dsr.toFixed(2)} tone={dsr.dsr >= 0.95 ? "green" : "red"} />
            )}
            {mc && <Kpi label="P(loss), Monte Carlo" value={`${mc.prob_loss_pct.toFixed(1)}%`} tone="yellow" />}
            {mc && <Kpi label="Max DD p95" value={`${mc.max_drawdown_pct.p95.toFixed(1)}%`} tone="yellow" />}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm tabular-nums">
              <thead className="text-xs text-[var(--text-dim)] text-left">
                <tr>
                  <th className="py-1.5 pr-4">Fold</th>
                  <th className="pr-4">Selected in-sample</th>
                  <th className="pr-4">OOS return</th>
                  <th className="pr-4">OOS Sharpe</th>
                  <th>OOS days</th>
                </tr>
              </thead>
              <tbody>
                {result.walk_forward.folds.map((f) => (
                  <tr key={f.label} className="border-t border-[var(--border)]">
                    <td className="py-1.5 pr-4">{f.label}</td>
                    <td className="pr-4">{f.winner}</td>
                    <td className={`pr-4 ${f.oos_return_pct >= 0 ? "text-[var(--green)]" : "text-[var(--red)]"}`}>
                      {f.oos_return_pct >= 0 ? "+" : ""}
                      {f.oos_return_pct.toFixed(1)}%
                    </td>
                    <td className="pr-4">{f.oos_sharpe.toFixed(2)}</td>
                    <td>{f.oos_days}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {mc && (
            <div className="text-xs text-[var(--text-dim)]">
              Monte Carlo ({mc.n_paths} resamples of {mc.n_trades} trades): final return p5 {mc.final_return_pct.p5}% /
              p50 {mc.final_return_pct.p50}% / p95 {mc.final_return_pct.p95}%.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
