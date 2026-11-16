"""Executioner agent – places orders via MT5 or the paper engine.

Idempotency: one signal creates at most one order (by signal_id).
"""
from __future__ import annotations

import time
from typing import Any

from ..db import fetch_signals
from ..models import AgentResult, AgentStatus, Signal
from ..paper_engine import paper_engine
from ..settings import SETTINGS
from .base import BaseAgent

_placed: set[str] = set()


class ExecutionerAgent(BaseAgent):
    name = "executioner"

    def run(self, context: dict[str, Any]) -> AgentResult:
        start = time.time()
        if context.get("guardian_veto"):
            return self._result(
                "skipped", "Executioner: Guardian vetoed – order never placed", {}, 0, self.timed(start)
            )
        signal = context.get("signal")
        if signal is None:
            return self._result("skipped", "Executioner: no signal", {}, 0, self.timed(start))
        if isinstance(signal, dict):
            signal = Signal(**signal)

        # Idempotency: never double-place
        if signal.signal_id in _placed:
            return self._result(
                "skipped", f"Executioner: signal {signal.signal_id} already executed", {}, 5, self.timed(start)
            )
        for row in fetch_signals(limit=1000):
            if row["signal_id"] == signal.signal_id and row["status"] == "placed":
                _placed.add(signal.signal_id)
                return self._result(
                    "skipped", f"Executioner: signal {signal.signal_id} already in DB", {}, 5, self.timed(start)
                )

        mode = "mt5" if SETTINGS and SETTINGS.data_mode == "mt5" else "paper"
        try:
            if mode == "mt5":
                from ..mt5_client import place_order

                res = place_order(
                    signal.instrument,
                    signal.direction,
                    signal.lot_size,
                    signal.stop_loss,
                    signal.take_profit_1,
                    signal.signal_id,
                )
            else:
                res = paper_engine.place_order(
                    signal.instrument,
                    signal.direction,
                    signal.lot_size,
                    signal.entry_price,
                    signal.stop_loss,
                    signal.take_profit_1,
                    signal.signal_id,
                )
        except Exception as e:
            return self._result("error", f"Executioner exception: {e}", {"signal_id": signal.signal_id}, 0, self.timed(start))

        if res.ok:
            _placed.add(signal.signal_id)
            signal.status = "placed"
            return self._result(
                "ok",
                f"Executioner: {'MT5' if mode == 'mt5' else 'paper'} order placed "
                f"{signal.direction} {signal.lot_size} {signal.instrument} @ {signal.entry_price} "
                f"(ticket {res.ticket})",
                {"signal_id": signal.signal_id, "ticket": res.ticket, "mode": mode, "fill_price": res.fill_price},
                10,
                self.timed(start),
            )
        return self._result(
            "error",
            f"Executioner: order rejected – {res.message}",
            {"signal_id": signal.signal_id, "retcode": res.retcode, "mode": mode},
            0,
            self.timed(start),
        )
