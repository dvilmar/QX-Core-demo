import json

import fakeredis
import pytest

import redis_store
from redis_store import JobStore, SnapshotHub


@pytest.fixture()
def fake(monkeypatch):
    client = fakeredis.FakeAsyncRedis(decode_responses=True)
    monkeypatch.setattr(redis_store, "get_client", lambda: client)
    return client


async def test_job_store_roundtrip_in_redis(fake):
    store = JobStore("t")
    await store.put("a", {"status": "done"})
    assert json.loads(await fake.get("qx:job:t:a")) == {"status": "done"}
    assert await JobStore("t").get("a") == {"status": "done"}
    assert await store.get("missing") is None


async def test_job_store_falls_back_to_memory_without_redis(monkeypatch):
    monkeypatch.setattr(redis_store, "get_client", lambda: None)
    store = JobStore("t")
    await store.put("a", {"status": "running"})
    assert await store.get("a") == {"status": "running"}


async def test_only_one_worker_publishes(fake):
    first, second = SnapshotHub(), SnapshotHub()
    assert await first.publish_once(lambda: {"v": 1}) is True
    assert await second.publish_once(lambda: {"v": 2}) is False
    assert first.is_leader and not second.is_leader
    assert await second.get(_never) == {"v": 1}


async def test_leader_keeps_leading_on_next_tick(fake):
    hub = SnapshotHub()
    assert await hub.publish_once(lambda: {"v": 1})
    assert await hub.publish_once(lambda: {"v": 2})
    assert await hub.get(_never) == {"v": 2}


async def test_get_falls_back_when_nothing_published(fake):
    async def local() -> dict:
        return {"local": True}

    assert await SnapshotHub().get(local) == {"local": True}


async def test_publish_failure_drops_leadership(monkeypatch):
    class Broken:
        async def set(self, *a, **k):
            raise ConnectionError("down")

    monkeypatch.setattr(redis_store, "get_client", lambda: Broken())
    hub = SnapshotHub()
    assert await hub.publish_once(lambda: {}) is False
    assert hub.is_leader is False


async def test_ping(fake, monkeypatch):
    assert await redis_store.ping() is True
    monkeypatch.setattr(redis_store, "get_client", lambda: None)
    assert await redis_store.ping() is False


async def _never() -> dict:
    raise AssertionError("fallback should not run")
