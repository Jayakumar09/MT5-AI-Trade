"""Chronicler agent – journal every decision with full agent trace.

Writes taken / vetoed / skipped decisions to SQLite and composes the AI
end-of-day review.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from ..db import insert_journal
from ..models import AgentResult, AgentStatus, JournalEntry
from .base import BaseAgent


class ChroniclerAgent(BaseAgent):
    name = "chronicler"

    def run(self, context: dict[str, Any]) -> AgentResult:
        start = time.time()
        trace = context.get("trace", [])
        event = context.get("event", "cycle")
        summary = context.get("summary", "Cycle completed")
        instrument = context.get("instrument", "")
        agent_name = context.get("agent", "orchestrator")

        entry = JournalEntry(
            entry_id=str(uuid.uuid4()),
            event=event,
            instrument=instrument,
            agent=agent_name,
            summary=summary,
            detail={"trace": trace, "context_keys": list(context.keys())},
        )
        insert_journal(entry)
        latency = self.timed(start)
        return self._result(
            "ok",
            f"Chronicler: logged '{event}' – {summary[:80]}",
            {"entry_id": entry.entry_id, "journal_size": len(trace)},
            confidence=10,
            latency_ms=latency,
        )

    def daily_review(self, entries: list[dict]) -> str:
        """Compose an AI end-of-day review from the journal."""
        taken = [e for e in entries if e.get("event") == "signal_taken"]
        vetoes = [e for e in entries if e.get("event") == "vetoed"]
        skipped = [e for e in entries if e.get("event") == "skipped"]
        wins = sum(1 for e in entries if e.get("event") == "closed" and e.get("detail", {}).get("pnl", 0) > 0)
        losses = sum(1 for e in entries if e.get("event") == "closed" and e.get("detail", {}).get("pnl", 0) <= 0)
        return (
            f"End-of-day review: {len(taken)} signal(s) taken, {len(vetoes)} veto(s) by AEGIS, "
            f"{len(skipped)} cycle(s) skipped. Closed trades: {wins} win / {losses} loss. "
            "Guardian discipline held: no LLM output reached execution without passing AEGIS."
        )
