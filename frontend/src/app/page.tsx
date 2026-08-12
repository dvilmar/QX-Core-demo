"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchCandles, fetchSnapshot, fetchTrades, wsUrl, type Candle, type Snapshot, type Trade } from "@/lib/api";
import Kpi from "@/components/Kpi";
import StatusBar from "@/components/StatusBar";
import CandlestickChart from "@/components/CandlestickChart";
import EquityChart from "@/components/EquityChart";
import TradesTable from "@/components/TradesTable";
import BacktestLab from "@/components/BacktestLab";

export default function Dashboard() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [connected, setConnected] = useState(false);
  const [tab, setTab] = useState<"dashboard" | "lab">("dashboard");
  const wsRef = useRef<WebSocket | null>(null);

  const loadInitial = useCallback(async () => {
    const [snap, c, t] = await Promise.all([fetchSnapshot(), fetchCandles(300), fetchTrades(30)]);
    setSnapshot(snap);
    setCandles(c);
    setTrades(t);
  }, []);

  useEffect(() => {
    loadInitial().catch(() => {});
  }, [loadInitial]);

  useEffect(() => {
    const ws = new WebSocket(wsUrl());
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = (event) => {
      try {
        const data: Snapshot = JSON.parse(event.data);
        setSnapshot(data);
      } catch {
        /* ignore malformed frame */
      }
    };
    return () => ws.close();
  }, []);

  return (
    <div className="min-h-screen p-6 max-w-6xl mx-auto space-y-4">
      <header className="space-y-1">
        <h1 className="text-xl font-semibold">Algo Trading Dashboard</h1>
        <p className="text-sm text-[var(--text-dim)]">
          Full-stack demo (FastAPI + Next.js + Docker) backed by synthetic market data and a simple
          illustrative EMA-crossover signal — not a real trading strategy or live exchange connection.
        </p>
      </header>

      <StatusBar connected={connected} lastPrice={snapshot?.last_price ?? null} />

      <div className="flex gap-1 bg-[var(--bg-card)] border border-[var(--border)] rounded-lg p-1 w-fit">
        {(["dashboard", "lab"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium capitalize transition-colors ${
              tab === t ? "bg-[var(--green-bg)] text-[var(--green)]" : "text-[var(--text-dim)] hover:text-[var(--text)]"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "dashboard" && snapshot && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <Kpi label="Equity" value={`$${snapshot.equity.toFixed(2)}`} />
            <Kpi label="Trades" value={String(snapshot.metrics.total_trades)} />
            <Kpi label="Win Rate" value={`${snapshot.metrics.win_rate_pct.toFixed(1)}%`} />
            <Kpi
              label="Return"
              value={`${snapshot.metrics.total_return_pct >= 0 ? "+" : ""}${snapshot.metrics.total_return_pct.toFixed(1)}%`}
              tone={snapshot.metrics.total_return_pct >= 0 ? "green" : "red"}
            />
            <Kpi label="Max Drawdown" value={`${snapshot.metrics.max_drawdown_pct.toFixed(1)}%`} tone="yellow" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-lg p-4">
              <div className="text-xs uppercase tracking-widest text-[var(--text-dim)] font-medium mb-3">
                Price
              </div>
              {candles.length > 0 && <CandlestickChart candles={candles} />}
            </div>
            <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-lg p-4">
              <div className="text-xs uppercase tracking-widest text-[var(--text-dim)] font-medium mb-3">
                Equity Curve
              </div>
              {snapshot.equity_curve.length > 0 && (
                <EquityChart values={snapshot.equity_curve} timestamps={snapshot.equity_timestamps} />
              )}
            </div>
          </div>

          <TradesTable trades={trades} />
        </div>
      )}

      {tab === "lab" && <BacktestLab />}

      <footer className="text-xs text-[var(--text-muted)] pt-4">
        Portfolio demo project. Synthetic data, no real market or brokerage connection.
      </footer>
    </div>
  );
}
