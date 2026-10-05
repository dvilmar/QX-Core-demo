import pytest
from fastapi.testclient import TestClient

from main import app
from observability.killswitch import KillSwitch


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_trip_info_and_clear(tmp_path):
    ks = KillSwitch(str(tmp_path))
    assert not ks.active() and ks.info() is None
    ks.trip("tester", "because")
    assert ks.active()
    assert ks.info()["reason"] == "because" and ks.info()["by"] == "tester"
    assert ks.clear() is True
    assert ks.clear() is False and not ks.active()


def test_unreadable_sentinel_still_halts(tmp_path):
    ks = KillSwitch(str(tmp_path))
    (tmp_path / ".HALT").write_text("not json")
    assert ks.active() and ks.info() == {}


def test_halt_endpoints_and_health(client):
    assert client.get("/api/halt").json()["halted"] is False
    assert client.post("/api/halt", json={"reason": "drill"}).json()["info"]["reason"] == "drill"
    health = client.get("/health").json()
    assert health["halted"] is True and health["status"] == "degraded"
    assert client.post("/api/resume").json() == {"halted": False}
    assert client.get("/health").json()["halted"] is False
