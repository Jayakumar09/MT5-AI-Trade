"""Core Pydantic models for QUANT PILOT trading application."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict


class Candle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ts: datetime = Field(description="candle open time (UTC)")
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class Direction(str):
    """Direction alias to keep backwards compatibility with quantpilot_v2 enums."""
    LONG = "LONG"
    SHORT = "SHORT"


class SignalStatus(str):
    CANDIDATE = "CANDIDATE"
    APPROVED = "APPROVED"
    VETOED = "VETOED"
    EXECUTED = "EXECUTED"
    NO_TRADE = "NO_TRADE"


class TradePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    risk_reward_ratio: float


class AgentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str  # CANDIDATE | APPROVED | VETOED | EXECUTED | NO_TRADE | SKIPPED
    summary: str
    data: dict = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AnalysisDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instrument: str
    bias: Literal["BULLISH_SWEEP_LONG", "BEARISH_SWEEP_SHORT", "NO_TRADE"]
    confidence_score: int = Field(ge=1, le=10)
    htf_level_targeted: str
    sweep_details: dict
    trade_plan: TradePlan
    reasoning: str = Field(max_length=500)
    invalidation_conditions: list[str] = Field(default_factory=list)


class Signal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"sig-{uuid4().hex[:8]}")
    instrument: str
    direction: Literal["LONG", "SHORT"]
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    risk_reward_ratio: float
    confidence: float
    status: str = SignalStatus.CANDIDATE
    agent_trace: list[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reason: str = ""
    slippage_points: int = 0
    lot_size: float = 0.0
    magic_number: int = 20260101
    comment: str = ""


class Position(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"pos-{uuid4().hex[:8]}")
    signal_id: str
    instrument: str
    direction: Literal["LONG", "SHORT"]
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    lot_size: float
    magic_number: int = 20260101
    comment: str = ""
    state: str = "OPEN"
    pnl: float = 0.0
    unrealized_pnl: float = 0.0
    opened_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    partial_close_done: bool = False


class AccountInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    balance: float = 10000.0
    equity: float = 10000.0
    margin_free: float = 10000.0
    profit: float = 0.0
    drawdown: float = 0.0
    daily_drawdown: float = 0.0
    mode: str = "DEMO"
    connected: bool = False


class MarketTick(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    bid: float
    ask: float
    spread_points: int
    ts: datetime = Field(default_factory=datetime.utcnow)


class OrchestrationCycle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cycle_id: str = Field(default_factory=lambda: f"cyc-{uuid4().hex[:8]}")
    instrument: str
    candle: Optional[Candle] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
