from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from types import ModuleType
from typing import Any

from fastapi import APIRouter, Request, Response

try:
    import prometheus_client

    prom: ModuleType | None = prometheus_client
except ImportError:  # pragma: no cover - only without the dependency
    prom = None


class _NoOp:
    def labels(self, *_a: object, **_k: object) -> _NoOp:
        return self

    def inc(self, *_a: object, **_k: object) -> None: ...

    def set(self, *_a: object, **_k: object) -> None: ...

    def observe(self, *_a: object, **_k: object) -> None: ...


def _make(kind: str, *args: Any, **kwargs: Any) -> Any:
    return getattr(prom, kind)(*args, **kwargs) if prom else _NoOp()


http_requests_total = _make(
    "Counter", "qx_api_http_requests_total", "HTTP requests handled by the API", ["method", "path", "status"]
)
http_request_duration_seconds = _make(
    "Histogram", "qx_api_http_request_duration_seconds", "HTTP request duration", ["method", "path"]
)
engine_equity = _make("Gauge", "qx_equity_usd", "Current demo-engine equity in USD", ["engine"])
engine_last_tick_age = _make(
    "Gauge", "qx_last_tick_age_seconds", "Seconds since the engine last processed a tick", ["engine"]
)
engine_ws_clients = _make("Gauge", "qx_ws_clients", "Connected dashboard WebSocket clients")
jobs_total = _make("Counter", "qx_jobs_total", "Background jobs finished", ["kind", "status"])
job_duration_seconds = _make("Histogram", "qx_job_duration_seconds", "Background job duration", ["kind"])

router = APIRouter()


async def track_requests(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    start = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    path = route.path if route is not None else "unmatched"
    http_requests_total.labels(method=request.method, path=path, status=response.status_code).inc()
    http_request_duration_seconds.labels(method=request.method, path=path).observe(time.perf_counter() - start)
    return response


def refresh_heartbeat_gauges() -> None:
    """Measure heartbeat age at scrape time, not at write time."""
    from observability import health

    for engine_id in health.list_engine_ids():
        age = health.last_tick_age_seconds(engine_id)
        if age is not None:
            engine_last_tick_age.labels(engine=engine_id).set(age)


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    if prom is None:
        return Response("# prometheus_client not installed\n", media_type="text/plain")
    refresh_heartbeat_gauges()
    return Response(prom.generate_latest(), media_type=prom.CONTENT_TYPE_LATEST)
