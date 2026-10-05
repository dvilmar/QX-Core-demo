import json
import logging

from observability import health, json_logging


def test_heartbeat_roundtrip_and_age():
    assert health.read_heartbeat("e1") is None
    health.write_heartbeat("e1", equity=5.0)
    assert health.read_heartbeat("e1")["equity"] == 5.0
    assert 0 <= health.last_tick_age_seconds("e1") < 5
    assert health.list_engine_ids() == ["e1"]


def test_heartbeat_cli_exit_codes():
    assert health.main(["missing"]) == 1
    health.write_heartbeat("alive")
    assert health.main(["alive", "--max-age", "60"]) == 0


def test_json_logging_writes_structured_lines(tmp_path):
    handler = json_logging.attach_json_handler(str(tmp_path), "t.jsonl")
    try:
        logging.getLogger("x").warning("hello %s", "world")
        handler.flush()
    finally:
        logging.getLogger().removeHandler(handler)
        handler.close()
    line = json.loads((tmp_path / "t.jsonl").read_text().splitlines()[0])
    assert line["message"] == "hello world" and line["level"] == "WARNING"


def test_last_tick_age_gauge_is_measured_at_scrape_time(monkeypatch):
    import time

    from fastapi.testclient import TestClient

    from main import app

    health.write_heartbeat("slow-engine")
    real_time = time.time
    monkeypatch.setattr("time.time", lambda: real_time() + 120)
    with TestClient(app) as client:
        text = client.get("/metrics").text
    line = next(ln for ln in text.splitlines() if ln.startswith('qx_last_tick_age_seconds{engine="slow-engine"}'))
    assert float(line.split()[-1]) >= 120
