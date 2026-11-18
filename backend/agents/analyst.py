"""Analyst — Claude (LLM) decision layer.

Gets the Hunter's candidate plus compact context and returns STRICT JSON
validated by Pydantic (``AnalysisDecision``). Retries once on invalid JSON,
then returns NO_TRADE. Claude may only refine or reject the Hunter's
candidate — never invent prices. If ANTHROPIC_API_KEY is missing, a rule-based
mock is used (Demo-friendly, deterministic).
"""

from __future__ import annotations

import json
import logging
import os
import time

from pydantic import ValidationError

from ..core.models import AnalysisDecision, AgentResult
from .base import Agent

logger = logging.getLogger("quantpilot.agents.analyst")

PROMPT = (
    "You are the QUANT PILOT analyst. The Hunter detected a Liquidity Sweep setup. "
    "You may ONLY refine or reject this candidate — never invent prices. "
    "Return STRICT JSON matching this schema exactly:\n"
    '{"instrument": str, "bias": "BULLISH_SWEEP_LONG"|"BEARISH_SWEEP_SHORT"|"NO_TRADE", '
    '"confidence_score": int 1-10, "htf_level_targeted": str, '
    '"sweep_details": {"extension_depth": number, "displacement_quality": number}, '
    '"trade_plan": {"entry_price": number, "stop_loss": number, "take_profit_1": number, '
    '"take_profit_2": number, "risk_reward_ratio": number}, '
    '"reasoning": str (max 3 sentences), "invalidation_conditions": [str]}\n'
    "Output ONLY the JSON object, no prose."
)


def _rule_based_decision(candidate: dict) -> AnalysisDecision:
    """Deterministic mock used when no Claude key is configured."""
    direction = candidate.get("direction", "LONG")
    bias = "BULLISH_SWEEP_LONG" if direction == "LONG" else "BEARISH_SWEEP_SHORT"
    depth = float(candidate.get("sweep_details", {}).get("extension_depth", 0.0))
    displacement = float(candidate.get("sweep_details", {}).get("displacement_quality", 1.3))
    conf = 8 if displacement >= 1.5 and depth > 0 else 6
    if conf < 7:
        bias = "NO_TRADE"
    return AnalysisDecision(
        instrument=candidate.get("instrument", "XAUUSD"),
        bias=bias,
        confidence_score=conf,
        htf_level_targeted=str(candidate.get("htf_level_targeted", "unknown")),
        sweep_details={
            "extension_depth": depth,
            "displacement_quality": displacement,
        },
        trade_plan={
            "entry_price": float(candidate["entry_price"]),
            "stop_loss": float(candidate["stop_loss"]),
            "take_profit_1": float(candidate["take_profit_1"]),
            "take_profit_2": float(candidate["take_profit_2"]),
            "risk_reward_ratio": float(candidate["risk_reward_ratio"]),
        },
        reasoning=(
            "Rule-based mock analyst (no ANTHROPIC_API_KEY set): sweep depth and displacement "
            "meet the strategy thresholds, and the candidate aligns with the mapped liquidity level. "
            "Approved subject to AEGIS risk guardian vetoes."
        ),
        invalidation_conditions=[
            "No re-entry inside the range within 3 candles",
            "News-hour filter triggered",
            "Close back through the swept level",
        ],
    )


def _call_claude(candidate: dict) -> dict:  # pragma: no cover - requires API key
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    msg = client.messages.create(
        model=model,
        max_tokens=800,
        system=PROMPT,
        messages=[{"role": "user", "content": json.dumps({"candidate": candidate})}],
    )
    text = "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")
    return json.loads(text)


class AnalystAgent(Agent):
    name = "ANALYST"

    def __init__(self, use_claude: bool | None = None) -> None:
        self._use_claude = bool(os.environ.get("ANTHROPIC_API_KEY")) if use_claude is None else use_claude

    def run(self, context: dict) -> AgentResult:
        started = time.perf_counter()
        instrument: str = context.get("instrument", "XAUUSD")
        candidate = context.get("hunter_candidate") or (context.get("signal") or {}).get("candidate") or context.get("candidate")

        if context.get("no_trade") or not candidate:
            return self._result(
                "NO_TRADE",
                "No Hunter candidate to analyze",
                data={"instrument": instrument},
                confidence=0.0,
                started=started,
            )

        decision: AnalysisDecision | None = None
        used = "MOCK_RULE_BASED"
        if self._use_claude:
            try:
                raw = _call_claude(candidate)
                decision = AnalysisDecision.model_validate(raw)
                used = "CLAUDE_LIVE"
            except Exception as exc:
                logger.warning("Claude call failed (%s); retrying once", exc)
                try:  # one retry
                    raw = _call_claude(candidate)
                    decision = AnalysisDecision.model_validate(raw)
                    used = "CLAUDE_LIVE"
                except Exception as exc2:
                    logger.warning("Claude retry failed (%s) — NO_TRADE", exc2)
        else:
            decision = _rule_based_decision(candidate)

        if decision is None or decision.bias == "NO_TRADE":
            return self._result(
                "NO_TRADE",
                "Analyst rejected the candidate (or no valid response) — NO_TRADE",
                data={"instrument": instrument, "analyst_source": used},
                confidence=0.0,
                started=started,
            )

        # Claude may only refine/reject — enforce Hunter's prices when present
        tp = decision.trade_plan
        refined = dict(tp.model_dump())
        for key, src in (("entry_price", "entry_price"), ("stop_loss", "stop_loss"), ("take_profit_1", "take_profit_1"), ("take_profit_2", "take_profit_2")):
            if src in candidate and candidate[src] is not None:
                refined[key] = float(candidate[src])
        refined["risk_reward_ratio"] = (
            abs(refined["take_profit_1"] - refined["entry_price"]) / abs(refined["entry_price"] - refined["stop_loss"])
            if abs(refined["entry_price"] - refined["stop_loss"]) > 0 else 0.0
        )

        return self._result(
            "CANDIDATE",
            (
                f"Analyst ({used}): {decision.bias}, confidence {decision.confidence_score}/10 — "
                f"{decision.reasoning}"
            ),
            data={
                "instrument": instrument,
                "analyst_source": used,
                "analysis": decision.model_dump(mode="json"),
                "trade_plan": refined,
                "htf_level_targeted": decision.htf_level_targeted,
                "sweep_details": decision.sweep_details,
                "invalidation_conditions": decision.invalidation_conditions,
                "bias": decision.bias,
                "confidence_score": decision.confidence_score,
                "reasoning": decision.reasoning,
            },
            confidence=min(decision.confidence_score / 10.0, 1.0),
            started=started,
        )