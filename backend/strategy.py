"""Liquidity Sweep strategy logic for QUANT PILOT.

Strategy: Price pierces a known liquidity level (PDH/PDL, Asian/London/New York
session high/low, 4H swing high/low, equal highs/lows), then a displacement
candle closes back inside the range.

Sweep depth: XAUUSD 10-25 pips beyond the level; BTCUSD 0.15%-0.4%.
Displacement: closes back inside within 3 candles, body at least 1.2x the
average body (volume spike is a bonus).
"""

from __future__ import annotations

import numpy as np

from .core.indicators import atr
from .core.models import Candle

# Spec constants
XAUUSD_PIPS_PER_POINT = 0.1          # 1 pip = $0.1 (0.10 USD)
XAUUSD_SPREAD_LIMIT = 35             # points
BTC_SPREAD_LIMIT = 500               # configurable, points (of 0.01 centimetre)


def is_sweep_depth_valid(instrument: str, sweep_depth: float, reference_price: float | None = None) -> bool:
    """Return True if the sweep depth is within the valid range for the instrument.

    For BTCUSD the spec defines the depth as a percentage (0.15%–0.4%) of the
    swept level. Pass ``reference_price`` to convert an absolute depth, or pass
    an already-relative fraction as ``sweep_depth``.
    """
    if instrument.upper().startswith("XAU"):
        pips = sweep_depth / XAUUSD_PIPS_PER_POINT
        return 10.0 <= pips <= 25.0
    elif instrument.upper().startswith("BTC"):
        if reference_price and reference_price > 0:
            pct = sweep_depth / reference_price
        else:
            pct = sweep_depth
        return 0.0015 <= pct <= 0.004
    return False


def displacement_strength(candles: list[Candle], lookback: int = 20) -> float:
    """Return the displacement strength as a ratio of body to average body."""
    if len(candles) < 2:
        return 1.0
    closes = [c.close for c in candles]
    avg_body = float(np.mean([abs(c.close - c.open) for c in candles[-lookback:]]))
    if avg_body <= 0:
        avg_body = 1e-9
    cur = abs(candles[-1].close - candles[-1].open)
    return cur / avg_body


def detect_displacement_candle(candles: list[Candle], direction: str) -> bool:
    """Return True if the last candle is a valid displacement candle in the given direction."""
    if not candles:
        return False
    last = candles[-1]
    body = abs(last.close - last.open)
    avg_body = float(np.mean([abs(c.close - c.open) for c in candles[-21:-1]])) if len(candles) > 1 else body
    if avg_body <= 0:
        avg_body = 1e-9
    ratio = body / avg_body
    if ratio < 1.2:
        return False
    if direction == "LONG":  # bullish reversal after sweep below
        return last.close >= last.open and last.close > candles[-2].close
    return last.close <= last.open and last.close < candles[-2].close


