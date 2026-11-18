"""Orchestrator — runs the seven agents in sequence every cycle.

Cycle order: Scout → Cartographer → Hunter → Analyst → Guardian → Executioner → Chronicler.
Each cycle broadcasts events over the provided WebSocket manager.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from .models import Candle, Signal
from ..agents.scout import ScoutAgent
from ..agents.cartographer import CartographerAgent
from ..agents.hunter import HunterAgent
from ..agents.analyst import AnalystAgent
from ..agents.risk_guardian import RiskGuardianAgent
from ..agents.executioner import ExecutionerAgent
from ..agents.chronicler import ChroniclerAgent

logger = logging.getLogger("quantpilot.orchestrator")

AGENT_SEQUENCE = ["SCOUT", "CARTOGRAPHER", "HUNTER", "ANALYST", "GUARDIAN", "EXECUTIONER", "CHRONICLER"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument TEXT NOT NULL,
    direction TEXT,
    entry_price REAL,
    stop_loss REAL,
    take_profit_1 REAL,
    take_profit_2 REAL,
    risk_reward REAL,
    confidence REAL,
    outcome TEXT NOT NULL,
    reason TEXT,
    trace_json TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS signals (
    id TEXT PRIMARY KEY,
    instrument TEXT NOT NULL,
    direction TEXT NOT NULL,
    entry_price REAL,
    stop_loss REAL,
    take_profit_1 REAL,
    take_profit_2 REAL,
    risk_reward REAL,
    confidence REAL,
    status TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS eod_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    summary TEXT NOT NULL,
    decisions INTEGER,
    created_at TEXT NOT NULL
);
"""


