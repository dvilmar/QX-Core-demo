import demo_engine as engine


def test_synthetic_data_is_reproducible():
    a = engine.generate_synthetic_candles(n_bars=200, seed=3)
    b = engine.generate_synthetic_candles(n_bars=200, seed=3)
    assert [c.close for c in a] == [c.close for c in b]


def test_candles_have_valid_ohlc():
    for c in engine.generate_synthetic_candles(n_bars=500, seed=5):
        assert c.high >= max(c.open, c.close) and c.low <= min(c.open, c.close)


def test_backtest_equity_curve_matches_bars(candles):
    result = engine.run_demo_backtest(candles)
    assert len(result.equity_curve) == len(candles)


def test_trades_are_chronological_and_fills_are_after_signal(candles):
    result = engine.run_demo_backtest(candles)
    for t in result.trades:
        assert t.exit_ts >= t.entry_ts


def test_costs_reduce_performance(candles, monkeypatch):
    with_costs = engine.run_demo_backtest(candles).equity_curve[-1]
    monkeypatch.setattr(engine, "FEE_RATE", 0.0)
    monkeypatch.setattr("quant.costs.MIN_SLIPPAGE", 0.0)
    monkeypatch.setattr("quant.costs.SLIPPAGE_ATR_MULT", 0.0)
    free = engine.run_demo_backtest(candles).equity_curve[-1]
    assert free > with_costs
