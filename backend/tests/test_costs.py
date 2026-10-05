import math

import pytest

from quant import costs


def test_slippage_floor_applies_on_quiet_bars():
    assert costs.slippage_rate(0.0, 100.0) == costs.MIN_SLIPPAGE


def test_slippage_scales_with_atr():
    assert costs.slippage_rate(5.0, 100.0) == pytest.approx(costs.SLIPPAGE_ATR_MULT * 0.05)


@pytest.mark.parametrize("atr,close", [(None, 100.0), (math.nan, 100.0), (-1.0, 100.0), (1.0, 0.0)])
def test_invalid_inputs_fall_back_to_floor(atr, close):
    assert costs.slippage_rate(atr, close) == costs.MIN_SLIPPAGE


def test_fills_are_adverse_on_both_sides():
    assert costs.buy_fill(100.0, 1.0) > 100.0
    assert costs.sell_fill(100.0, 1.0) < 100.0


def test_round_trip_always_loses_money_at_flat_price():
    assert costs.sell_fill(costs.buy_fill(100.0, 1.0), 1.0) < 100.0
