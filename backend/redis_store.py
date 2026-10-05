import asyncio
import json
import logging
import os
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

SNAPSHOT_KEY = "qx:snapshot"
LEADER_KEY = "qx:snapshot:leader"
LEADER_TTL_S = 3
SNAPSHOT_TTL_S = 5
JOB_TTL_S = 3600

_client: Any = None
_client_loop: Any = None


def redis_url() -> str | None:
    return os.environ.get("REDIS_URL", "") or None


def get_client() -> Any:
    global _client, _client_loop
    url = redis_url()
    if url is None:
        return None
    loop = asyncio.get_running_loop()
    if _client is None or _client_loop is not loop:
        import redis.asyncio as aioredis

        _client = aioredis.Redis.from_url(url, decode_responses=True, socket_timeout=2, socket_connect_timeout=2)
        _client_loop = loop
    return _client


async def ping() -> bool:
    client = get_client()
    if client is None:
        return False
    try:
        return bool(await client.ping())
    except Exception:
        return False


class JobStore:
    def __init__(self, namespace: str) -> None:
        self.namespace = namespace
        self._local: dict[str, dict] = {}

    def _key(self, job_id: str) -> str:
        return f"qx:job:{self.namespace}:{job_id}"

    async def put(self, job_id: str, job: dict) -> None:
        self._local[job_id] = job
        client = get_client()
        if client is None:
            return
        try:
            await client.set(self._key(job_id), json.dumps(job, default=str), ex=JOB_TTL_S)
        except Exception:
            logger.warning("redis job write failed; keeping it in memory", exc_info=True)

    async def get(self, job_id: str) -> dict | None:
        client = get_client()
        if client is not None:
            try:
                raw = await client.get(self._key(job_id))
                if raw is not None:
                    return json.loads(raw)
            except Exception:
                logger.warning("redis job read failed; using memory", exc_info=True)
        return self._local.get(job_id)


class SnapshotHub:
    """One elected worker computes the snapshot; all workers serve it."""

    def __init__(self) -> None:
        self.worker_id = uuid.uuid4().hex
        self.is_leader = False

    async def get(self, fallback: Callable[[], Awaitable[dict]]) -> dict:
        client = get_client()
        if client is not None:
            try:
                raw = await client.get(SNAPSHOT_KEY)
                if raw is not None:
                    return json.loads(raw)
            except Exception:
                logger.warning("redis snapshot read failed; computing locally", exc_info=True)
        return await fallback()

    async def _try_lead(self, client: Any) -> bool:
        if await client.set(LEADER_KEY, self.worker_id, nx=True, ex=LEADER_TTL_S):
            return True
        if await client.get(LEADER_KEY) == self.worker_id:
            await client.expire(LEADER_KEY, LEADER_TTL_S)
            return True
        return False

    async def publish_once(self, compute: Callable[[], dict]) -> bool:
        client = get_client()
        if client is None:
            self.is_leader = False
            return False
        try:
            self.is_leader = await self._try_lead(client)
            if not self.is_leader:
                return False
            snapshot = await asyncio.to_thread(compute)
            await client.set(SNAPSHOT_KEY, json.dumps(snapshot, default=str), ex=SNAPSHOT_TTL_S)
            return True
        except Exception:
            self.is_leader = False
            logger.warning("redis snapshot publish failed", exc_info=True)
            return False

    async def run(self, compute: Callable[[], dict], interval_s: float) -> None:
        while True:
            await self.publish_once(compute)
            await asyncio.sleep(interval_s)


snapshot_hub = SnapshotHub()
