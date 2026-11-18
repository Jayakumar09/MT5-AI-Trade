"""Hunter — Sweep Detector.

Rule-based sweep + displacement detection on the 5M chart. Returns candidate
setups with exact numbers.
"""

from __future__ import annotations

import time

from ..strategy import detect_sweep, XAUUSD_PIPS_PER_POINT
from .base import Agent


class HunterAgent(Agent):
    name = "HUNTER"

    def run(self, context: dict):
        started = time.perf_counter()
        instrument: str = context.get("instrument", "XAUUSD")
        candles = (context.get("candles") or {}).get("5m") or []
        levels = context.get("liquidity_levels") or (context.get("scout_data") or {}).get("liquidity_levels") or []

        candidate = detect_sweep(instrument, candles, levels)

        if candidate is None:
            return self._result(
                "NO_TRADE",
                f"No sweep + displacement pattern detected on {instrument} — standing by",
                data={"instrument": instrument},
                confidence=0.0,
                started=started,
            )

        candidate["instrument"] = instrument
        return self._result(
            "CANDIDATE",
            (
                f"Sweep detected on {instrument}: {candidate['direction']} @ {candidate['entry_price']:.2f} "
                f"(SL {candidate['stop_loss']:.2f} / TP1 {candidate['take_profit_1']:.2f}, RR {candidate['risk_reward_ratio']})"
            ),
            data={"candidate": candidate},
            confidence=0.7,
            started=started,
        )