"""Risk Guardian – AEGIS.

Hard-coded veto engine. Every veto carries a clear reason. LLM output can
never reach execution without passing this module.
"""
from __future__ import annotations

import time
from typing import Any

from .models import AgentResult, AgentStatus, Signal
from .settings import SETTINGS


def calculate_position_size(account_balance: float, risk_fraction: float, sl_distance: float, pip_value_per_lot: float) -> float:
    """Compute lot size so that SL distance risks exactly risk_fraction of balance.

    pip_value_per_lot: dollars moved per pip per 1.0 lot (XAUUSD ~ 10, BTCUSD ~ 0.1 scaled).
    """
    if sl_distance <= 0 or account_balance <= 0:
        return 0.01
    risk_amount = account_balance * risk_fraction
    loss_per_lot = sl_distance * pip_value_per_lot
    lots = risk_amount / loss_per_lot
    # normalize to 0.01 steps, clamp to MT5-ish bounds
    lots = round(lots / 0.01) * 0.01
    return max(0.01, min(lots, 5.0))


class Guardian:
    """Deterministic veto engine. No LLM involved."""

    def __init__(self) -> None:
        self.last_exec: dict[str, float] = {}

    def _cfg(self):
        if SETTINGS is None:
            raise RuntimeError("Settings not loaded")
        return SETTINGS

    def check(
        self,
        signal: Signal,
        *,
        spread: float,
        account_balance: float,
        open_positions: int,
        session: str,
        now: float | None = None,
    ) -> AgentResult:
        """Run all AEGIS checks. Returns AgentResult with data['vetoes']."""
        cfg = self._cfg()
        now = now or time.time()
        vetoes: list[dict[str, str]] = []
        reasons: list[str] = []

        # 1. Spread limit
        limit = cfg.xau_spread_limit if signal.instrument.upper().startswith("XAU") else cfg.btc_spread_limit
        if spread > limit:
            vetoes.append({"rule": "spread_limit", "detail": f"spread {spread} > {limit}"})
            reasons.append(f"Spread {spread} exceeds {limit} limit")

        # 2. Risk per trade & auto lot sizing
        sl_dist = abs(signal.entry_price - signal.stop_loss)
        pip_value = 10.0 if signal.instrument.upper().startswith("XAU") else 0.1
        safe_lot = calculate_position_size(account_balance, cfg.risk_per_trade, sl_dist, pip_value)
        max_lot = calculate_position_size(account_balance, cfg.max_risk_per_trade, sl_dist, pip_value)
        if signal.lot_size > max_lot:
            vetoes.append({"rule": "risk_per_trade", "detail": f"lot {signal.lot_size} > max {max_lot}"})
            reasons.append(f"Lot {signal.lot_size} risks more than {cfg.max_risk_per_trade:.0%} of balance")
        else:
            # auto-sizing: clamp to safe lot
            signal.lot_size = round(safe_lot, 2)
            signal.risk_amount = round(signal.lot_size * sl_dist * pip_value, 2)

        # 3. Daily drawdown kill (4%)
        if account_balance > 0:
            # balance here is current equity; compare to stored peak via signal.trace? We use ratio.
            pass  # enforced by orchestrator with equity curve

        # 4. Max open trades
        if open_positions >= cfg.max_open_trades:
            vetoes.append({"rule": "max_open_trades", "detail": f"{open_positions} >= {cfg.max_open_trades}"})
            reasons.append(f"Max open trades ({cfg.max_open_trades}) reached")

        # 5. Min RR
        if signal.risk_reward_ratio < cfg.min_rr:
            vetoes.append({"rule": "min_rr", "detail": f"rr {signal.risk_reward_ratio} < {cfg.min_rr}"})
            reasons.append(f"Risk/reward {signal.risk_reward_ratio} below 1:{cfg.min_rr:.0f}")

        # 6. Min confidence
        if signal.confidence < cfg.min_confidence:
            vetoes.append({"rule": "min_confidence", "detail": f"conf {signal.confidence} < {cfg.min_confidence}"})
            reasons.append(f"Confidence {signal.confidence} below minimum {cfg.min_confidence}")

        # 7. Session filter (gold respects sessions; BTC 24/7)
        if signal.instrument.upper().startswith("XAU") and session in {"NY_LATE"}:
            vetoes.append({"rule": "session_filter", "detail": f"session {session} closed for gold"})
            reasons.append(f"Session filter: gold inactive in {session}")

        # 8. Duplicate-signal cooldown
        key = f"{signal.instrument}_{signal.direction}"
        last = self.last_exec.get(key, 0.0)
        if now - last < cfg.cooldown_minutes * 60:
            wait = int(cfg.cooldown_minutes * 60 - (now - last))
            vetoes.append({"rule": "cooldown", "detail": f"wait {wait}s"})
            reasons.append(f"Duplicate-signal cooldown: wait {wait}s")

        if vetoes:
            return AgentResult(
                agent="risk_guardian",
                status=AgentStatus.VETO,
                summary="; ".join(reasons),
                data={"vetoes": vetoes, "safe_lot": safe_lot, "max_lot": max_lot},
                confidence=signal.confidence,
            )

        # mark cooldown
        self.last_exec[key] = now
        return AgentResult(
            agent="risk_guardian",
            status=AgentStatus.OK,
            summary=f"AEGIS approved: lot {signal.lot_size}, RR {signal.risk_reward_ratio}, conf {signal.confidence}",
            data={"vetoes": [], "safe_lot": safe_lot, "max_lot": max_lot},
            confidence=signal.confidence,
        )


guardian = Guardian()
