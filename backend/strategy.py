"""Liquidity Sweep strategy – deterministic detection engine.

A liquidity sweep: price pierces a known liquidity level (PDH/PDL, Asian
session high/low, 4H swing high/low, equal highs/lows), then a displacement
candle closes back inside the range.

Depth: XAUUSD 10-25 pips beyond the level; BTCUSD 0.15%-0.4%.
Displacement: closes back inside within 3 candles, body >= 1.2x avg body.
Entry: on the confirmation close, or pullback to 50% of the sweep wick.
SL: beyond the wick extreme + buffer (5 pips XAUUSD, 0.1% BTC).
TP1 at 1:2 RR; TP2 at the next liquidity pool (1:3+).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .models import Candle, SweepCandidate

# Smallest price unit we call a "pip" per instrument (demo convention).
PIP = {"XAUUSD": 0.10, "BTCUSD": 0.01}
SL_BUFFER_PIPS_XAU = 5.0          # 5 pips beyond wick extreme
SL_BUFFER_PCT_BTC = 0.001         # 0.1% beyond wick extreme
DISPLACEMENT_BODY_MULT = 1.2      # body >= 1.2x average body
MAX_CANDLES_TO_CLOSE = 3          # must close back inside within 3 candles


def pip_size(instrument: str) -> float:
    return PIP.get(instrument.upper(), 0.01)


def depth_bounds(instrument: str) -> tuple[float, float]:
    """Return (min_depth, max_depth) in price units."""
    if instrument.upper().startswith("XAU"):
        p = pip_size(instrument)
        return (10 * p, 25 * p)
    return (0.0015, 0.004)  # BTCUSD: fraction of level price


def sl_buffer(instrument: str, level_price: float) -> float:
    """SL buffer beyond the wick extreme, in price units."""
    if instrument.upper().startswith("XAU"):
        return SL_BUFFER_PIPS_XAU * pip_size(instrument)
    return SL_BUFFER_PCT_BTC * level_price


@dataclass
class LiquidityLevel:
    level_type: str  # PDH / PDL / ASIAN_HIGH / ASIAN_LOW / SWING_HIGH / SWING_LOW / EQUAL_HIGHS / EQUAL_LOWS
    price: float


def avg_body(candles: list[Candle], period: int = 20) -> float:
    bodies = [abs(c.close - c.open) for c in candles[-period:]]
    return float(np.mean(bodies)) if bodies else 0.0


def atr(candles: list[Candle], period: int = 14) -> float:
    if len(candles) <= period:
        return 0.0
    trs = []
    for i in range(period, len(candles)):
        hi, lo = candles[i].high, candles[i].low
        prev = candles[i - 1]
        trs.append(max(hi - lo, abs(hi - prev.close), abs(lo - prev.close)))
    return float(np.mean(trs)) if trs else 0.0


def swing_levels(highs: np.ndarray, lows: np.ndarray, lookback: int = 3) -> list[LiquidityLevel]:
    """Extract swing high / swing low liquidity levels."""
    levels: list[LiquidityLevel] = []
    n = len(highs)
    for i in range(lookback, n - lookback):
        if highs[i] == max(highs[i - lookback:i + lookback + 1]) and highs[i] > highs[i - 1]:
            if not any(abs(highs[i] - l.price) < 1e-9 for l in levels):
                levels.append(LiquidityLevel("SWING_HIGH", float(highs[i])))
        if lows[i] == min(lows[i - lookback:i + lookback + 1]) and lows[i] < lows[i - 1]:
            if not any(abs(lows[i] - l.price) < 1e-9 for l in levels):
                levels.append(LiquidityLevel("SWING_LOW", float(lows[i])))
    return levels


def equal_highs(highs: np.ndarray, tol: float = 1e-6) -> list[float]:
    out = []
    for i in range(len(highs) - 1):
        if abs(highs[i] - highs[i + 1]) <= tol and not any(abs(highs[i] - x) < tol for x in out):
            out.append(float(highs[i]))
    return out


def equal_lows(lows: np.ndarray, tol: float = 1e-6) -> list[float]:
    out = []
    for i in range(len(lows) - 1):
        if abs(lows[i] - lows[i + 1]) <= tol and not any(abs(lows[i] - x) < tol for x in out):
            out.append(float(lows[i]))
    return out


def _is_resistance(lt: str) -> bool:
    return lt in {"PDH", "ASIAN_HIGH", "SWING_HIGH", "EQUAL_HIGHS"}


def detect_sweep(
    candles: list[Candle],
    instrument: str,
    extra_levels: Iterable[LiquidityLevel] | None = None,
) -> list[SweepCandidate]:
    """Scan the most recent candles for liquidity sweeps. Returns candidates."""
    if len(candles) < 10:
        return []

    highs = np.array([c.high for c in candles], dtype=float)
    lows = np.array([c.low for c in candles], dtype=float)

    levels: list[LiquidityLevel] = list(extra_levels or [])
    if not levels:
        levels += swing_levels(highs, lows)
        levels.append(LiquidityLevel("PDH", float(highs.max())))
        levels.append(LiquidityLevel("PDL", float(lows.min())))
        for p in equal_highs(highs):
            levels.append(LiquidityLevel("EQUAL_HIGHS", float(p)))
        for p in equal_lows(lows):
            levels.append(LiquidityLevel("EQUAL_LOWS", float(p)))

    body_avg = avg_body(candles)
    candidates: list[SweepCandidate] = []
    n = len(candles)

    for level in levels:
        resistance = _is_resistance(level.level_type)
        # Search the last MAX_CANDLES_TO_CLOSE+1 candles for the sweep wick.
        for i in range(max(0, n - MAX_CANDLES_TO_CLOSE - 2), n - 1):
            wick = candles[i]
            if resistance:
                swept = wick.high > level.price
                if not swept:
                    continue
                depth = wick.high - level.price
                wick_extreme = wick.high
            else:
                swept = wick.low < level.price
                if not swept:
                    continue
                depth = level.price - wick.low
                wick_extreme = wick.low

            # Depth gate: must pierce by at least the minimum (per instrument).
            min_d, max_d = depth_bounds(instrument)
            if instrument.upper().startswith("BTC"):
                min_d = min_d * level.price
                max_d = max_d * level.price
            if depth < min_d:
                continue

            # Find displacement candle that closes back inside within 3 candles.
            disp_idx = None
            for j in range(i + 1, min(i + 1 + MAX_CANDLES_TO_CLOSE, n)):
                c = candles[j]
                if resistance and c.close < level.price:
                    disp_idx = j
                    break
                if (not resistance) and c.close > level.price:
                    disp_idx = j
                    break
            if disp_idx is None:
                continue

            disp = candles[disp_idx]
            body = abs(disp.close - disp.open)
            if body < DISPLACEMENT_BODY_MULT * body_avg:
                continue  # displacement too weak

            direction = "short" if resistance else "long"
            entry = disp.close
            buf = sl_buffer(instrument, level.price)
            if direction == "short":
                stop_loss = wick_extreme + buf
                tp1 = entry - 2 * abs(entry - stop_loss)
                tp2 = entry - 3 * abs(entry - stop_loss)
            else:
                stop_loss = wick_extreme - buf
                tp1 = entry + 2 * abs(entry - stop_loss)
                tp2 = entry + 3 * abs(entry - stop_loss)

            risk = abs(entry - stop_loss)
            rr1 = abs(tp1 - entry) / risk if risk > 0 else 0.0
            rr2 = abs(tp2 - entry) / risk if risk > 0 else 0.0
            quality = min(1.0, depth / (max_d if not resistance else max_d) )

            candidates.append(
                SweepCandidate(
                    instrument=instrument,
                    direction=direction,
                    level_type=level.level_type,
                    level_price=level.price,
                    wick_extreme=wick_extreme,
                    extension_depth=depth,
                    candles_to_close=disp_idx - i,
                    displacement_quality=round(quality, 3),
                    entry_price=entry,
                    stop_loss=stop_loss,
                    take_profit_1=tp1,
                    take_profit_2=tp2,
                    risk_reward_ratio=round(max(rr1, rr2), 2),
                    session="LONDON",
                )
            )
            # one candidate per level
            break

    return candidates


def compute_indicators(candles: list[Candle]) -> dict:
    if len(candles) < 2:
        return {"sma20": 0.0, "ema5": 0.0, "atr14": 0.0, "rsi14": 50.0}
    closes = np.array([c.close for c in candles], dtype=float)
    sma20 = float(np.mean(closes[-20:])) if len(closes) >= 20 else float(np.mean(closes))
    ema5 = float(np.mean(closes[-5:]))
    a14 = atr(candles, 14)
    deltas = np.diff(closes[-15:])
    gain = float(np.mean([d for d in deltas if d > 0])) if len(deltas) else 0.0
    loss = float(np.mean([abs(d) for d in deltas if d < 0])) if len(deltas) else 0.0
    rs = gain / loss if loss > 0 else 100.0
    rsi = float(100 - (100 / (1 + rs)))
    return {"sma20": sma20, "ema5": ema5, "atr14": a14, "rsi14": round(rsi, 2)}
