"""Deterministic synthetic market data for DEMO MODE.

Generates realistic XAUUSD / BTCUSD OHLCV with embedded liquidity sweeps so
the strategy has something to detect without a broker connection.
"""
from __future__ import annotations

import math
import random
import time
from typing import Iterable

from .models import Candle
from .strategy import LiquidityLevel, equal_highs, equal_lows, swing_levels

import numpy as np


def _seed_for(instrument: str) -> int:
    return sum(ord(ch) for ch in instrument) * 7919


def _session_volatility(hour_utc: int) -> float:
    """Volatility multiplier by session (Asian quiet, London/NY active)."""
    if 0 <= hour_utc < 6:
        return 0.6
    if 6 <= hour_utc < 12:
        return 1.4
    if 12 <= hour_utc < 21:
        return 1.8
    return 0.9


def generate_candles(
    instrument: str,
    count: int,
    timeframe_minutes: int = 5,
    start_price: float | None = None,
) -> list[Candle]:
    """Generate synthetic OHLCV with drift, mean reversion, and sweeps."""
    rng = random.Random(_seed_for(instrument))
    if start_price is None:
        start_price = 2650.0 if instrument.upper().startswith("XAU") else 97000.0

    pip = 0.10 if instrument.upper().startswith("XAU") else 0.01
    candles: list[Candle] = []
    price = start_price
    now = time.time() - count * timeframe_minutes * 60

    for i in range(count):
        hour_utc = time.gmtime(now + i * timeframe_minutes * 60).tm_hour
        vol = _session_volatility(hour_utc)
        base = 1.2 * pip * vol * (1 + 0.5 * math.sin(i / 12))
        drift = 0.15 * pip * math.sin(i / 25)
        open_p = price
        # random walk within bar
        steps = 6
        path = [open_p]
        for _ in range(steps):
            path.append(path[-1] + rng.gauss(drift, base))
        close = path[-1]
        high = max(path)
        low = min(path)
        volume = float(rng.randint(50, 400)) * (1.0 + vol * 0.5)
        candles.append(
            Candle(
                time=now + i * timeframe_minutes * 60,
                open=round(open_p, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(close, 2),
                volume=round(volume, 2),
            )
        )
        price = close

    # Inject a liquidity sweep near the end so the Hunter always finds one.
    _inject_sweep(candles, instrument, rng)
    return candles


def _inject_sweep(candles: list[Candle], instrument: str, rng: random.Random) -> None:
    """Force a clean sweep + displacement pattern in the last few candles."""
    if len(candles) < 6:
        return
    pip = 0.10 if instrument.upper().startswith("XAU") else 0.01
    level = candles[-5].high
    # candle -3: wick sweeps above level, closes below
    c = candles[-3]
    c.high = round(level + 18 * pip, 2)
    c.close = round(level - 2 * pip, 2)
    c.open = round(level - 1 * pip, 2)
    c.low = round(level - 3 * pip, 2)
    # candle -2: displacement candle, big body, closes back inside
    d = candles[-2]
    d.open = round(level - 2 * pip, 2)
    d.close = round(level + 8 * pip, 2)
    d.high = round(level + 10 * pip, 2)
    d.low = round(level - 2.5 * pip, 2)
    d.volume = round(d.volume * 2.5, 2)
    # candle -1: continuation
    e = candles[-1]
    e.open = round(d.close, 2)
    e.close = round(d.close + 6 * pip, 2)
    e.high = round(d.close + 9 * pip, 2)
    e.low = round(d.close - 1 * pip, 2)


def get_levels(candles: list[Candle]) -> list[LiquidityLevel]:
    """Compute PDH/PDL, swing, and equal-high/low levels from candles."""
    highs = np.array([c.high for c in candles], dtype=float)
    lows = np.array([c.low for c in candles], dtype=float)
    levels: list[LiquidityLevel] = []
    levels.append(LiquidityLevel("PDH", float(highs.max())))
    levels.append(LiquidityLevel("PDL", float(lows.min())))
    for s in swing_levels(highs, lows):
        levels.append(s)
    for p in equal_highs(highs):
        levels.append(LiquidityLevel("EQUAL_HIGHS", float(p)))
    for p in equal_lows(lows):
        levels.append(LiquidityLevel("EQUAL_LOWS", float(p)))
    return levels


def current_price(candles: list[Candle]) -> float:
    return candles[-1].close if candles else 0.0


def spread_for(instrument: str) -> float:
    """Demo spread in points."""
    return 18.0 if instrument.upper().startswith("XAU") else 25.0


def account_info() -> dict:
    return {
        "balance": 10000.0,
        "equity": 10000.0,
        "margin_used": 0.0,
        "free_margin": 10000.0,
        "mode": "paper",
    }
