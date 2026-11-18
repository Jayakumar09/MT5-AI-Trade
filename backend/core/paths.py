"""Storage rule (§3.5): everything lives under H:\\MT5-AI-Trade."""

from pathlib import Path

ROOT = Path(r"H:\MT5-AI-Trade")
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "quantpilot.db"
LOG_DIR = ROOT / "logs" / "app"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)