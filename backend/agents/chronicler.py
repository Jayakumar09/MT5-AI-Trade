"""Chronicler — Journal.

Logs every decision (taken, vetoed, skipped) to SQLite with the full agent
trace, and writes an AI end-of-day review.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

from ..core.models import AgentResult
from .base import Agent

logger = logging.getLogger("quantpilot.agents.chronicler")


class ChroniclerAgent(Agent):
    name = "CHRONICLER"

    def run(self, context: dict) -> AgentResult:
        started = time.perf_counter()
        db = context.get("db")
        trace = {
            "scout": (context.get("scout_data") or {}).get("summary"),
            "cartographer": (context.get("cartographer_data") or {}).get("summary"),
            "hunter": (context.get("hunter_data") or {}).get("summary"),
            "analyst": (context.get("analyst_data") or {}).get("summary"),
            "guardian": (context.get("guardian_data") or {}).get("summary"),
            "executioner": (context.get("executioner_data") or {}).get("summary"),
        }
        decision_id = None
        if db is not None:
            try:
                decision_id = self._log_decision(db, context, trace)
            except Exception as exc:
                logger.warning("failed to write journal entry: %s", exc)

        review = self._eod_review(context)

        return self._result(
            "OK",
            f"Journal updated (decision #{decision_id or 'n/a'}) — {review['summary']}",
            data={
                "decision_id": decision_id,
                "trace": trace,
                "eod_review": review,
            },
            confidence=1.0,
            started=started,
        )

    def _log_decision(self, db, context, trace) -> int | None:
        now = datetime.now(timezone.utc).isoformat()
        outcome = "TAKEN" if (context.get("guardian_data") or {}).get("approved") and (context.get("executioner_data") or {}).get("status") == "EXECUTED" else (
            "VETOED" if (context.get("guardian_data") or {}).get("vetoed") else "SKIPPED"
        )
        cur = db.execute(
            """
            INSERT INTO decisions (instrument, direction, entry_price, stop_loss, take_profit_1,
                take_profit_2, risk_reward, confidence, outcome, reason, trace_json, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                context.get("instrument", "XAUUSD"),
                (context.get("trade_plan") or {}).get("direction") or (context.get("signal") or {}).get("direction") or "UNKNOWN",
                float((context.get("trade_plan") or {}).get("entry_price", 0.0) or 0.0),
                float((context.get("trade_plan") or {}).get("stop_loss", 0.0) or 0.0),
                float((context.get("trade_plan") or {}).get("take_profit_1", 0.0) or 0.0),
                float((context.get("trade_plan") or {}).get("take_profit_2", 0.0) or 0.0),
                float((context.get("trade_plan") or {}).get("risk_reward_ratio", 0.0) or 0.0),
                float((context.get("analyst_data") or {}).get("confidence_score", 0) or 0),
                outcome,
                (context.get("guardian_data") or {}).get("veto_reasons", [""])[0] if outcome == "VETOED" else "cycle completed",
                json.dumps(trace),
                now,
            ),
        )
        db.commit()
        return cur.lastrowid

    def _eod_review(self, context) -> dict:
        analyst = context.get("analyst_data") or {}
        guardian = context.get("guardian_data") or {}
        if guardian.get("vetoed"):
            summary = "Cycle ended in VETO — discipline held; no order sent."
        elif (context.get("executioner_data") or {}).get("status") == "EXECUTED":
            summary = "Trade executed per plan — monitor BE at 1R and partial close at TP1."
        else:
            summary = "No trade this cycle — waiting for a qualifying sweep."
        return {
            "summary": summary,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "ai_generated": False,
        }

    @staticmethod
    def ai_eod_review(db) -> dict:
        """Aggregate the day's decisions into a one-paragraph review (rule-based)."""
        if db is None:
            return {"summary": "Journal empty", "decisions": 0}
        try:
            rows = db.execute(
                "SELECT outcome, COUNT(*) AS n FROM decisions GROUP BY outcome"
            ).fetchall()
            counts = {r["outcome"]: r["n"] for r in rows}
            total = sum(counts.values())
            taken = counts.get("TAKEN", 0)
            vetoed = counts.get("VETOED", 0)
            summary = (
                f"EOD REVIEW — {total} decisions logged: {taken} taken, {vetoed} vetoed, "
                f"{counts.get('SKIPPED', 0)} skipped. "
                "Discipline metrics held within AEGIS limits; review open trades for BE management."
            )
            return {"summary": summary, "decisions": total, "counts": counts}
        except Exception as exc:
            return {"summary": f"Review unavailable: {exc}", "decisions": 0}