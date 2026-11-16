"""Scout agent – data collection.

Pulls OHLCV on 5M/15M/4H/Daily, spread, and account info from MT5 or Demo.
"""
from __future__ import annotations

import time
from typing import Any

from ..demo_data import account_info, generate_candles, spread_for
from ..models import AgentResult
from ..settings import SETTINGS
from .base import BaseAgent


class ScoutAgent(BaseAgent):
    name = "scout"

    def run(self, context: dict[str, Any]) -> AgentResult:
        start = time.time()
        instrument = context.get("instrument", "XAUUSD")
        demo = SETTINGS.demo_mode if SETTINGS else True
        try:
            candles_5m = generate_candles(instrument, 120, 5)
            candles_15m = generate_candles(instrument, 80, 15)
            candles_4h = generate_candles(instrument, 60, 240)
            candles_daily = generate_candles(instrument, 30, 1440)
            spread = spread_for(instrument)
            account = account_info()
            latency = self.timed(start)
            return self._result(
                "ok",
                f"Scout: fetched {len(candles_5m)} 5M bars for {instrument}, spread {spread}",
                {
                    "instrument": instrument,
                    "candles_5m": [c.model_dump() for c in candles_5m],
                    "candles_15m": [c.model_dump() for c in candles_15m],
                    "candles_4h": [c.model_dump() for c in candles_4h],
                    "candles_daily": [c.model_dump() for c in candles_daily],
                    "spread": spread,
                    "account": account,
                    "mode": "demo" if demo else "mt5",
                },
                confidence=10,
                latency_ms=latency,
            )
        except Exception as e:
            return self._result("error", f"Scout failed: {e}", {}, 0, self.timed(start))
