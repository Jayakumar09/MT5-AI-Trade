"""Cartographer agent – liquidity mapping.

Deterministic Python: PDH/PDL, Asian session high/low, swing points,
equal-high/equal-low clusters.
"""
from __future__ import annotations

import time
from typing import Any

import numpy as np

from ..models import AgentResult, Candle
from ..strategy import LiquidityLevel, equal_highs, equal_lows, swing_levels
from .base import BaseAgent


class CartographerAgent(BaseAgent):
    name = "cartographer"

    def run(self, context: dict[str, Any]) -> AgentResult:
        start = time.time()
        instrument = context.get("instrument", "XAUUSD")
        candles = [Candle(**c) for c in context.get("candles_5m", [])]
        if not candles:
            return self._result("no_data", "Cartographer: no candles", {}, 0, self.timed(start))

        highs = np.array([c.high for c in candles], dtype=float)
        lows = np.array([c.low for c in candles], dtype=float)
        closes = np.array([c.close for c in candles], dtype=float)

        levels: list[LiquidityLevel] = []
        levels.append(LiquidityLevel("PDH", float(highs.max())))
        levels.append(LiquidityLevel("PDL", float(lows.min())))

        # Asian session high/low (first 6 hours of UTC day approximation)
        asian_high = float(highs[: max(1, len(highs) // 4)].max())
        asian_low = float(lows[: max(1, len(lows) // 4)].min())
        levels.append(LiquidityLevel("ASIAN_HIGH", asian_high))
        levels.append(LiquidityLevel("ASIAN_LOW", asian_low))

        levels += swing_levels(highs, lows)
        for p in equal_highs(highs):
            levels.append(LiquidityLevel("EQUAL_HIGHS", float(p)))
        for p in equal_lows(lows):
            levels.append(LiquidityLevel("EQUAL_LOWS", float(p)))

        # Session context
        hour = time.gmtime().tm_hour
        if 0 <= hour < 6:
            session = "ASIAN"
        elif 6 <= hour < 12:
            session = "LONDON"
        elif 12 <= hour < 21:
            session = "NEW_YORK"
        else:
            session = "NY_LATE"

        latency = self.timed(start)
        return self._result(
            "ok",
            f"Cartographer: mapped {len(levels)} liquidity levels ({session} session)",
            {
                "instrument": instrument,
                "levels": [
                    {"level_type": l.level_type, "price": l.price} for l in levels
                ],
                "session": session,
                "asian_high": asian_high,
                "asian_low": asian_low,
                "pdh": float(highs.max()),
                "pdl": float(lows.min()),
                "current_price": float(closes[-1]),
                "atr14": float(np.mean(np.diff(closes))) if len(closes) > 1 else 0.0,
            },
            confidence=9,
            latency_ms=latency,
        )
