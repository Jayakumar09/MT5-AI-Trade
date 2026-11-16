"""Base agent interface.

Every agent implements run(context) -> AgentResult. The Orchestrator calls
them in sequence and broadcasts each result over WebSocket.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from ..models import AgentResult


class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    def run(self, context: dict[str, Any]) -> AgentResult:
        """Execute the agent's job. Must return an AgentResult."""

    def _result(
        self,
        status: str,
        summary: str,
        data: dict[str, Any] | None = None,
        confidence: int = 0,
        latency_ms: float = 0.0,
    ) -> AgentResult:
        return AgentResult(
            agent=self.name,
            status=status,
            summary=summary,
            data=data or {},
            confidence=confidence,
            latency_ms=latency_ms,
        )

    @staticmethod
    def timed(start: float) -> float:
        return (time.time() - start) * 1000.0
