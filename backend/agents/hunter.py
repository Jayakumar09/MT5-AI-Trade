"""Hunter agent – sweep + displacement detection.

Rule-based: finds liquidity sweeps with exact numbers and returns candidate
setups for the Analyst to refine.
"""
from __future__ import annotations

import time
from typing import Any

from ..models import AgentResult, Candle, SweepCandidate
from ..strategy import LiquidityLevel, detect_sweep
from .base import BaseAgent


class HunterAgent(BaseAgent):
    name = "hunter"

    def run(self, context: dict[str, Any]) -> AgentResult:
        start = time.time()
        instrument = context.get("instrument", "XAUUSD")
        candles = [Candle(**c) for c in context.get("candles_5m", [])]
        levels_raw = context.get("levels", [])
        levels = [LiquidityLevel(l["level_type"], float(l["price"])) for l in levels_raw]

        candidates = detect_sweep(candles, instrument, levels)
        latency = self.timed(start)

        if not candidates:
            return self._result(
                "no_data",
                "Hunter: no sweep detected this cycle",
                {"instrument": instrument, "candidates": []},
                confidence=3,
                latency_ms=latency,
            )

        best = candidates[0]
        return self._result(
            "ok",
            f"Hunter: {best.direction.upper()} sweep at {best.level_type} {best.level_price:.2f} "
            f"depth {best.extension_depth:.2f} quality {best.displacement_quality}",
            {
                "instrument": instrument,
                "candidates": [c.model_dump() for c in candidates],
                "count": len(candidates),
            },
            confidence=8,
            latency_ms=latency,
        )
