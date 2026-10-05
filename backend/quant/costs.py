from __future__ import annotations

import math

FEE_RATE = 0.001
MIN_SLIPPAGE = 0.0002
SLIPPAGE_ATR_MULT = 0.1


def slippage_rate(atr: float | None, close: float) -> float:
    """max(MIN_SLIPPAGE, SLIPPAGE_ATR_MULT * ATR / close)."""
    if atr is None or math.isnan(atr) or atr < 0 or close <= 0:
        return MIN_SLIPPAGE
    return max(MIN_SLIPPAGE, SLIPPAGE_ATR_MULT * atr / close)


def buy_fill(price: float, atr: float | None, fee: float = FEE_RATE) -> float:
    return price * (1.0 + fee + slippage_rate(atr, price))


def sell_fill(price: float, atr: float | None, fee: float = FEE_RATE) -> float:
    return price * (1.0 - fee - slippage_rate(atr, price))
