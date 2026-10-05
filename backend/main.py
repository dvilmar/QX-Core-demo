import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import redis_store
from auth_routes import router as auth_router
from marketdata import store
from observability import health, json_logging, metrics
from observability.killswitch import KillSwitch
from routes import TICK_S, compute_snapshot, live_tick_loop, router, ws_router

if os.getenv("QX_LOG_DIR"):
    json_logging.attach_json_handler(os.environ["QX_LOG_DIR"])

logger = logging.getLogger(__name__)
STALE_AFTER_S = float(os.getenv("QX_STALE_AFTER_S", "60"))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    store.init_db()
    tasks = [asyncio.create_task(live_tick_loop())]
    if redis_store.redis_url():
        tasks.append(asyncio.create_task(redis_store.snapshot_hub.run(compute_snapshot, TICK_S)))
    yield
    for task in tasks:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Algo Trading Dashboard API (demo)", version="2.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(metrics.track_requests)

app.include_router(metrics.router)
app.include_router(auth_router)
app.include_router(router, prefix="/api")
app.include_router(ws_router, prefix="/api")


@app.get("/health")
async def health_check() -> dict:
    engines = {}
    for engine_id in health.list_engine_ids():
        hb = health.read_heartbeat(engine_id) or {}
        age = health.last_tick_age_seconds(engine_id)
        engines[engine_id] = {
            "stale": age is None or age > STALE_AFTER_S,
            "last_tick_age_seconds": age,
            "equity": hb.get("equity"),
            "ws_connected": hb.get("ws_connected"),
            "halted": bool(hb.get("halted")),
        }
    db_ok = await asyncio.to_thread(store.database_ok)
    redis_enabled = redis_store.redis_url() is not None
    redis_ok = await redis_store.ping() if redis_enabled else None
    halted = KillSwitch().active()
    degraded = (not db_ok) or halted or any(e["stale"] for e in engines.values()) or (redis_enabled and not redis_ok)
    return {
        "status": "degraded" if degraded else "ok",
        "api": {"ok": True},
        "database": {"backend": "sqlite", "ok": db_ok},
        "redis": {"enabled": redis_enabled, "ok": redis_ok},
        "halted": halted,
        "engines": engines,
    }
