import asyncio
import logging
import random
import time
import uuid
from collections.abc import Callable
from contextlib import suppress

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

import alerts
import demo_engine as engine
from auth import check_ws_auth, require_auth
from marketdata import store
from models import (
    BacktestParams,
    CandleOut,
    HaltRequest,
    JobStatusOut,
    MetricsOut,
    RunOut,
    SnapshotOut,
    TradeOut,
)
from observability import health, metrics
from observability.killswitch import KillSwitch
from quant.validation_runner import run_validation
from redis_store import JobStore, snapshot_hub

logger = logging.getLogger(__name__)

ENGINE_ID = "demo-engine"
TICK_S = 10

router = APIRouter(dependencies=[Depends(require_auth)])
ws_router = APIRouter()

_candles = engine.generate_synthetic_candles()
_result = engine.run_demo_backtest(_candles)
_metrics = engine.compute_metrics(_result)

jobs = JobStore("jobs")
_tasks: set[asyncio.Task] = set()
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


def compute_snapshot() -> dict:
    return _snapshot().model_dump(mode="json")


async def _local_snapshot() -> dict:
    return compute_snapshot()


async def current_snapshot() -> dict:
    return await snapshot_hub.get(_local_snapshot)


@router.get("/snapshot", response_model=SnapshotOut)
async def get_snapshot() -> SnapshotOut:
    return SnapshotOut(**await current_snapshot())


@router.get("/candles", response_model=list[CandleOut])
async def get_candles(limit: int = 300) -> list[CandleOut]:
    return [CandleOut(**vars(c)) for c in _candles[-limit:]]


@router.get("/trades", response_model=list[TradeOut])
async def get_trades(limit: int = 50) -> list[TradeOut]:
    return [TradeOut(**vars(t)) for t in _result.trades[-limit:]]


async def _run_job(job_id: str, kind: str, fn: Callable[[], dict]) -> None:
    started = time.perf_counter()
    try:
        payload = await asyncio.to_thread(fn)
        await jobs.put(job_id, {"status": "done", "result": payload})
        metrics.jobs_total.labels(kind=kind, status="done").inc()
    except Exception as e:
        logger.exception("%s job %s failed", kind, job_id)
        await jobs.put(job_id, {"status": "error", "error": str(e)})
        metrics.jobs_total.labels(kind=kind, status="error").inc()
        await asyncio.to_thread(alerts.notify, f"qx-core demo: {kind} job {job_id} failed: {e}")
    finally:
        metrics.job_duration_seconds.labels(kind=kind).observe(time.perf_counter() - started)


async def _start_job(kind: str, fn: Callable[[], dict]) -> dict:
    job_id = str(uuid.uuid4())
    await jobs.put(job_id, {"status": "running"})
    task = asyncio.create_task(_run_job(job_id, kind, fn))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return {"job_id": job_id}


async def _job_status(job_id: str) -> JobStatusOut:
    job = await jobs.get(job_id) or {"status": "error", "error": "unknown job_id"}
    return JobStatusOut(job_id=job_id, **job)


def _backtest(params: BacktestParams) -> dict:
    result = engine.run_demo_backtest(
        engine.generate_synthetic_candles(),
        capital=params.capital,
        risk_per_trade=params.risk_per_trade,
        ema_fast=params.ema_fast,
        ema_slow=params.ema_slow,
        rsi_period=params.rsi_period,
    )
    run_metrics = engine.compute_metrics(result, capital=params.capital)
    payload = {"metrics": run_metrics, "trades": len(result.trades), "final_equity": run_metrics["final_equity"]}
    store.save_run("backtest", params.model_dump(), payload)
    return payload


def _validation(params: BacktestParams) -> dict:
    payload = run_validation(
        engine.generate_synthetic_candles(), capital=params.capital, risk_per_trade=params.risk_per_trade
    )
    store.save_run("validation", params.model_dump(), payload)
    return payload


@router.post("/backtest/run")
async def start_backtest(params: BacktestParams) -> dict:
    return await _start_job("backtest", lambda: _backtest(params))


@router.get("/backtest/run/{job_id}", response_model=JobStatusOut)
async def get_backtest_status(job_id: str) -> JobStatusOut:
    return await _job_status(job_id)


@router.post("/validation/run")
async def start_validation(params: BacktestParams) -> dict:
    return await _start_job("validation", lambda: _validation(params))


@router.get("/validation/run/{job_id}", response_model=JobStatusOut)
async def get_validation_status(job_id: str) -> JobStatusOut:
    return await _job_status(job_id)


@router.get("/runs", response_model=list[RunOut])
async def get_runs(limit: int = 20) -> list[RunOut]:
    return [RunOut(**r) for r in store.list_runs(limit=limit)]


@router.get("/halt")
async def halt_status() -> dict:
    ks = KillSwitch()
    return {"halted": ks.active(), "info": ks.info()}


@router.post("/halt")
async def trip_halt(body: HaltRequest) -> dict:
    ks = KillSwitch()
    ks.trip("api", body.reason)
    return {"halted": True, "info": ks.info()}


@router.post("/resume")
async def resume() -> dict:
    ks = KillSwitch()
    ks.clear()
    return {"halted": ks.active()}


@ws_router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    if not await check_ws_auth(websocket):
        return
    await websocket.accept()
    _ws_clients.add(websocket)
    metrics.engine_ws_clients.set(len(_ws_clients))
    try:
        while True:
            await websocket.send_json(await current_snapshot())
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(websocket)
        metrics.engine_ws_clients.set(len(_ws_clients))


async def live_tick_loop() -> None:
    """Paused while the kill switch is set."""
    rng = random.Random()
    while True:
        await asyncio.sleep(TICK_S)
        halted = KillSwitch().active()
        if not halted:
            last = _candles[-1]
            step = last.close * (1 + rng.gauss(0, 0.0015))
            _candles[-1] = engine.Candle(
                ts=last.ts,
                open=last.close,
                high=max(last.close, step),
                low=min(last.close, step),
                close=step,
                volume=abs(rng.gauss(1_000, 250)),
            )
        equity = _result.equity_curve[-1] if _result.equity_curve else engine.DEFAULT_CAPITAL
        health.write_heartbeat(ENGINE_ID, ws_connected=bool(_ws_clients), equity=equity, halted=halted)
        metrics.engine_equity.labels(engine=ENGINE_ID).set(equity)
        if not halted:
            payload = await current_snapshot()
            for client in list(_ws_clients):
                with suppress(Exception):
                    await client.send_json(payload)
