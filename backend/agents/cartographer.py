"""Cartographer — Liquidity Mapper.

Maps PDH/PDL, session ranges, swing points, and equal-high/low clusters using
deterministic Python (no AI).
"""

from __future__ import annotations

import time

from ..core.demo_data import build_liquidity_levels, session_for
from .base import Agent


class CartographerAgent(Agent):
    name = "CARTOGRAPHER"

    def run(self, context: dict):
        started = time.perf_counter()
        instrument: str = context.get("instrument", "XAUUSD")
        candles = (context.get("candles") or {}).get("5m") or []

        levels = build_liquidity_levels(candles, instrument)
        session = session_for(candles[-1].ts) if candles else "UNKNOWN"

        return self._result(
            "OK",
            f"Liquidity map for {instrument}: {len(levels)} levels (PDH/PDL, swings, equal highs/lows, session ranges) — session {session}",
            data={
                "instrument": instrument,
                "liquidity_levels": levels,
                "session": session,
                "level_count": len(levels),
                "above": [l for l in levels if l["side"] == "above"],
                "below": [l for l in levels if l["side"] == "below"],
            },
            confidence=1.0,
            started=started,
        )