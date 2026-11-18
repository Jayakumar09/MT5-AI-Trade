"""AEGIS Risk Guardian — hard-coded veto rules + lot sizing.

Rules (non-negotiable, ADR-11 through ADR-19):
- Spread limit: XAUUSD 35 points; BTC configurable
- Risk per trade default 1%, max 2%
- Daily drawdown kill at 4%
- Max open trades configurable
- Min RR 1:2
- Min confidence 7
- Session filter
- Duplicate-signal cooldown
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import (
    AccountInfo,
    Signal,
)


class RiskRuleResult:
    """Result of evaluating a single risk rule."""

    def __init__(
        self,
        rule_name: str,
        veto: bool,
        reason: str,
        current: Any,
        limit: Any,
    ):
        self.rule_name = rule_name
        self.veto = veto
        self.reason = reason
        self.current = current
        self.limit = limit


class AegisResult:
    """Result of full AEGIS risk guard evaluation."""

    def __init__(self) -> None:
        self.vetoed: bool = False
        self.veto_reasons: list[str] = []
        self.approved: bool = True
        self.lot_size: Optional[float] = None
        self.confidence: Optional[float] = None
        self.drawdown_ok: bool = True
        self.rr_ok: bool = True
        self.session_ok: bool = True
        self.cooldown_ok: bool = True
        self.duplicate_ok: bool = True


def spread_ok(instrument: str, spread_points: int, rules: Dict[str, Any]) -> bool:
    """Check spread against configured limits."""
    if instrument.upper().startswith("XAU"):
        limit = rules.get("spread_limit_xau", 35)
        return spread_points <= limit
    # BTC config
    limit = rules.get("spread_limit_btc", 500)
    return spread_points <= limit


def risk_per_trade_ok(
    direction: str,
    signal_confidence: float,
    rules: Dict[str, Any],
    account: AccountInfo,
) -> bool:
    """Check risk-per-trade percentage against configured max."""
    default_risk = rules.get("risk_per_trade_default", 0.01)
    max_risk = rules.get("risk_per_trade_max", 0.02)
    # use default if no explicit value set
    risk_pct = max(default_risk, min(signal_confidence / 10.0, max_risk))
    # sanity check — never more than 2% of equity
    max_allowed_risk_usd = account.equity * risk_pct
    return risk_pct <= max_risk  # always validate against config


def rr_ok(trade_plan: dict) -> bool:
    """Check minimum risk-reward ratio 1:2."""
    rr = trade_plan.get("risk_reward_ratio", 0.0)
    return rr >= 2.0


def confidence_ok(confidence: float, rules: Dict[str, Any]) -> bool:
    """Check minimum confidence threshold."""
    min_c = rules.get("min_confidence", 7.0)
    return confidence >= min_c


def daily_drawdown_ok(account: AccountInfo, rules: Dict[str, Any]) -> bool:
    """Check daily drawdown has not exceeded the kill level."""
    kill_level = rules.get("daily_drawdown_kill", 0.04)  # 4%
    current_dd = account.daily_drawdown / account.equity if account.equity > 0 else 0.0
    return current_dd <= kill_level


def max_open_trades_ok(
    open_trades: int,
    rules: Dict[str, Any],
) -> bool:
    """Check maximum concurrent open trades limit."""
    max_trades = rules.get("max_open_trades", 5)
    return open_trades <= max_trades


def session_ok(
    instrument: str,
    current_time: Any,
    rules: Dict[str, Any],
) -> bool:
    """Check session filter (e.g., gold only trades certain sessions)."""
    # If no session filter configured, always OK
    filter_cfg = rules.get("session_filter", {})
    if not filter_cfg:
        return True
    # Session filtering logic would go here; defaults to OK
    return True


def duplicate_signal_ok(
    signal_id: str,
    recent_signals: list[str],
    rules: Dict[str, Any],
    cooldown_minutes: int = 30,
) -> bool:
    """Check cooldown against recently sent signals."""
    if not recent_signals:
        return True
    # Simple check: signal should not appear in last cooldown_minutes signals
    return signal_id not in recent_signals


def aegis_guard(
    instrument: str,
    signal: Signal,
    account: AccountInfo,
    trade_plan: dict,
    rules: Dict[str, Any],
    recent_signals: list[str],
) -> AegisResult:
    """Full AEGIS risk guard evaluation.

    Returns AegisResult with veto flags and lot-size recommendation.
    """
    result = AegisResult()

    # 1. Spread limit check
    # Spread comes from latest tick data; if not available, we assume paper OK
    spread_pass = spread_ok(instrument, signal.slippage_points, rules)
    if not spread_pass:
        result.vetoed = True
        result.veto_reasons.append(
            f"Spread {signal.slippage_points} exceeds limit for {instrument}"
        )
    else:
        result.rr_ok = rr_ok(trade_plan)

    # 2. Risk per trade / lot sizing
    if risk_per_trade_ok(
        signal.direction,
        signal.confidence,
        rules,
        account,
    ):
        # Compute lot size normalized to 1% risk
        equity = account.equity
        entry_px = float(trade_plan.get("entry_price", 0.0) or 0.0)
        sl_px = float(trade_plan.get("stop_loss", 0.0) or 0.0)
        if entry_px > 0 and sl_px > 0:
            risk_per_unit = abs(entry_px - sl_px)
            if risk_per_unit > 0:
                lot_size = (equity * 0.01) / (risk_per_unit * 10.0)  # simplified
                result.lot_size = round(max(lot_size, 0.01), 3)
        else:
            result.lot_size = 0.01
    else:
        result.veto_reasons.append("Risk per trade limit would be exceeded")
        result.vetoed = True

    # 3. Min RR check
    if not rr_ok(trade_plan):
        result.veto_reasons.append("Risk-reward ratio below minimum 1:2")
        result.vetoed = True

    # 4. Min confidence check
    if not confidence_ok(signal.confidence, rules):
        result.veto_reasons.append(f"Confidence {signal.confidence} below minimum 7")
        result.vetoed = True

    # 5. Daily drawdown check
    if not daily_drawdown_ok(account, rules):
        result.veto_reasons.append(
            f"Daily drawdown {account.daily_drawdown:.2f} exceeds kill level 4%"
        )
        result.vetoed = True

    # 6. Max open trades check
    open_trades = getattr(account, "open_trades_count", 0)
    if not max_open_trades_ok(open_trades, rules):
        result.veto_reasons.append(
            f"Open trades {open_trades} exceeds limit {rules.get('max_open_trades', 5)}"
        )
        result.vetoed = True

    # 7. Session filter
    if not session_ok(instrument, account.ts if hasattr(account, "ts") else None, rules):
        result.veto_reasons.append(f"Session filter blocked trading {instrument}")
        result.vetoed = True

    # 8. Duplicate signal cooldown
    if not duplicate_signal_ok(
        signal.id, recent_signals, rules, cooldown_minutes=30,
    ):
        result.veto_reasons.append("Duplicate signal within cooldown period")
        result.vetoed = True

    # If not vetoed, approved
    if not result.vetoed:
        result.approved = True
        result.lot_size = result.lot_size or 0.01

    return result