class Orchestrator:
    def __init__(self, ws_manager=None, db=None, paper_engine=None, mt5=None, mode: str = "PAPER") -> None:
        self.ws = ws_manager
        self.db = db
        self.paper = paper_engine
        self.mt5 = mt5
        self.mode = mode
        self.recent_signals: list[str] = []
        self.running = False
        self.cycle_count = 0
        self.last_cycle: dict[str, Any] | None = None

        self.scout = ScoutAgent()
        self.cartographer = CartographerAgent()
        self.hunter = HunterAgent()
        self.analyst = AnalystAgent()
        self.guardian = RiskGuardianAgent()
        self.executioner = ExecutionerAgent()
        self.chronicler = ChroniclerAgent()
        if self.db is not None:
            self._ensure_schema()

    def _ensure_schema(self) -> None:
        try:
            self.db.executescript(SCHEMA)
            self.db.commit()
        except Exception as exc:
            logger.warning("schema bootstrap failed: %s", exc)

    def publish(self, event: dict) -> None:
        if self.ws is not None:
            try:
                self.ws.publish(event)
            except Exception as exc:  # pragma: no cover
                logger.debug("ws publish failed: %s", exc)

    async def run_cycle(self, instrument: str = "XAUUSD") -> dict[str, Any]:
        cycle_id = f"cyc-{uuid.uuid4().hex[:8]}"
        self.publish({"type": "cycle_start", "cycle_id": cycle_id, "instrument": instrument, "ts": datetime.now(timezone.utc).isoformat()})
        results: dict[str, dict] = {}
        context: dict[str, Any] = {
            "instrument": instrument,
            "mode": self.mode,
            "mt5_mode": __import__("os").environ.get("MT5_MODE", "demo_only"),
            "mt5": self.mt5,
            "paper_engine": self.paper,
            "db": self.db,
            "ws": self.ws,
            "recent_signals": self.recent_signals[-20:],
        }

        def log_step(agent: str, res) -> None:
            results[agent.lower()] = res.model_dump(mode="json")
            payload = dict(res.data or {})
            payload.setdefault("summary", res.summary)
            payload.setdefault("status", res.status)
            context[f"{agent.lower()}_data"] = payload
            self.publish({
                "type": "agent_result",
                "cycle_id": cycle_id,
                "agent": agent,
                "status": res.status,
                "summary": res.summary,
                "confidence": res.confidence,
                "data": {k: v for k, v in (res.data or {}).items() if k != "candles"},  # avoid flooding the wire
                "ts": datetime.now(timezone.utc).isoformat(),
            })

        errors: list[str] = []

        try:
            res = self.scout.run(context)
            # Scout provides the raw candle payload separately to downstream agents
            context["candles"] = _unpack_scout_candles(res.data)
            context["tick"] = res.data.get("tick")
            context["account"] = _account_from_dict(res.data.get("account"))
            log_step("SCOUT", res)
        except Exception as exc:
            logger.exception("scout failed")
            errors.append(f"SCOUT: {exc}")

        try:
            liq = self.cartographer.run(context)
            context["liquidity_levels"] = liq.data.get("liquidity_levels", [])
            log_step("CARTOGRAPHER", liq)
        except Exception as exc:
            logger.exception("cartographer failed")
            errors.append(f"CARTOGRAPHER: {exc}")

        try:
            hunt = self.hunter.run(context)
            hunter_payload = hunt.data or {}
            candidate = hunter_payload.get("candidate")
            context["hunter_candidate"] = candidate
            context["no_trade"] = hunt.status == "NO_TRADE"
            context["trade_plan"] = candidate or {}
            log_step("HUNTER", hunt)
        except Exception as exc:
            logger.exception("hunter failed")
            errors.append(f"HUNTER: {exc}")

        try:
            ana = self.analyst.run(context)
            context["analyst_data"] = ana.data
            if ana.status == "CANDIDATE" and ana.data.get("trade_plan"):
                tp = ana.data["trade_plan"]
                context["trade_plan"] = tp
                context["signal"] = {
                    "id": f"sig-{uuid.uuid4().hex[:8]}",
                    "instrument": instrument,
                    "direction": "LONG" if ana.data.get("bias", "BULLISH_SWEEP_LONG") == "BULLISH_SWEEP_LONG" else "SHORT",
                    "entry_price": tp["entry_price"],
                    "stop_loss": tp["stop_loss"],
                    "take_profit_1": tp["take_profit_1"],
                    "take_profit_2": tp["take_profit_2"],
                    "risk_reward_ratio": tp["risk_reward_ratio"],
                    "confidence": ana.data.get("confidence_score", 5),
                }
            log_step("ANALYST", ana)
        except Exception as exc:
            logger.exception("analyst failed")
            errors.append(f"ANALYST: {exc}")

        try:
            guard = self.guardian.run(context)
            context["guardian_data"] = guard.data
            log_step("GUARDIAN", guard)
        except Exception as exc:
            logger.exception("guardian failed")
            errors.append(f"GUARDIAN: {exc}")

        try:
            ex = self.executioner.run(context)
            context["executioner_data"] = ex.data
            if ex.data.get("signal_id"):
                self.recent_signals.append(ex.data["signal_id"])
            log_step("EXECUTIONER", ex)
        except Exception as exc:
            logger.exception("executioner failed")
            errors.append(f"EXECUTIONER: {exc}")

        try:
            chron = self.chronicler.run(context)
            log_step("CHRONICLER", chron)
        except Exception as exc:
            logger.exception("chronicler failed")
            errors.append(f"CHRONICLER: {exc}")

        self.cycle_count += 1
        summary = {
            "cycle_id": cycle_id,
            "instrument": instrument,
            "errors": errors,
            "cycle_count": self.cycle_count,
            "results": results,
            "signal_id": (context.get("signal") or {}).get("id") if isinstance(context.get("signal"), dict) else None,
            "outcome": _outcome(context),
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        self.last_cycle = summary
        self.publish({"type": "cycle_end", **summary})
        return summary


def _unpack_scout_candles(data: dict) -> dict:
    raw = (data or {}).get("candles") or {}
    return {tf: [Candle(**c) for c in candles] for tf, candles in raw.items()}


def _account_from_dict(d):
    from .models import AccountInfo

    if not d:
        return AccountInfo()
    try:
        return AccountInfo(
            balance=float(d.get("balance", 10000)),
            equity=float(d.get("equity", 10000)),
            margin_free=float(d.get("margin_free", 10000)),
            profit=float(d.get("profit", 0.0)),
            drawdown=float(d.get("drawdown", 0.0)),
            daily_drawdown=float(d.get("daily_drawdown", 0.0)),
            mode=str(d.get("mode", "DEMO")),
            connected=bool(d.get("connected", False)),
        )
    except Exception:
        return AccountInfo()


def _outcome(context: dict) -> str:
    guardian = context.get("guardian_data") or {}
    executioner = context.get("executioner_data") or {}
    if guardian.get("approved") and executioner.get("status") == "EXECUTED":
        return "TAKEN"
    if guardian.get("vetoed"):
        return "VETOED"
    if context.get("no_trade"):
        return "NO_TRADE"
    return "SKIPPED"


__all__ = ["Orchestrator", "AGENT_SEQUENCE"]