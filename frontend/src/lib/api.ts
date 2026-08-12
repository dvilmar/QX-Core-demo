const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

export interface Candle {
  ts: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Trade {
  entry_ts: string;
  exit_ts: string;
  side: string;
  entry_price: number;
  exit_price: number;
  qty: number;
  pnl: number;
  reason: string;
}

export interface Metrics {
  total_trades: number;
  win_rate_pct: number;
  profit_factor: number | null;
  total_return_pct: number;
  max_drawdown_pct: number;
  final_equity: number;
}

export interface Snapshot {
  last_price: number;
  last_ts: string;
  position: number;
  equity: number;
  metrics: Metrics;
  equity_curve: number[];
  equity_timestamps: string[];
}

export interface BacktestParams {
  capital: number;
  risk_per_trade: number;
  ema_fast: number;
  ema_slow: number;
  rsi_period: number;
}

export interface JobStatus {
  job_id: string;
  status: "running" | "done" | "error";
  result?: { metrics: Metrics; trades: number; final_equity: number };
  error?: string;
}

function headers(): HeadersInit {
  return API_KEY ? { "X-API-Key": API_KEY } : {};
}

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}/api${path}`, { headers: headers(), cache: "no-store" });
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}/api${path}`, {
    method: "POST",
    headers: { ...headers(), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json();
}

export const fetchSnapshot = () => apiGet<Snapshot>("/snapshot");
export const fetchCandles = (limit = 300) => apiGet<Candle[]>(`/candles?limit=${limit}`);
export const fetchTrades = (limit = 50) => apiGet<Trade[]>(`/trades?limit=${limit}`);
export const startBacktest = (params: BacktestParams) => apiPost<{ job_id: string }>("/backtest/run", params);
export const fetchBacktestStatus = (jobId: string) => apiGet<JobStatus>(`/backtest/run/${jobId}`);

export function wsUrl(): string {
  const base = API_BASE.replace(/^http/, "ws");
  return API_KEY ? `${base}/api/ws?api_key=${API_KEY}` : `${base}/api/ws`;
}
