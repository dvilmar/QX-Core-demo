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

export interface WalkForwardFold {
  label: string;
  winner: string;
  train_metric: number;
  oos_return_pct: number;
  oos_sharpe: number;
  oos_days: number;
}

export interface ValidationResult {
  performance: Record<string, number | string | null>;
  walk_forward: { folds_oos_positive: number; folds: WalkForwardFold[] };
  deflated_sharpe: { dsr: number; sr_hat_annualized: number; sr0_benchmark_annualized: number; n_trials: number } | null;
  monte_carlo: {
    n_paths: number;
    n_trades: number;
    final_return_pct: { p5: number; p50: number; p95: number };
    max_drawdown_pct: { p5: number; p50: number; p95: number };
    prob_loss_pct: number;
  } | null;
}

export interface ValidationStatus {
  job_id: string;
  status: "running" | "done" | "error";
  result?: ValidationResult;
  error?: string;
}

function headers(): HeadersInit {
  return API_KEY ? { "X-API-Key": API_KEY } : {};
}

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}/api${path}`, { headers: headers(), cache: "no-store", credentials: "include" });
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}/api${path}`, {
    method: "POST",
    headers: { ...headers(), "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "include",
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json();
}

export const fetchSnapshot = () => apiGet<Snapshot>("/snapshot");
export const fetchCandles = (limit = 300) => apiGet<Candle[]>(`/candles?limit=${limit}`);
export const fetchTrades = (limit = 50) => apiGet<Trade[]>(`/trades?limit=${limit}`);
export const startBacktest = (params: BacktestParams) => apiPost<{ job_id: string }>("/backtest/run", params);
export const fetchBacktestStatus = (jobId: string) => apiGet<JobStatus>(`/backtest/run/${jobId}`);

export const startValidation = (params: BacktestParams) => apiPost<{ job_id: string }>("/validation/run", params);
export const fetchValidationStatus = (jobId: string) => apiGet<ValidationStatus>(`/validation/run/${jobId}`);

export async function verifySession(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/auth/verify`, { credentials: "include", cache: "no-store" });
    return res.ok;
  } catch {
    return true;
  }
}

export async function login(username: string, password: string): Promise<string | null> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
    credentials: "include",
  });
  if (res.ok) return null;
  if (res.status === 429) return "Too many attempts, try again later";
  return "Invalid credentials";
}

export function wsUrl(): string {
  const base = API_BASE.replace(/^http/, "ws");
  return API_KEY ? `${base}/api/ws?api_key=${API_KEY}` : `${base}/api/ws`;
}
