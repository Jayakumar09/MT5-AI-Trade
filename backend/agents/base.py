"""Common agent interface for QUANT PILOT (doc §MULTI-AGENT ARCHITECTURE).

Each agent is its own module exposing a class with ``run(context) -> AgentResult``.

``context`` is a plain dict carrying the shared cycle state:
  - instrument: str
  - candles: dict[str, list[Candle]]  (timeframe -> candles)
  - tick: MarketTick
  - account: AccountInfo
  - paper_engine: PaperEngine
  - mt5: MT5Client
  - db: sqlite3.Connection | None
  - signal: Signal | None   (set by agents as the cycle progresses)
  - liquidity_levels / candidate / analyst / guardian: dict | None
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from ..core.models import AgentResult

logger = logging.getLogger("quantpilot.agents")


class Agent(ABC):
    """Base class for all QUANT PILOT agents."""

    name: str = "AGENT"

    @abstractmethod
    def run(self, context: dict) -> AgentResult:
        raise NotImplementedError

    def _result(
        self,
        status: str,
        summary: str,
        data: dict | None = None,
        confidence: float = 0.0,
        started: float | None = None,
    ) -> AgentResult:
        elapsed_ms = int((time.perf_counter() - (started or time.perf_counter())) * 1000)
        payload = dict(data or {})
        payload["latency_ms"] = elapsed_ms
        return AgentResult(
            status=status,
            summary=summary,
            data=payload,
            confidence=confidence,
            timestamp=datetime.now(timezone.utc),
        )

    def tick_broadcast(self, ws_manager, event: dict) -> None:
        """Best-effort WebSocket broadcast; never raises."""
        if ws_manager is None:
            return
        try:
            event = {"agent": self.name, **event, "ts": datetime.now(timezone.utc).isoformat()}
            ws_manager.publish(event)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("broadcast failed for %s: %s", self.name, exc)