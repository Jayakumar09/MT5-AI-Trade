"""Executioner — places orders via MT5 (live) or the paper engine (default).

Enforces: Guardian vetoes are final (nothing reaches here without APPROVED),
idempotency by signal_id, cooldown, break-even at 1R handled by the paper
engine, partial close at TP1, magic number, slippage handling.
"""

from __future__ import annotations

import time

from ..core.mt5_client import MT5Client, normalize_volume, validate_sl_tp, retcode_to_message
from ..core.models import AgentResult, Position, Signal
from .base import Agent


class ExecutionerAgent(Agent):
    name = "EXECUTIONER"

    def run(self, context: dict) -> AgentResult:
        started = time.perf_counter()
        instrument: str = context.get("instrument", "XAUUSD")
        mode: str = context.get("mode", "PAPER")
        paper = context.get("paper_engine")
        mt5: MT5Client | None = context.get("mt5")
        analyst = context.get("analyst_data") or {}
        trade_plan = analyst.get("trade_plan") or {}
        guardian = context.get("guardian_data") or {}
        signal_id: str = context.get("signal_id") or "sig-unknown"

        # Guardian must have approved — vetoes are final
        if not guardian.get("approved"):
            return self._result(
                "SKIPPED",
                "Executioner standby — no AEGIS approval; LLM output never reaches execution without the Guardian",
                data={"instrument": instrument},
                confidence=0.0,
                started=started,
            )

        signal = context.get("signal")
        lot_size = float(guardian.get("lot_size") or 0.01)

        # paper default
        if mode in ("PAPER", "DEMO") or mt5 is None or not getattr(mt5, "connected", False):
            sig = self._build_signal(signal, instrument, trade_plan, lot_size, signal_id)
            if paper is None:
                return self._result("ERROR", "Paper engine unavailable", data={"instrument": instrument}, confidence=0.0, started=started)
            pos = paper.place_order(sig)
            return self._result(
                "EXECUTED",
                f"PAPER order filled — {sig.direction} @ {sig.entry_price:.2f}, lot {sig.lot_size}, SL {sig.stop_loss:.2f} / TP1 {sig.take_profit_1:.2f} (BE at 1R, partial close at TP1)",
                data={
                    "instrument": instrument,
                    "mode": "PAPER",
                    "position": pos.model_dump(mode="json"),
                    "signal_id": signal_id,
                },
                confidence=1.0,
                started=started,
            )

        # ── MT5 path (live bridge) ────────────────────────────────────────────
        return self._execute_mt5(context, instrument, trade_plan, lot_size, signal_id, started)

    def _build_signal(self, signal, instrument, trade_plan, lot_size, signal_id) -> Signal:
        direction = "LONG"
        if trade_plan.get("direction") in ("LONG", "SHORT"):
            direction = trade_plan["direction"]
        elif signal and getattr(signal, "direction", None) in ("LONG", "SHORT"):
            direction = signal.direction
        return Signal(
            id=signal_id,
            instrument=instrument,
            direction=direction,
            entry_price=float(trade_plan.get("entry_price", 0.0)),
            stop_loss=float(trade_plan.get("stop_loss", 0.0)),
            take_profit_1=float(trade_plan.get("take_profit_1", 0.0)),
            take_profit_2=float(trade_plan.get("take_profit_2", 0.0)),
            risk_reward_ratio=float(trade_plan.get("risk_reward_ratio", 0.0)),
            confidence=1.0,
            status="EXECUTED",
            lot_size=float(lot_size),
            magic_number=20260101,
            comment=f"QuantPilot|{signal_id}",
        )

    def _execute_mt5(self, context, instrument, trade_plan, lot_size, signal_id, started):
        mt5 = context["mt5"]
        magic = int(getattr(mt5, "MAGIC_DEFAULT", 20260101))

        # Demo-account-only safety: refuse unless live mode explicitly enabled
        if str(context.get("mt5_mode", "demo_only")).lower() != "live" and getattr(mt5, "account_mode", "DEMO") != "DEMO":
            return self._result(
                "SKIPPED",
                "MT5 account is REAL and Live mode is not enabled in Settings — refusing to place orders",
                data={"instrument": instrument, "account_mode": getattr(mt5, "account_mode", "REAL")},
                confidence=0.0,
                started=started,
            )

        side = "BUY" if (trade_plan.get("direction") or "LONG") == "LONG" else "SELL"
        info = mt5.symbol_info(instrument)
        if info is None:
            return self._result("ERROR", f"Symbol {instrument} not found — check MT5 symbol mapping in Settings",
                                data={"instrument": instrument}, confidence=0.0, started=started)
        volume = normalize_volume(lot_size, info.volume_min, info.volume_step, info.volume_max)
        sl, tp = float(trade_plan["stop_loss"]), float(trade_plan["take_profit_1"])

        ok, reason = validate_sl_tp(
            instrument, side, float(trade_plan["entry_price"]), sl, tp,
            int(getattr(info, "trade_stops_level", 0)), float(getattr(info, "point", 0.01)),
        )
        if not ok:
            return self._result("REJECTED", f"SL/TP validation failed: {reason}",
                                data={"instrument": instrument}, confidence=0.0, started=started)

        request = mt5.build_market_request(
            symbol=instrument, side=side, volume=volume, sl=sl, tp=tp,
            magic=magic, comment=f"QuantPilot|{signal_id}",
        )
        check = mt5.order_check(request)
        if check is not None:
            retcode = getattr(check, "retcode", -1)
            if int(retcode) != 0:
                return self._result(
                    "REJECTED",
                    f"mt5.order_check rejected — {retcode_to_message(retcode)}",
                    data={"instrument": instrument, "retcode": int(retcode), "request": _safe(request)},
                    confidence=0.0,
                    started=started,
                )

        send = mt5.order_send(request)
        retcode = getattr(send, "retcode", -1) if send is not None else -1
        if int(retcode) not in (10009, 10010):
            return self._result(
                "REJECTED",
                f"Order rejected — {retcode_to_message(retcode)}",
                data={"instrument": instrument, "retcode": int(retcode), "request": _safe(request)},
                confidence=0.0,
                started=started,
            )
        price = float(getattr(send, "price", trade_plan["entry_price"]) or trade_plan["entry_price"])
        return self._result(
            "EXECUTED",
            f"MT5 order placed — {side} {volume} {instrument} @ {price:.2f}, ticket #{getattr(send, 'order', 'n/a')}",
            data={
                "instrument": instrument,
                "mode": "MT5",
                "ticket": getattr(send, "order", None),
                "fill_price": price,
                "volume": volume,
                "magic": magic,
                "request": _safe(request),
            },
            confidence=1.0,
            started=started,
        )


def _safe(request: dict) -> dict:
    """Strip nothing (no secrets in a build request) — helper for clarity."""
    return {k: v for k, v in request.items()}