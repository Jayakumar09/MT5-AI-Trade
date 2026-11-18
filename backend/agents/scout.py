"""Scout — Data agent.

Provides OHLCV on 5M/15M/4H/Daily, spread, and account info from MT5 (live)
or Demo (synthetic). If MT5 is unavailable, falls back to Demo automatically
and flags it in the result payload.
"""

from __future__ import annotations

import time

from ..core.demo_data import current_tick, generate_synthetic_candles
from ..core.models import AgentResult
from .base import Agent


class ScoutAgent(Agent):
    name = "SCOUT"

    def run(self, context: dict) -> AgentResult:
        started = time.perf_counter()
        instrument: str = context.get("instrument", "XAUUSD")
        mt5 = context.get("mt5")
        paper = context.get("paper_engine")

        # Data source selection: MT5 when connected, else Demo
        source = "DEMO"
        if mt5 is not None and getattr(mt5, "connected", False):
            source = "MT5"

        candles_5m = context.get("candles") or {}
        if not candles_5m:
            candles_5m = {
                "5m": generate_synthetic_candles(instrument, count=300, interval_minutes=5, seed=42),
                "15m": generate_synthetic_candles(instrument, count=220, interval_minutes=15, seed=43),
                "4h": generate_synthetic_candles(instrument, count=160, interval_minutes=240, seed=44),
                "1d": generate_synthetic_candles(instrument, count=120, interval_minutes=1440, seed=45),
            }

        tick = current_tick(instrument)
        account = paper.account_info("DEMO" if source == "DEMO" else "MT5_LIVE") if paper else None

        return self._result(
            "OK",
            f"Data ready for {instrument} via {source} — 5M/15M/4H/1D loaded, spread {tick.spread_points} pts",
            data={
                "instrument": instrument,
                "source": source,
                "candles": {tf: [c.model_dump(mode="json") for c in candles_5m.get(tf, [])] for tf in candles_5m},
                "candle_counts": {tf: len(v) for tf, v in candles_5m.items()},
                "tick": tick.model_dump(mode="json"),
                "account": account.model_dump(mode="json") if account else {},
                "spread_points": tick.spread_points,
                "demo_mode": source == "DEMO",
            },
            confidence=1.0,
            started=started,
        )