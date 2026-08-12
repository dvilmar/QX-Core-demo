"""
REST + WebSocket API. Same shape/patterns as the private version of this
project (async job queue for long-running backtests, WebSocket push for
live updates, simple API-key auth) — wired here to the synthetic demo
engine instead of a real exchange/strategy.
"""

import asyncio
import uuid
from contextlib import suppress

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

import demo_engine as engine
from auth import check_ws_api_key, require_api_key
from models import BacktestParams, CandleOut, JobStatusOut, MetricsOut, SnapshotOut, TradeOut

router = APIRouter(dependencies=[Depends(require_api_key)])

# ── In-memory demo state (regenerated at process start; no DB needed) ──────
_candles = engine.generate_synthetic_candles()
_result = engine.run_demo_backtest(_candles)
_metrics = engine.compute_metrics(_result)

_jobs: dict[str, dict] = {}
_ws_clients: set[WebSocket] = set()


def _snapshot() -> SnapshotOut:
    last = _candles[-1]
    position = 1 if _result.trades and _result.trades[-1].exit_ts == last.ts else 0
    return SnapshotOut(
        last_price=last.close,
        last_ts=last.ts,
        position=position,
        equity=_result.equity_curve[-1] if _result.equity_curve else engine.DEFAULT_CAPITAL,
        metrics=MetricsOut(**_metrics),
        equity_curve=_result.equity_curve[-500:],
        equity_timestamps=_result.equity_timestamps[-500:],
    )


@router.get("/snapshot", response_model=SnapshotOut)
async def get_snapshot() -> SnapshotOut:
    return _snapshot()


@router.get("/candles", response_model=list[CandleOut])
async def get_candles(limit: int = 300) -> list[CandleOut]:
    return [CandleOut(**vars(c)) for c in _candles[-limit:]]


@router.get("/trades", response_model=list[TradeOut])
async def get_trades(limit: int = 50) -> list[TradeOut]:
    return [TradeOut(**vars(t)) for t in _result.trades[-limit:]]


def _run_backtest_job(job_id: str, params: BacktestParams) -> None:
    try:
        candles = engine.generate_synthetic_candles()
        result = engine.run_demo_backtest(
            candles,
            capital=params.capital,
            risk_per_trade=params.risk_per_trade,
            ema_fast=params.ema_fast,
            ema_slow=params.ema_slow,
            rsi_period=params.rsi_period,
        )
        metrics = engine.compute_metrics(result, capital=params.capital)
        _jobs[job_id] = {
            "status": "done",
            "result": {
                "metrics": metrics,
                "trades": len(result.trades),
                "final_equity": metrics["final_equity"],
            },
        }
    except Exception as e:  # pragma: no cover - defensive, demo endpoint
        _jobs[job_id] = {"status": "error", "error": str(e)}


@router.post("/backtest/run")
async def start_backtest(params: BacktestParams) -> dict:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "running"}
    asyncio.create_task(asyncio.to_thread(_run_backtest_job, job_id, params))
    return {"job_id": job_id}


@router.get("/backtest/run/{job_id}", response_model=JobStatusOut)
async def get_backtest_status(job_id: str) -> JobStatusOut:
    job = _jobs.get(job_id, {"status": "error", "error": "unknown job_id"})
    return JobStatusOut(job_id=job_id, **job)


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    if not await check_ws_api_key(websocket):
        return
    await websocket.accept()
    _ws_clients.add(websocket)
    try:
        while True:
            await websocket.send_json(_snapshot().model_dump(mode="json"))
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(websocket)


async def live_tick_loop() -> None:
    """Advances the synthetic price by one small random step periodically so
    the dashboard has something visibly 'live' to show, without any real
    exchange connection."""
    import random

    rng = random.Random()
    while True:
        await asyncio.sleep(10)
        last = _candles[-1]
        step = last.close * (1 + rng.gauss(0, 0.0015))
        new_candle = engine.Candle(
            ts=last.ts,
            open=last.close,
            high=max(last.close, step),
            low=min(last.close, step),
            close=step,
            volume=abs(rng.gauss(1_000, 250)),
        )
        _candles[-1] = new_candle
        for client in list(_ws_clients):
            with suppress(Exception):
                await client.send_json(_snapshot().model_dump(mode="json"))
