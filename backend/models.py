"""Pydantic data models for QUANT PILOT.

Every agent result, trade, and journal entry is validated through these
schemas so the LLM output can never leak unstructured text into the system.
"""
from __future__ import annotations

import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentStatus(str, Enum):
    OK = "ok"
    VETO = "veto"
    SKIPPED = "skipped"
    ERROR = "error"
    NO_DATA = "no_data"


class AgentResult(BaseModel):
    """Uniform return type for every agent's run(context) -> AgentResult."""

    model_config = ConfigDict(extra="allow")

    agent: str
    status: AgentStatus
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    confidence: int = 0
    timestamp: float = Field(default_factory=time.time)
    latency_ms: float = 0.0


class Bias(str, Enum):
    BULLISH_SWEEP_LONG = "BULLISH_SWEEP_LONG"
    BEARISH_SWEEP_SHORT = "BEARISH_SWEEP_SHORT"
    NO_TRADE = "NO_TRADE"


class SweepDetails(BaseModel):
    instrument: str
    level_type: str  # PDH / PDL / ASIAN_HIGH / ASIAN_LOW / SWING_HIGH / SWING_LOW / EQUAL_HIGHS / EQUAL_LOWS
    level_price: float
    extension_depth: float
    displacement_quality: float  # 0..1
    candles_to_close: int
    wick_extreme: float


class TradePlan(BaseModel):
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    risk_reward_ratio: float

    @field_validator("risk_reward_ratio")
    @classmethod
    def _rr_check(cls, v: float) -> float:
        if v < 0:
            raise ValueError("risk_reward_ratio must be non-negative")
        return v


class AnalystOutput(BaseModel):
    """Strict JSON the Analyst agent must produce. Validated by Pydantic."""

    instrument: str
    bias: Bias
    confidence_score: int = Field(ge=1, le=10)
    htf_level_targeted: str
    sweep_details: SweepDetails
    trade_plan: TradePlan
    reasoning: str = Field(max_length=400)
    invalidation_conditions: str = Field(max_length=400)


class Signal(BaseModel):
    """An approved trade signal ready for execution."""

    model_config = ConfigDict(extra="allow")

    signal_id: str
    instrument: str
    bias: str
    direction: str  # BUY / SELL
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    risk_reward_ratio: float
    confidence: int
    lot_size: float
    risk_amount: float
    created_at: float = Field(default_factory=time.time)
    source: str = "analyst"
    trace: list[str] = Field(default_factory=list)
    status: str = "approved"  # approved | vetoed | placed | closed


class OrderResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    ok: bool
    ticket: int | None = None
    retcode: str = ""
    message: str = ""
    fill_price: float | None = None
    volume: float | None = None
    mode: str = "paper"


class Position(BaseModel):
    model_config = ConfigDict(extra="allow")

    ticket: int
    instrument: str
    direction: str
    volume: float
    open_price: float
    current_price: float
    sl: float
    tp: float
    open_time: float = Field(default_factory=time.time)
    unrealized_pnl: float = 0.0
    mode: str = "paper"
    magic: int = 0


class Candle(BaseModel):
    """OHLCV bar."""

    time: float
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class JournalEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    entry_id: str
    timestamp: float = Field(default_factory=time.time)
    event: str  # signal_taken | vetoed | skipped | placed | closed | review | error
    instrument: str = ""
    agent: str = ""
    summary: str = ""
    detail: dict[str, Any] = Field(default_factory=dict)


class AccountState(BaseModel):
    model_config = ConfigDict(extra="allow")

    balance: float = 0.0
    equity: float = 0.0
    margin_used: float = 0.0
    free_margin: float = 0.0
    day_pnl: float = 0.0
    drawdown_pct: float = 0.0
    open_risk: float = 0.0
    mode: str = "paper"
    peak_equity: float = 0.0


class SweepCandidate(BaseModel):
    """Raw candidate produced by the Hunter before the Analyst refines it."""

    instrument: str
    direction: str  # long | short
    level_type: str
    level_price: float
    wick_extreme: float
    extension_depth: float
    candles_to_close: int
    displacement_quality: float
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    risk_reward_ratio: float
    session: str
    timestamp: float = Field(default_factory=time.time)