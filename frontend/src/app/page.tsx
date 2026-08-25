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
    <div className="min-h-screen px-6 py-8 max-w-6xl mx-auto space-y-5">
      <header className="flex flex-col gap-3 pb-2 border-b border-[var(--border)]">
        <div className="flex items-baseline gap-3">
          <span
            aria-hidden
            className="font-display italic text-2xl text-[var(--accent)] leading-none select-none"
          >
            Q
          </span>
          <h1 className="font-display text-2xl md:text-[28px] leading-none text-[var(--text)]">
            Algo Trading Dashboard
          </h1>
        </div>
        <p className="text-sm text-[var(--text-dim)] max-w-2xl">
          Full-stack demo (FastAPI + Next.js + Docker) backed by synthetic market data and a simple
          illustrative EMA-crossover signal — not a real trading strategy or live exchange connection.
        </p>
      </header>

      <StatusBar connected={connected} lastPrice={snapshot?.last_price ?? null} />

      <div className="flex gap-1 panel p-1 w-fit">
        {(["dashboard", "lab"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold capitalize transition-colors ${
              tab === t
                ? "bg-[var(--accent-bg)] text-[var(--accent-strong)]"
                : "text-[var(--text-dim)] hover:text-[var(--text)]"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "dashboard" && snapshot && (
        <div className="space-y-5">
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
            <div className="panel p-4">
              <div className="eyebrow mb-3">Price</div>
              {candles.length > 0 && <CandlestickChart candles={candles} />}
            </div>
            <div className="panel p-4">
              <div className="eyebrow mb-3">Equity Curve</div>
              {snapshot.equity_curve.length > 0 && (
                <EquityChart values={snapshot.equity_curve} timestamps={snapshot.equity_timestamps} />
              )}
            </div>
          </div>

          <TradesTable trades={trades} />
        </div>
      )}

      {tab === "lab" && <BacktestLab />}

      <footer className="text-xs text-[var(--text-muted)] pt-4 pb-2">
        Portfolio demo project. Synthetic data, no real market or brokerage connection.
      </footer>
    </div>
  );
}
