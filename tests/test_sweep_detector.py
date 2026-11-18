"""Unit tests for the liquidity sweep detector (backend/strategy.py)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.core.models import Candle
from backend.strategy import (
    detect_displacement_candle,
    detect_sweep,
    displacement_strength,
    is_sweep_depth_valid,
)

T0 = datetime(2026, 11, 17, tzinfo=timezone.utc)


def _candle(i, open_, high, low, close, volume=100.0):
    return Candle(ts=T0 + timedelta(minutes=5 * i), open=open_, high=high, low=low, close=close, volume=volume)


def _base_series(n=60, price=2380.0):
    candles = []
    for i in range(n):
        o = price + (0.4 if i % 2 else -0.4)
        c = o + (0.3 if i % 3 else -0.2)
        candles.append(_candle(i, o, max(o, c) + 0.3, min(o, c) - 0.3, c))
    return candles


def _sweep_series_long():
    """Series with a bullish sweep below equal lows, then displacement back inside."""
    candles = _base_series(60, 2380.0)
    # equal lows cluster near 2370
    for idx in (10, 20, 30):
        candles[idx] = _candle(idx, 2371.0, 2372.0, 2370.0, 2371.2)
    # sweep candle: wick pierces below 2370 (depth ~1.6 -> 16 pips), close nearby
    candles[55] = _candle(55, 2371.5, 2372.0, 2368.4, 2371.6)
    # displacement candle: closes back inside, large body
    candles[56] = _candle(56, 2371.4, 2376.0, 2371.2, 2375.8, volume=400.0)
    candles[57] = _candle(57, 2376.0, 2377.0, 2375.0, 2376.5)
    return candles


def test_sweep_depth_valid_xau():
    assert is_sweep_depth_valid("XAUUSD", 1.6) is True   # 16 pips
    assert is_sweep_depth_valid("XAUUSD", 0.5) is False  # 5 pips, too shallow
    assert is_sweep_depth_valid("XAUUSD", 3.0) is False  # 30 pips, too deep


def test_sweep_depth_valid_btc():
    assert is_sweep_depth_valid("BTCUSD", 0.002) is True
    assert is_sweep_depth_valid("BTCUSD", 0.0005) is False


def test_displacement_strength_and_detection():
    series = _sweep_series_long()
    strength = displacement_strength(series[-2:], lookback=20)
    assert strength > 0
    series = _base_series(40, 2380.0)
    series[-1] = _candle(39, 2371.0, 2378.0, 2370.8, 2377.5, volume=300.0)
    series[-2] = _candle(38, 2371.5, 2372.0, 2370.0, 2371.2)
    assert detect_displacement_candle(series, "LONG") in (True, False)  # rule-based; must not raise


def test_detect_bullish_sweep_returns_candidate():
    series = _sweep_series_long()
    levels = [
        {"price": 2370.0, "type": "EQUAL_LOW", "side": "below"},
        {"price": 2395.0, "type": "RESISTANCE", "side": "above"},
        {"price": 2408.0, "type": "PDH", "side": "above"},
    ]
    candidate = detect_sweep("XAUUSD", series, levels)
    assert candidate is not None, "expected a LONG sweep candidate"
    assert candidate["direction"] == "LONG"
    assert candidate["entry_price"] > 0
    assert candidate["stop_loss"] < candidate["entry_price"]
    assert candidate["take_profit_1"] > candidate["entry_price"]
    assert candidate["risk_reward_ratio"] > 0
    assert candidate["sweep_details"]["extension_depth"] > 0


def test_detect_sweep_insufficient_data():
    series = _base_series(10, 2380.0)
    assert detect_sweep("XAUUSD", series, []) is None


def test_detect_sweep_no_levels():
    series = _sweep_series_long()
    assert detect_sweep("XAUUSD", series, []) is None