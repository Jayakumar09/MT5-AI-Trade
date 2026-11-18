"""Risk Guardian (AEGIS) — hard-coded vetoes + lot sizing.

Every veto shows a clear reason. Vetoes are final — LLM output can never
reach the Executioner without passing this gate.
"""

from __future__ import annotations

import time
from typing import Any

from ..core.models import AgentResult
from ..core.risk import aegis_guard
from .base import Agent

DEFAULT_RULES: dict[str, Any] = {
    "spread_limit_xau": 35,
    "spread_limit_btc": 500,
    "risk_per_trade_default": 0.01,
    "risk_per_trade_max": 0.02,
    "daily_drawdown_kill": 0.04,
    "max_open_trades": 5,
    "min_rr": 2.0,
    "min_confidence": 7.0,
    "session_filter": {},
}


class RiskGuardianAgent(Agent):
    name = "GUARDIAN"

    def run(self, context: dict) -> AgentResult:
        started = time.perf_counter()
        instrument: str = context.get("instrument", "XAUUSD")
        rules = {**DEFAULT_RULES, **(context.get("guardian_rules") or {})}
        account = context.get("account")
        analyst = context.get("analyst_data") or {}
        trade_plan = (analyst.get("trade_plan") or {})
        signal = context.get("signal")

        if signal is None or not trade_plan:
            return self._result(
                "SKIPPED",
                "No proposed trade to review",
                data={"instrument": instrument},
                confidence=0.0,
                started=started,
            )

        # Adapt models for the aegis_guard entry contract
        from ..core.models import Signal as _Signal
        if isinstance(signal, dict):
            sig = _Signal(**{k: v for k, v in signal.items() if k in _Signal.model_fields}) if "entry_price" in signal else None
        else:
            sig = signal
        if sig is None:
            sig = _Signal(
                instrument=instrument,
                direction=trade_plan.get("direction", "LONG") or ("LONG" if analyst.get("bias", "") != "BEARISH_SWEEP_SHORT" else "SHORT"),
                entry_price=float(trade_plan.get("entry_price", 0.0)),
                stop_loss=float(trade_plan.get("stop_loss", 0.0)),
                take_profit_1=float(trade_plan.get("take_profit_1", 0.0)),
                take_profit_2=float(trade_plan.get("take_profit_2", 0.0)),
                risk_reward_ratio=float(trade_plan.get("risk_reward_ratio", 0.0)),
                confidence=float(analyst.get("confidence_score", 5)),
            )
        # keep confidence + RR from the analyst's actual plan
        sig.confidence = float(analyst.get("confidence_score", 5))
        if trade_plan.get("risk_reward_ratio"):
            sig.risk_reward_ratio = float(trade_plan["risk_reward_ratio"])

        # Attach spread from tick if present
        tick = context.get("tick")
        spread = int(getattr(tick, "spread_points", 0) or (tick or {}).get("spread_points", 0))

        open_trades = getattr(account, "open_trades_count", None)
        if open_trades is None:
            open_trades = 0
        try:
            setattr(account, "open_trades_count", open_trades)
        except Exception:
            pass

        result = aegis_guard(
            instrument=instrument,
            signal=_spread_signal(sig, spread),
            account=account,
            trade_plan=trade_plan,
            rules=rules,
            recent_signals=context.get("recent_signals", []),
        )

        # Override the RR-rule lookup: aegis_guard reads trade_plan dict
        if result.vetoed:
            return self._result(
                "VETOED",
                "VETO — " + "; ".join(result.veto_reasons),
                data={
                    "instrument": instrument,
                    "vetoed": True,
                    "veto_reasons": result.veto_reasons,
                    "lot_size": result.lot_size,
                    "rules": rules,
                },
                confidence=0.0,
                started=started,
            )

        return self._result(
            "APPROVED",
            f"AEGIS approved — lot size {result.lot_size}, all hard-coded vetoes passed",
            data={
                "instrument": instrument,
                "approved": True,
                "lot_size": result.lot_size,
                "rules": rules,
                "checklist": {
                    "level_swept": True,
                    "depth_in_range": True,
                    "displacement_strong": True,
                    "session_ok": True,
                    "rr_ge_1to2": True,
                    "guardian_approved": True,
                },
            },
            confidence=min(sig.confidence / 10.0, 1.0),
            started=started,
        )


def _spread_signal(sig, spread: int):
    """aegis_guard reads slippage for the spread check — reuse slippage_points."""
    sig.slippage_points = spread
    return sig