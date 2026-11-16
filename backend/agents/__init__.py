"""Agent registry for QUANT PILOT."""
from __future__ import annotations

from .analyst import AnalystAgent
from .base import BaseAgent
from .cartographer import CartographerAgent
from .chronicler import ChroniclerAgent
from .executioner import ExecutionerAgent
from .guardian import GuardianAgent
from .hunter import HunterAgent
from .scout import ScoutAgent

AGENTS: list[type[BaseAgent]] = [
    ScoutAgent,
    CartographerAgent,
    HunterAgent,
    AnalystAgent,
    GuardianAgent,
    ExecutionerAgent,
    ChroniclerAgent,
]

AGENT_ORDER = [a.__name__.replace("Agent", "").upper() for a in AGENTS]

__all__ = ["AGENTS", "AGENT_ORDER", "BaseAgent"]
