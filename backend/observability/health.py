from __future__ import annotations

import json
import os
import time
from typing import Any


def health_dir() -> str:
    return os.path.join(os.environ.get("QX_DATA_DIR", "data"), "health")


def _path(engine_id: str) -> str:
    return os.path.join(health_dir(), f"{engine_id}.json")


def write_heartbeat(engine_id: str, **fields: Any) -> None:
    payload = {"last_tick_at_unix": time.time(), **fields}
    os.makedirs(health_dir(), exist_ok=True)
    tmp = _path(engine_id) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    os.replace(tmp, _path(engine_id))


def read_heartbeat(engine_id: str) -> dict[str, Any] | None:
    try:
        with open(_path(engine_id), encoding="utf-8") as f:
            parsed = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def last_tick_age_seconds(engine_id: str) -> float | None:
    hb = read_heartbeat(engine_id)
    if not hb or "last_tick_at_unix" not in hb:
        return None
    try:
        return round(time.time() - float(hb["last_tick_at_unix"]), 1)
    except (TypeError, ValueError):
        return None


def list_engine_ids() -> list[str]:
    try:
        names = os.listdir(health_dir())
    except OSError:
        return []
    return sorted(n[: -len(".json")] for n in names if n.endswith(".json"))


def main(argv: list[str] | None = None) -> int:
    """Exit 0 when the heartbeat is fresh (used by the Docker HEALTHCHECK)."""
    import argparse

    parser = argparse.ArgumentParser(description="Exit 0 when the engine heartbeat is fresh.")
    parser.add_argument("engine_id")
    parser.add_argument("--max-age", type=float, default=300.0)
    args = parser.parse_args(argv)
    age = last_tick_age_seconds(args.engine_id)
    return 0 if age is not None and age <= args.max_age else 1


if __name__ == "__main__":
    raise SystemExit(main())