def detect_sweep(
    instrument: str,
    candles: list[Candle],
    liquidity_levels: list[dict],
) -> dict | None:
    """Detect a liquidity sweep + displacement pattern.

    Returns a candidate setup dict or None if no sweep is detected.
    """
    if len(candles) < 50:
        return None

    ohlcv = [c.close for c in candles]
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    opens = [c.open for c in candles]

    atr_vals = atr(highs, lows, ohlcv, 14)
    atr_val = atr_vals[-1] if not np.isnan(atr_vals[-1]) else abs(highs[-1] - lows[-1]) or 1e-9

    # average body over recent window
    bodies = [abs(c.close - c.open) for c in candles]
    avg_body = float(np.mean(bodies[-21:-1])) or 1e-9

    # Candidate: swept a liquidity level and closed back inside
    for level in liquidity_levels:
        level_price = level["price"]
        level_type = level.get("type", "UNKNOWN")
        # Find a candle whose wick pierces the level
        for i in range(max(0, len(candles) - 5), len(candles)):
            c = candles[i]
            # Bullish sweep: low pierced below level (sell-side liquidity) then close back above
            if level.get("side", "below") == "below" and c.low < level_price:
                if instrument.upper().startswith("XAU"):
                    depth = level_price - c.low
                    valid_depth = 10.0 <= (depth / XAUUSD_PIPS_PER_POINT) <= 25.0
                else:
                    depth = level_price - c.low
                    rel_depth = depth / level_price if level_price else 0.0
                    valid_depth = 0.0015 <= rel_depth <= 0.004
                if not valid_depth:
                    continue
                # displacement check: close back inside within 3 candles
                for j in range(i, min(i + 3, len(candles))):
                    disp = candles[j]
                    body = abs(disp.close - disp.open)
                    if disp.close > level_price and body >= 1.2 * avg_body:
                        entry = disp.close
                        sl = min(lows[i:j + 1]) - (5 * XAUUSD_PIPS_PER_POINT if instrument.upper().startswith("XAU") else level_price * 0.001)
                        # TP1: 1:2 RR using opposite range boundary
                        opposite = [l for l in liquidity_levels if l.get("side") == "above"]
                        tp1 = opposite[0]["price"] if opposite else entry + 2 * abs(entry - sl)
                        tp2 = opposite[1]["price"] if len(opposite) > 1 else entry + 3 * abs(entry - sl)
                        rr = abs(tp1 - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0
                        return {
                            "instrument": instrument,
                            "direction": "LONG",
                            "entry_price": entry,
                            "stop_loss": sl,
                            "take_profit_1": tp1,
                            "take_profit_2": tp2,
                            "risk_reward_ratio": round(rr, 2),
                            "htf_level_targeted": f"{level_type} @ {level_price:.2f}",
                            "sweep_details": {
                                "extension_depth": round(depth, 4),
                                "sweep_candle_index": i,
                                "displacement_quality": round(body / avg_body, 2),
                            },
                            "liquidity_sweep": True,
                            "level_price": level_price,
                        }
            # Bearish sweep: high pierced above level (buy-side liquidity) then close back below
            if level.get("side", "above") == "above" and c.high > level_price:
                if instrument.upper().startswith("XAU"):
                    depth = c.high - level_price
                    valid_depth = 10.0 <= (depth / XAUUSD_PIPS_PER_POINT) <= 25.0
                else:
                    depth = c.high - level_price
                    rel_depth = depth / level_price if level_price else 0.0
                    valid_depth = 0.0015 <= rel_depth <= 0.004
                if not valid_depth:
                    continue
                for j in range(i, min(i + 3, len(candles))):
                    disp = candles[j]
                    body = abs(disp.close - disp.open)
                    if disp.close < level_price and body >= 1.2 * avg_body:
                        entry = disp.close
                        sl = max(highs[i:j + 1]) + (5 * XAUUSD_PIPS_PER_POINT if instrument.upper().startswith("XAU") else level_price * 0.001)
                        opposite = [l for l in liquidity_levels if l.get("side") == "below"]
                        tp1 = opposite[0]["price"] if opposite else entry - 2 * abs(entry - sl)
                        tp2 = opposite[1]["price"] if len(opposite) > 1 else entry - 3 * abs(entry - sl)
                        rr = abs(entry - tp1) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0
                        return {
                            "instrument": instrument,
                            "direction": "SHORT",
                            "entry_price": entry,
                            "stop_loss": sl,
                            "take_profit_1": tp1,
                            "take_profit_2": tp2,
                            "risk_reward_ratio": round(rr, 2),
                            "htf_level_targeted": f"{level_type} @ {level_price:.2f}",
                            "sweep_details": {
                                "extension_depth": round(depth, 4),
                                "sweep_candle_index": i,
                                "displacement_quality": round(body / avg_body, 2),
                            },
                            "liquidity_sweep": True,
                            "level_price": level_price,
                        }
    return None


__all__ = [
    "detect_sweep",
    "detect_displacement_candle",
    "displacement_strength",
    "is_sweep_depth_valid",
    "XAUUSD_PIPS_PER_POINT",
    "XAUUSD_SPREAD_LIMIT",
    "BTC_SPREAD_LIMIT",
]