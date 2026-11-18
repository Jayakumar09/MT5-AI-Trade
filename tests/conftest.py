"""pytest bootstrap for QUANT PILOT backend tests."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

# Allow `from backend.strategy import ...` and `from backend.core.risk import ...`
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))