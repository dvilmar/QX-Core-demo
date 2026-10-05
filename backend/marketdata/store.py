from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS candles (
    symbol    TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    ts        INTEGER NOT NULL,
    open      REAL NOT NULL,
    high      REAL NOT NULL,
    low       REAL NOT NULL,
    close     REAL NOT NULL,
    volume    REAL NOT NULL,
    PRIMARY KEY (symbol, timeframe, ts)
);
CREATE TABLE IF NOT EXISTS backtest_runs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    kind       TEXT NOT NULL,
    params     TEXT NOT NULL,
    result     TEXT NOT NULL
);
"""


def db_path() -> str:
    return os.environ.get("QX_DB_PATH", os.path.join(os.environ.get("QX_DATA_DIR", "data"), "qx.db"))


@contextmanager
def connect(path: str | None = None) -> Iterator[sqlite3.Connection]:
    path = path or db_path()
    if os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(path: str | None = None) -> None:
    with connect(path) as conn:
        conn.executescript(SCHEMA)


def upsert_candles(frame: pd.DataFrame, symbol: str, timeframe: str, path: str | None = None) -> int:
    """`frame` is indexed by UTC timestamp with open/high/low/close/volume."""
    rows = [
        (symbol, timeframe, int(ts.timestamp() * 1000), r.open, r.high, r.low, r.close, r.volume)
        for ts, r in frame.iterrows()
    ]
    with connect(path) as conn:
        conn.executemany("INSERT OR REPLACE INTO candles VALUES (?,?,?,?,?,?,?,?)", rows)
    return len(rows)


def load_candles(symbol: str, timeframe: str, path: str | None = None) -> pd.DataFrame:
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT ts, open, high, low, close, volume FROM candles WHERE symbol=? AND timeframe=? ORDER BY ts",
            (symbol, timeframe),
        ).fetchall()
    frame = pd.DataFrame([dict(r) for r in rows], columns=["ts", "open", "high", "low", "close", "volume"])
    frame["ts"] = pd.to_datetime(frame["ts"], unit="ms", utc=True)
    return frame.set_index("ts")


def save_run(kind: str, params: dict, result: dict, path: str | None = None) -> int:
    with connect(path) as conn:
        cur = conn.execute(
            "INSERT INTO backtest_runs (created_at, kind, params, result) VALUES (?,?,?,?)",
            (datetime.now(UTC).isoformat(timespec="seconds"), kind, json.dumps(params), json.dumps(result)),
        )
        return int(cur.lastrowid or 0)


def list_runs(limit: int = 20, path: str | None = None) -> list[dict]:
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT id, created_at, kind, params, result FROM backtest_runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [
        {
            "id": r["id"],
            "created_at": r["created_at"],
            "kind": r["kind"],
            "params": json.loads(r["params"]),
            "result": json.loads(r["result"]),
        }
        for r in rows
    ]


def database_ok(path: str | None = None) -> bool:
    try:
        with connect(path) as conn:
            conn.execute("SELECT 1").fetchone()
        return True
    except sqlite3.Error:
        return False
