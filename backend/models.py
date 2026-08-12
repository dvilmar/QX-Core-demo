"""Pydantic response models for the API."""

from datetime import datetime

from pydantic import BaseModel


class CandleOut(BaseModel):
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class TradeOut(BaseModel):
    entry_ts: datetime
    exit_ts: datetime
    side: str
    entry_price: float
    exit_price: float
    qty: float
    pnl: float
    reason: str


class MetricsOut(BaseModel):
    total_trades: int
    win_rate_pct: float
    profit_factor: float | None
    total_return_pct: float
    max_drawdown_pct: float
    final_equity: float


class SnapshotOut(BaseModel):
    last_price: float
    last_ts: datetime
    position: int
    equity: float
    metrics: MetricsOut
    equity_curve: list[float]
    equity_timestamps: list[datetime]


class BacktestParams(BaseModel):
    capital: float = 10_000.0
    risk_per_trade: float = 0.02
    ema_fast: int = 20
    ema_slow: int = 50
    rsi_period: int = 14


class JobStatusOut(BaseModel):
    job_id: str
    status: str  # "running" | "done" | "error"
    result: dict | None = None
    error: str | None = None
