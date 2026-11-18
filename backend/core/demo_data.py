"""Demo Mode data provider — synthetic, replayable XAUUSD/BTCUSD candles.

No broker or API key is required. Generates realistic candles with built-in
liquidity sweeps (equal highs/lows above/below which stops cluster, then a
stop-hunt reversal), Asian/London/New York session tagging, and spread
simulation.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import numpy as np

from .models import Candle, MarketTick

SYMBOLS = {
    "XAUUSD": {"base": 2380.0, "vol": 4.5, "pip": 0.1},
    "BTCUSD": {"base": 67000.0, "vol": 380.0, "pip": 10.0},
}


def session_for(ts: datetime) -> str:
    """Tag a UTC timestamp with the dominant session."""
    hour = ts.hour
    if 0 <= hour < 8:
        return "ASIAN"
    if 7 <= hour < 13:
        return "LONDON"
    if 13 <= hour < 21:
        return "NEW_YORK"
    return "ASIAN"


def generate_synthetic_candles(
    symbol: str,
    count: int = 300,
    interval_minutes: int = 5,
    seed: int = 42,
    include_sweep: bool = True,
) -> list[Candle]:
    """Generate synthetic OHLCV candles with a built-in liquidity sweep."""
    cfg = SYMBOLS.get(symbol.upper(), SYMBOLS["XAUUSD"])
    rng = np.random.default_rng(seed)

    start = datetime.now(timezone.utc) - timedelta(minutes=interval_minutes * count)
    start = start.replace(second=0, microsecond=0)

    price = cfg["base"]
    candles: list[Candle] = []
    anchor = cfg["base"]

    for i in range(count):
        ts = start + timedelta(minutes=interval_minutes * i)
        wave = math.sin(i / 17.0) * cfg["vol"] * 1.6 + math.sin(i / 5.3) * cfg["vol"] * 0.6
        noise = float(rng.normal(0, cfg["vol"] * 0.35))
        target = anchor + wave + noise

        open_ = price
        close = target
        high_ = max(open_, close) + abs(float(rng.normal(0, cfg["vol"] * 0.35)))
        low_ = min(open_, close) - abs(float(rng.normal(0, cfg["vol"] * 0.35)))
        volume = float(rng.integers(80, 320))
        candles.append(_mk(ts, open_, high_, low_, close, volume))
        price = close

    # ── Deterministic liquidity sweep appended to the tail (Detected by the Hunter) ──
    if include_sweep and len(candles) >= 40:
        if symbol.upper().startswith("XAU"):
            level = anchor - 8.0                     # equal lows pool (16 pips of sweep below)
            sweep_low = level - 1.7                  # 17-pip pierce
            # plant several equal lows inside the history so the level is "known liquidity"
            for back in (12, 24, 33):
                c = candles[-back]
                candles[-back] = _mk(c.ts, c.open, c.open + 0.6, level + 0.02, c.open + 0.3, c.volume)
            candles[-2] = _mk(start + timedelta(minutes=interval_minutes * (count - 2)),
                              level + 0.9, level + 1.3, sweep_low, level + 0.55, float(rng.integers(220, 320)))
            candles[-1] = _mk(start + timedelta(minutes=interval_minutes * (count - 1)),
                              level + 0.55, level + 6.6, level + 0.4, level + 6.1,
                              float(rng.integers(600, 800)))  # displacement candle, big body
        else:  # BTCUSD — depth in pct (0.25% below the pool)
            level = anchor - 180.0
            sweep_low = level * (1 - 0.0025)
            for back in (12, 24, 33):
                c = candles[-back]
                candles[-back] = _mk(c.ts, c.open, c.open + 8.0, level + 0.4, c.open + 4.0, c.volume)
            candles[-2] = _mk(start + timedelta(minutes=interval_minutes * (count - 2)),
                              level + 12.0, level + 18.0, sweep_low, level + 9.0, float(rng.integers(220, 320)))
            candles[-1] = _mk(start + timedelta(minutes=interval_minutes * (count - 1)),
                              level + 9.0, level + 120.0, level + 7.0, level + 115.0,
                              float(rng.integers(600, 800)))

    return candles


def _mk(ts: datetime, o: float, h: float, l: float, c: float, v: float) -> Candle:
    return Candle(ts=ts, open=round(o, 5), high=round(h, 5), low=round(l, 5), close=round(c, 5), volume=v)


def replay_candles(symbol: str, limit: int = 300) -> list[Candle]:
    """Replay the deterministic built-in sweep scenario for the given symbol."""
    return generate_synthetic_candles(symbol, count=limit, seed=7 if symbol.upper().startswith("XAU") else 13)


def current_tick(symbol: str) -> MarketTick:
    """Synthetic latest tick with a deterministic-ish spread."""
    cfg = SYMBOLS.get(symbol.upper(), SYMBOLS["XAUUSD"])
    seed = hash((symbol, datetime.now(timezone.utc).strftime("%H:%M")))
    rng = np.random.default_rng(abs(seed) % (2**32))
    mid = cfg["base"] + math.sin(datetime.now(timezone.utc).timestamp() / 120.0) * cfg["vol"]
    spread_pts = int(rng.integers(8, 22)) if symbol.upper().startswith("XAU") else int(rng.integers(120, 320))
    half = spread_pts * cfg["pip"] / 2 / 10
    return MarketTick(symbol=symbol, bid=round(mid - half, 5), ask=round(mid + half, 5), spread_points=spread_pts, ts=datetime.now(timezone.utc))


def build_liquidity_levels(candles: list[Candle], symbol: str = "XAUUSD") -> list[dict]:
    """Build liquidity map from candles: equal highs/lows, swing high/low, session ranges.

    Returns list of {"price": float, "type": str, "side": "above"|"below"}.
    """
    if not candles:
        return []
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    closes = [c.close for c in candles]
    last = closes[-1]

    levels: list[dict] = []

    # swing highs/lows over the whole window (fractal lookback 2)
    for i in range(2, len(highs) - 2):
        if highs[i] == max(highs[i - 2 : i + 3]):
            levels.append({"price": round(highs[i], 5), "type": "SWING_HIGH", "side": "above"})
        if lows[i] == min(lows[i - 2 : i + 3]):
            levels.append({"price": round(lows[i], 5), "type": "SWING_LOW", "side": "below"})

    # equal highs / equal lows (cluster of >=2 touches within tolerance)
    tol = 0.05 if symbol.upper().startswith("XAU") else 25.0
    for level in equal_levels(highs, tol, "above", "EQUAL_HIGH"):
        levels.append(level)
    for level in equal_levels(lows, tol, "below", "EQUAL_LOW"):
        levels.append(level)

    # previous day high/low (use last ~78 5M candles ~ 1 day)
    window = candles[-78:] if len(candles) >= 78 else candles
    pdh = max(c.high for c in window)
    pdl = min(c.low for c in window)
    levels.append({"price": round(pdh, 5), "type": "PDH", "side": "above"})
    levels.append({"price": round(pdl, 5), "type": "PDL", "side": "below"})

    # Asian session range (first 8h worth of 5M candles of the window)
    asian = window[:96] if len(window) >= 96 else window
    levels.append({"price": round(max(c.high for c in asian), 5), "type": "ASIAN_HIGH", "side": "above"})
    levels.append({"price": round(min(c.low for c in asian), 5), "type": "ASIAN_LOW", "side": "below"})

    # de-duplicate near-identical prices keeping first occurrence
    seen: set[int] = set()
    deduped: list[dict] = []
    for lvl in levels:
        key = round(lvl["price"], 1)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(lvl)
    return deduped


def equal_levels(values: list[float], tol: float, side: str, level_type: str) -> list[dict]:
    out: list[dict] = []
    used: set[int] = set()
    for i, v in enumerate(values):
        if i in used:
            continue
        cluster = [v]
        for j in range(i + 1, len(values)):
            if abs(values[j] - v) <= tol:
                cluster.append(values[j])
                used.add(j)
        if len(cluster) >= 2:
            out.append({"price": round(float(np.mean(cluster)), 5), "type": level_type, "side": side})
    return out


__all__ = [
    "SYMBOLS",
    "generate_synthetic_candles",
    "replay_candles",
    "current_tick",
    "session_for",
    "build_liquidity_levels",
]