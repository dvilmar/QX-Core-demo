"use client";

import { useState } from "react";
import { startBacktest, fetchBacktestStatus, type BacktestParams, type Metrics } from "@/lib/api";
import Kpi from "@/components/Kpi";

const DEFAULT_PARAMS: BacktestParams = {
  capital: 10_000,
  risk_per_trade: 0.02,
  ema_fast: 20,
  ema_slow: 50,
  rsi_period: 14,
};

export default function BacktestLab() {
  const [params, setParams] = useState<BacktestParams>(DEFAULT_PARAMS);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  const field = (key: keyof BacktestParams, label: string, step: number) => (
    <label className="flex flex-col gap-1.5 text-xs text-[var(--text-dim)] font-medium">
      {label}
      <input
        type="number"
        step={step}
        value={params[key]}
        onChange={(e) => setParams((p) => ({ ...p, [key]: Number(e.target.value) }))}
        className="bg-[var(--bg)] border border-[var(--border)] rounded-lg px-2.5 py-1.5 text-sm text-[var(--text)] tabular-nums transition-colors focus:border-[var(--accent)] outline-none"
      />
    </label>
  );

  async function run() {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const { job_id } = await startBacktest(params);
      // simple poll loop -- same async-job pattern as the live app
      for (let i = 0; i < 20; i++) {
        await new Promise((r) => setTimeout(r, 400));
        const status = await fetchBacktestStatus(job_id);
        if (status.status === "done" && status.result) {
          setResult(status.result.metrics);
          break;
        }
        if (status.status === "error") {
          setError(status.error ?? "Unknown error");
          break;
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="panel p-4 space-y-4">
      <div className="eyebrow">Backtest Lab — run the demo strategy with custom parameters</div>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {field("capital", "Capital ($)", 1000)}
        {field("risk_per_trade", "Risk / Trade", 0.01)}
        {field("ema_fast", "EMA Fast", 1)}
        {field("ema_slow", "EMA Slow", 1)}
        {field("rsi_period", "RSI Period", 1)}
      </div>
      <button
        onClick={run}
        disabled={running}
        className="bg-[var(--accent-bg)] text-[var(--accent-strong)] border border-[var(--accent)]/30 rounded-lg px-4 py-2 text-sm font-semibold hover:bg-[var(--accent)]/20 transition-colors disabled:opacity-50"
      >
        {running ? "Running…" : "Run Backtest"}
      </button>

      {error && <div className="text-sm text-[var(--red)]">{error}</div>}

      {result && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 pt-2">
          <Kpi label="Trades" value={String(result.total_trades)} />
          <Kpi label="Win Rate" value={`${result.win_rate_pct.toFixed(1)}%`} />
          <Kpi
            label="Profit Factor"
            value={result.profit_factor?.toFixed(2) ?? "∞"}
            tone={result.profit_factor && result.profit_factor >= 1 ? "green" : "red"}
          />
          <Kpi
            label="Return"
            value={`${result.total_return_pct >= 0 ? "+" : ""}${result.total_return_pct.toFixed(1)}%`}
            tone={result.total_return_pct >= 0 ? "green" : "red"}
          />
          <Kpi label="Max Drawdown" value={`${result.max_drawdown_pct.toFixed(1)}%`} tone="yellow" />
        </div>
      )}
    </div>
  );
}
