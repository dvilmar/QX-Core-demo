import secrets
import time

import pytest
from fastapi.testclient import TestClient

from main import app
from observability import health


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _wait(client, path, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(path).json()
        if body["status"] != "running":
            return body
        time.sleep(0.2)
    raise AssertionError("job did not finish")


def test_health_reports_ok_without_engines(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["database"]["ok"] is True


def test_health_degrades_on_stale_heartbeat(client, monkeypatch):
    health.write_heartbeat("demo-engine", equity=1.0)
    monkeypatch.setattr("main.STALE_AFTER_S", -1.0)
    body = client.get("/health").json()
    assert body["status"] == "degraded"
    assert body["engines"]["demo-engine"]["stale"] is True


def test_metrics_endpoint_exposes_request_counters(client):
    client.get("/api/snapshot")
    text = client.get("/metrics").text
    assert "qx_api_http_requests_total" in text


def test_snapshot_and_candles(client):
    snap = client.get("/api/snapshot").json()
    assert snap["equity"] > 0
    assert len(client.get("/api/candles?limit=10").json()) == 10


def test_backtest_job_is_persisted(client):
    job = client.post("/api/backtest/run", json={}).json()["job_id"]
    body = _wait(client, f"/api/backtest/run/{job}")
    assert body["status"] == "done"
    runs = client.get("/api/runs").json()
    assert runs and runs[0]["kind"] == "backtest"


def test_validation_job_returns_full_battery(client):
    job = client.post("/api/validation/run", json={}).json()["job_id"]
    body = _wait(client, f"/api/validation/run/{job}")
    assert body["status"] == "done", body.get("error")
    result = body["result"]
    assert len(result["walk_forward"]["folds"]) == 3
    assert "performance" in result and "monte_carlo" in result


def test_unknown_job(client):
    assert client.get("/api/backtest/run/nope").json()["status"] == "error"


def test_api_key_is_enforced_when_configured(client, monkeypatch):
    key = secrets.token_hex(8)
    monkeypatch.setattr("auth.API_KEY", key)
    assert client.get("/api/snapshot").status_code == 401
    assert client.get("/api/snapshot", headers={"X-API-Key": key}).status_code == 200
