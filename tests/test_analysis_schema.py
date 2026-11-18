"""Unit tests for the Analyst JSON schema validation (backend/core/models.py)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.core.models import AnalysisDecision

VALID = {
    "instrument": "XAUUSD",
    "bias": "BULLISH_SWEEP_LONG",
    "confidence_score": 8,
    "htf_level_targeted": "EQUAL_LOW @ 2370.0",
    "sweep_details": {"extension_depth": 1.6, "displacement_quality": 1.4},
    "trade_plan": {
        "entry_price": 2375.8,
        "stop_loss": 2368.0,
        "take_profit_1": 2391.4,
        "take_profit_2": 2405.0,
        "risk_reward_ratio": 2.0,
    },
    "reasoning": "Sweep below equal lows with displacement close back inside. Session support holds.",
    "invalidation_conditions": ["Close back below the swept level", "News filter triggered"],
}


def test_valid_analysis_decision_parses():
    d = AnalysisDecision.model_validate(VALID)
    assert d.bias == "BULLISH_SWEEP_LONG"
    assert d.confidence_score == 8


def test_invalid_bias_rejected():
    bad = {**VALID, "bias": "SUPER_BULLISH"}
    with pytest.raises(ValidationError):
        AnalysisDecision.model_validate(bad)


def test_confidence_score_bounds():
    with pytest.raises(ValidationError):
        AnalysisDecision.model_validate({**VALID, "confidence_score": 11})
    with pytest.raises(ValidationError):
        AnalysisDecision.model_validate({**VALID, "confidence_score": 0})


def test_reasoning_max_length_enforced():
    with pytest.raises(ValidationError):
        AnalysisDecision.model_validate({**VALID, "reasoning": "x" * 600})


def test_missing_trade_plan_field_rejected():
    bad = dict(VALID)
    bad["trade_plan"] = {k: v for k, v in VALID["trade_plan"].items() if k != "stop_loss"}
    with pytest.raises(ValidationError):
        AnalysisDecision.model_validate(bad)