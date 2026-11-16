"""Risk Guardian agent – wraps the AEGIS veto engine as an agent."""
from __future__ import annotations

import time
from typing import Any

from ..models import AgentResult, Signal
from ..risk import guardian
from .base import BaseAgent


class GuardianAgent(BaseAgent):
    name = "risk_guardian"

    def run(self, context: dict[str, Any]) -> AgentResult:
        start = time.time()
        signal = context.get("signal")
        if signal is None:
            return self._result("skipped", "Guardian: no signal to check", {}, 0, self.timed(start))
        if isinstance(signal, dict):
            signal = Signal(**signal)

        result = guardian.check(
            signal,
            spread=float(context.get("spread", 0)),
            account_balance=float(context.get("account_balance", 10000)),
            open_positions=int(context.get("open_positions", 0)),
            session=str(context.get("session", "LONDON")),
        )
        result.latency_ms = self.timed(start)
        if result.status.value == "veto":
            context["guardian_veto"] = True
        else:
            context["guardian_veto"] = False
        return result
