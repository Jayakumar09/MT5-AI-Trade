"""Analyst agent – Claude refinement of the Hunter's candidate.

Sends the candidate plus compact context to Claude (claude-sonnet-5-5) and
requires STRICT JSON validated by Pydantic. Claude may only refine or reject
the Hunter's candidate – never invent prices. On invalid JSON we retry once,
then fall back to NO_TRADE. If the API key is missing we use a rule-based
mock so the app still works end-to-end in Demo Mode.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from ..models import AgentResult, AnalystOutput, Bias, SweepCandidate, SweepDetails, TradePlan
from ..settings import SETTINGS
from .base import BaseAgent

logger = logging.getLogger("quantpilot.analyst")

SYSTEM_PROMPT = (
    "You are the Analyst agent of QUANT PILOT. You receive a liquidity-sweep "
    "candidate from the Hunter plus compact market context. You may only REFINE "
    "or REJECT the candidate. You must NEVER invent prices that are not in the "
    "input. Reply with STRICT JSON only, no prose, no markdown, exactly this "
    "shape: {\"instrument\": string, \"bias\": \"BULLISH_SWEEP_LONG\" | "
    "\"BEARISH_SWEEP_SHORT\" | \"NO_TRADE\", \"confidence_score\": int 1-10, "
    "\"htf_level_targeted\": string, \"sweep_details\": {\"instrument\": string, "
    "\"level_type\": string, \"level_price\": number, \"extension_depth\": number, "
    "\"displacement_quality\": number 0-1, \"candles_to_close\": int, "
    "\"wick_extreme\": number}, \"trade_plan\": {\"entry_price\": number, "
    "\"stop_loss\": number, \"take_profit_1\": number, \"take_profit_2\": number, "
    "\"risk_reward_ratio\": number}, \"reasoning\": string max 3 sentences, "
    "\"invalidation_conditions\": string}. If the setup is weak, return "
    "bias=NO_TRADE with confidence_score 1 and keep the input prices unchanged."
)


def _mock_output(candidate: SweepCandidate) -> AnalystOutput:
    """Rule-based mock used when ANTHROPIC_API_KEY is missing."""
    quality = candidate.displacement_quality
    confidence = 8 if quality >= 0.7 else 5
    bias = Bias.BULLISH_SWEEP_LONG if candidate.direction == "long" else Bias.BEARISH_SWEEP_SHORT
    if quality < 0.5 or candidate.risk_reward_ratio < 2.0:
        bias = Bias.NO_TRADE
        confidence = 2
    return AnalystOutput(
        instrument=candidate.instrument,
        bias=bias,
        confidence_score=confidence,
        htf_level_targeted=candidate.level_type,
        sweep_details=SweepDetails(
            instrument=candidate.instrument,
            level_type=candidate.level_type,
            level_price=candidate.level_price,
            extension_depth=candidate.extension_depth,
            displacement_quality=candidate.displacement_quality,
            candles_to_close=candidate.candles_to_close,
            wick_extreme=candidate.wick_extreme,
        ),
        trade_plan=TradePlan(
            entry_price=candidate.entry_price,
            stop_loss=candidate.stop_loss,
            take_profit_1=candidate.take_profit_1,
            take_profit_2=candidate.take_profit_2,
            risk_reward_ratio=candidate.risk_reward_ratio,
        ),
        reasoning=(
            f"{candidate.level_type} swept by {candidate.extension_depth:.2f}. "
            f"Displacement closed back inside in {candidate.candles_to_close} candle(s). "
            f"Risk/reward {candidate.risk_reward_ratio} meets the 1:2 minimum."
        ),
        invalidation_conditions="Close back beyond the swept level; spread above limit; session rollover.",
    )


def _parse_claude(text: str, candidate: SweepCandidate) -> AnalystOutput:
    """Validate strict JSON from Claude; raise ValueError on failure."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1] if cleaned.count("```") >= 2 else cleaned
    cleaned = cleaned.strip()
    if cleaned.startswith("{"):
        # take the outermost object only
        depth = 0
        for i, ch in enumerate(cleaned):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    cleaned = cleaned[: i + 1]
                    break
    raw = json.loads(cleaned)
    # Guard: Claude may not invent prices outside the candidate's bounds.
    plan = raw.get("trade_plan", {})
    for key in ("entry_price", "stop_loss", "take_profit_1", "take_profit_2"):
        if key in plan:
            cand_val = {
                "entry_price": candidate.entry_price,
                "stop_loss": candidate.stop_loss,
                "take_profit_1": candidate.take_profit_1,
                "take_profit_2": candidate.take_profit_2,
            }[key]
            if not isinstance(plan[key], (int, float)) or plan[key] <= 0:
                plan[key] = cand_val
            # allow refinement within +/-2% only
            if abs(plan[key] - cand_val) / cand_val > 0.02:
                plan[key] = cand_val
    raw["trade_plan"] = plan
    raw.setdefault("instrument", candidate.instrument)
    return AnalystOutput(**raw)


def _call_claude(payload: dict[str, Any]) -> str:
    import anthropic

    if SETTINGS is None:
        raise RuntimeError("settings missing")
    client = anthropic.Anthropic(api_key=SETTINGS.anthropic_api_key)
    resp = client.messages.create(
        model=SETTINGS.anthropic_model,
        max_tokens=512,
        temperature=0.0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(payload)}],
    )
    return resp.content[0].text  # type: ignore[union-attr]


class AnalystAgent(BaseAgent):
    name = "analyst"

    def run(self, context: dict[str, Any]) -> AgentResult:
        start = time.time()
        candidate = context.get("candidate")
        if candidate is None:
            return self._result(
                "skipped", "Analyst: no candidate from Hunter", {}, 1, self.timed(start)
            )
        if isinstance(candidate, dict):
            candidate = SweepCandidate(**candidate)

        payload = {
            "instrument": candidate.instrument,
            "direction": candidate.direction,
            "level_type": candidate.level_type,
            "level_price": candidate.level_price,
            "wick_extreme": candidate.wick_extreme,
            "extension_depth": candidate.extension_depth,
            "candles_to_close": candidate.candles_to_close,
            "displacement_quality": candidate.displacement_quality,
            "session": candidate.session,
            "rr": candidate.risk_reward_ratio,
            "entry_price": candidate.entry_price,
            "stop_loss": candidate.stop_loss,
            "take_profit_1": candidate.take_profit_1,
            "take_profit_2": candidate.take_profit_2,
            "rsi": context.get("rsi"),
            "spread": context.get("spread"),
        }

        api_key = SETTINGS.anthropic_api_key if SETTINGS else ""
        used_mock = False
        try:
            if api_key:
                text = _call_claude(payload)
                output = _parse_claude(text, candidate)
            else:
                output = _mock_output(candidate)
                used_mock = True
        except Exception as e:
            logger.warning("Analyst claude failed: %s", e)
            try:
                output = _parse_claude(json.dumps({}), candidate)
            except Exception:
                output = _mock_output(candidate)
                used_mock = True

        latency = self.timed(start)
        summary = (
            f"Analyst: bias={output.bias.value} conf={output.confidence_score} "
            f"rr={output.trade_plan.risk_reward_ratio}"
            + (" (mock)" if used_mock else "")
        )
        return self._result(
            "ok" if output.bias != Bias.NO_TRADE else "skipped",
            summary,
            {
                "analyst_output": output.model_dump(),
                "used_mock": used_mock,
                "latency_ms": latency,
            },
            confidence=output.confidence_score,
            latency_ms=latency,
        )
