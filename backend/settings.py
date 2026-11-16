"""Central configuration for QUANT PILOT.

All environment driven settings are loaded here exactly once. No secrets are
ever logged; the MT5 password is redacted in every representation.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

logger = logging.getLogger("quantpilot.settings")


def _env_bool(key: str, default: bool = False) -> bool:
    """Parse a boolean environment variable tolerantly."""
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "y"}


def _env_float(key: str, default: float) -> float:
    """Parse a float environment variable, falling back on malformed input."""
    try:
        return float(os.getenv(key, default))
    except (TypeError, ValueError):
        logger.warning("Invalid float for %s, using default %s", key, default)
        return default


@dataclass
class Settings:
    """Runtime configuration."""

    app_name: str = "QUANT PILOT"
    author: str = "Sumedh Kumar"
    author_site: str = "SUMEDHHKUMAR.ai"

    demo_mode: bool = True
    data_mode: str = "demo"  # demo | mt5

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"

    mt5_mode: str = "demo_only"  # demo_only | live
    mt5_login: int = 0
    mt5_password: str = field(default="", repr=False)
    mt5_server: str = ""
    mt5_path: str = ""
    mt5_magic: int = 16112026

    host: str = "127.0.0.1"
    port: int = 8000
    db_path: str = str(ROOT / "data" / "quantpilot.db")

    default_instruments: tuple[str, ...] = ("XAUUSD", "BTCUSD")
    max_cycle_seconds: int = 20

    # Risk defaults (all editable at runtime through Settings API)
    risk_per_trade: float = 0.01
    max_risk_per_trade: float = 0.02
    daily_drawdown_kill: float = 0.04
    max_open_trades: int = 2
    min_confidence: int = 7
    min_rr: float = 2.0
    cooldown_minutes: int = 30
    xau_spread_limit: float = 35.0
    btc_spread_limit: float = 60.0


def load_settings() -> Settings | None:
    """Build settings from environment variables."""
    mode = os.getenv("DATA_MODE", "demo").strip().lower()
    s = Settings(
        demo_mode=_env_bool("DEMO_MODE", True) or mode != "mt5",
        data_mode=mode,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5").strip(),
        mt5_mode=os.getenv("MT5_MODE", "demo_only").strip().lower(),
        mt5_login=int(_env_float("MT5_LOGIN", 0)),
        mt5_password=os.getenv("MT5_PASSWORD", ""),
        mt5_server=os.getenv("MT5_SERVER", ""),
        mt5_path=os.getenv("MT5_PATH", ""),
        mt5_magic=int(_env_float("MT5_MAGIC", 16112026)),
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(_env_float("PORT", 8000)),
        risk_per_trade=_env_float("RISK_PER_TRADE", 0.01),
        max_risk_per_trade=_env_float("MAX_RISK_PER_TRADE", 0.02),
    )
    Path(s.db_path).parent.mkdir(parents=True, exist_ok=True)
    return s


def safe_settings(settings: Settings):
    """Return a settings object with secrets removed for API exposure."""
    return {
        "app_name": settings.app_name,
        "data_mode": settings.data_mode,
        "demo_mode": settings.demo_mode,
        "mt5_mode": settings.mt5_mode,
        "mt5_login": settings.mt5_login,
        "mt5_server": settings.mt5_server,
        "mt5_password_set": bool(_ENV_PASSWORD),
        "mt5_path": settings.mt5_path,
        "mt5_magic": settings.mt5_magic,
        "anthropic_model": settings.anthropic_model,
        "anthropic_key_set": bool(settings.anthropic_api_key),
        "default_instruments": list(settings.default_instruments),
    }


_ENV_PASSWORD = os.getenv("MT5_PASSWORD", "")

SETTINGS: Settings | None = load_settings()
