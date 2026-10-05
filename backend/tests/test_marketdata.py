from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from marketdata import store
from marketdata.migrate_to_postgres import migrate
from marketdata.provider import fetch_ohlcv
from marketdata.quality import quality_report


def _frame(n=48, start="2024-01-01"):
    idx = pd.date_range(start, periods=n, freq="1h", tz="UTC", name="ts")
    base = pd.Series(range(n), index=idx, dtype=float) + 100
    return pd.DataFrame({"open": base, "high": base + 2, "low": base - 2, "close": base + 1, "volume": 10.0}, index=idx)


class FakeExchange:
    def __init__(self, frame):
        self.rows = [
            [int(ts.timestamp() * 1000), r.open, r.high, r.low, r.close, r.volume] for ts, r in frame.iterrows()
        ]
        self.calls = 0

    def fetch_ohlcv(self, symbol, timeframe, since=None, limit=1000):
        self.calls += 1
        return [r for r in self.rows if r[0] >= since][:limit]


def test_store_roundtrip_and_upsert(tmp_path):
    path = str(tmp_path / "t.db")
    store.init_db(path)
    frame = _frame()
    assert store.upsert_candles(frame, "BTC/USDT", "1h", path) == 48
    store.upsert_candles(frame, "BTC/USDT", "1h", path)
    loaded = store.load_candles("BTC/USDT", "1h", path)
    assert len(loaded) == 48
    assert loaded["close"].iloc[0] == pytest.approx(101.0)


def test_runs_are_persisted_newest_first(tmp_path):
    path = str(tmp_path / "t.db")
    store.init_db(path)
    store.save_run("backtest", {"a": 1}, {"r": 1}, path)
    store.save_run("validation", {"a": 2}, {"r": 2}, path)
    runs = store.list_runs(path=path)
    assert [r["kind"] for r in runs] == ["validation", "backtest"]
    assert runs[0]["params"] == {"a": 2}


def test_quality_report_flags_gaps_and_bad_ohlc():
    assert quality_report(_frame(), "1h")["status"] == "ok"
    gappy = _frame().drop(_frame().index[10:13])
    assert quality_report(gappy, "1h")["missing_bars"] == 3
    broken = _frame()
    broken.iloc[5, broken.columns.get_loc("high")] = 0.5
    assert quality_report(broken, "1h")["invalid_ohlc"] >= 1
    assert quality_report(_frame().iloc[0:0], "1h")["status"] == "empty"


def test_fetch_paginates_and_drops_forming_bar():
    frame = _frame(n=120)
    ex = FakeExchange(frame)
    start = frame.index[0].to_pydatetime()
    end = start + timedelta(hours=100, minutes=30)
    out = fetch_ohlcv("BTC/USDT", "1h", start, end, exchange=ex, limit=40)
    assert ex.calls >= 3
    assert out.index.is_unique and out.index.is_monotonic_increasing
    assert out.index[-1] + pd.Timedelta("1h") <= pd.Timestamp(end)
    assert len(out) == 100


def test_fetch_handles_empty_exchange():
    empty = FakeExchange(_frame().iloc[0:0])
    out = fetch_ohlcv(
        "BTC/USDT", "1h", datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 1, 2, tzinfo=UTC), exchange=empty
    )
    assert out.empty


def test_postgres_migration_dry_run_counts_rows(tmp_path):
    path = str(tmp_path / "t.db")
    store.init_db(path)
    store.upsert_candles(_frame(10), "ETH/USDT", "1h", path)
    store.save_run("backtest", {}, {}, path)
    report = migrate(path, "", dry_run=True)
    assert report["candles"]["source"] == 10
    assert report["backtest_runs"]["source"] == 1
