import pytest

import demo_engine as engine


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("QX_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("QX_DB_PATH", raising=False)
    monkeypatch.delenv("DASHBOARD_API_KEY", raising=False)


@pytest.fixture(scope="session")
def candles():
    return engine.generate_synthetic_candles(n_bars=24 * 300, seed=11)
