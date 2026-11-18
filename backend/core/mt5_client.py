"""MetaTrader5 execution bridge.

On non-Windows or when the MetaTrader5 package / terminal is unavailable, the
app stays in Demo/Paper mode. All MT5 interaction is guarded behind try/except
and the `MetaTrader5` import is optional.
"""

from __future__ import annotations

import os
import time
from typing import Any, Optional

try:  # optional dependency — Windows only
    import MetaTrader5 as mt5  # type: ignore
except Exception:  # pragma: no cover - environment dependent
    mt5 = None  # type: ignore


def normalize_volume(volume: float, volume_min: float, volume_step: float, volume_max: float) -> float:
    """Normalize a requested volume to broker min/step/max constraints."""
    if volume_step <= 0:
        volume_step = 0.01
    normalized = round(round(volume / volume_step) * volume_step, 8)
    normalized = max(volume_min, min(normalized, volume_max))
    return round(normalized, 8)


def validate_sl_tp(
    symbol: str,
    direction: str,
    entry: float,
    sl: float,
    tp: float,
    stops_level_points: int,
    point: float,
) -> tuple[bool, str]:
    """Validate SL/TP against the symbol's trade_stops_level."""
    if stops_level_points < 0:
        stops_level_points = 0
    min_dist = stops_level_points * point
    if min_dist <= 0:
        min_dist = point
    if direction.upper() in ("BUY", "LONG"):
        if sl >= entry:
            return False, "BUY stop loss must be below entry"
        if tp <= entry:
            return False, "BUY take profit must be above entry"
        if entry - sl < min_dist:
            return False, f"SL too close: min distance {min_dist:.5f}"
        if tp - entry < min_dist:
            return False, f"TP too close: min distance {min_dist:.5f}"
    else:
        if sl <= entry:
            return False, "SELL stop loss must be above entry"
        if tp >= entry:
            return False, "SELL take profit must be below entry"
        if sl - entry < min_dist:
            return False, f"SL too close: min distance {min_dist:.5f}"
        if entry - tp < min_dist:
            return False, f"TP too close: min distance {min_dist:.5f}"
    return True, "OK"


def fill_type_preference(symbol_info: Any) -> int:
    """Pick a filling mode the symbol supports (FOK > IOC > RETURN)."""
    filling = getattr(symbol_info, "filling_mode", 0)
    return 2 if filling & 2 else (1 if filling & 1 else 0)  # 2=IOC/FOK style, 1=RETURN fallback


# Retcode table — human readable messages (subset, full mapping kept small)
RETCODE_MESSAGES = {
    10004: "Requote — price moved",
    10006: "Order rejected — check stops/margin",
    10007: "Request canceled by trader",
    10009: "Done — request completed",
    10010: "Done with warning",
    10013: "Invalid request",
    10015: "Invalid volume",
    10016: "Invalid stop — SL/TP violate stops level",
    10019: "No money — insufficient margin",
    10018: "Market closed",
    10021: "No connection with trade server",
    10030: "Invalid order type for symbol",
    10031: "Invalid expiration",
    10032: "Too many requests / rate limited",
    10033: "Invalid order setup",
    10034: "Invalid account",
}


def retcode_to_message(retcode: int) -> str:
    return RETCODE_MESSAGES.get(int(retcode), f"Unknown retcode {retcode}")


class MT5Client:
    """Thin wrapper over the MetaTrader5 Python API with demo-only safety."""

    MAGIC_DEFAULT = 20260101

    def __init__(self, env: Optional[dict] = None) -> None:
        self.env = env or dict(os.environ)
        self.available = mt5 is not None
        self.connected = False
        self.account_mode = "UNKNOWN"
        self.last_error: Optional[str] = None
        self.trade_allowed = False

    # ── connection ───────────────────────────────────────────────────────────
    def connect(self) -> bool:
        if not self.available:
            self.last_error = "MetaTrader5 package unavailable (non-Windows or not installed)"
            return False
        try:
            ok = mt5.initialize(
                path=self.env.get("MT5_PATH") or None,
                login=int(self.env.get("MT5_LOGIN", "0") or 0),
                password=self.env.get("MT5_PASSWORD") or None,
                server=self.env.get("MT5_SERVER") or None,
            )
            if not ok:
                self.last_error = f"mt5.initialize failed: {mt5.last_error()}"
                return False
            info = mt5.account_info()
            term = mt5.terminal_info()
            self.connected = True
            self.account_mode = "DEMO" if (info and getattr(info, "trade_mode", 0) == 0) else "REAL"
            self.trade_allowed = bool(term and getattr(term, "trade_allowed", False))
            return True
        except Exception as exc:  # pragma: no cover
            self.last_error = f"MT5 connection error: {exc}"
            return False

    def status(self) -> dict:
        return {
            "available": self.available,
            "connected": self.connected,
            "account_mode": self.account_mode,
            "trade_allowed": self.trade_allowed,
            "last_error": self.last_error,
            "mt5_login_configured": bool(self.env.get("MT5_LOGIN")),
        }

    # ── symbol/account helpers ──────────────────────────────────────────────
    def account_info(self):  # pragma: no cover - needs terminal
        if not self.connected or mt5 is None:
            return None
        return mt5.account_info()

    def symbol_candidates(self, want: str) -> list[str]:  # pragma: no cover - needs terminal
        if mt5 is None:
            return []
        try:
            symbols = mt5.symbols_get()
            names = [s.name for s in symbols] if symbols else []
            want_u = want.upper()
            return [n for n in names if want_u[:3] in n.upper()]
        except Exception:
            return []

    def tick(self, symbol: str):  # pragma: no cover - needs terminal
        if mt5 is None:
            return None
        try:
            return mt5.symbol_info_tick(symbol)
        except Exception:
            return None

    def symbol_info(self, symbol: str):  # pragma: no cover - needs terminal
        if mt5 is None:
            return None
        try:
            return mt5.symbol_info(symbol)
        except Exception:
            return None

    # ── order flow ───────────────────────────────────────────────────────────
    def order_check(self, request: dict) -> Any:  # pragma: no cover - needs terminal
        if mt5 is None:
            return None
        return mt5.order_check(request)

    def order_send(self, request: dict) -> Any:  # pragma: no cover - needs terminal
        if mt5 is None:
            return None
        return mt5.order_send(request)

    def build_market_request(
        self,
        symbol: str,
        side: str,
        volume: float,
        sl: float,
        tp: float,
        magic: int,
        comment: str,
        deviation: int = 20,
    ) -> dict:
        """Build an mt5.order_send request dict (TRADE_ACTION_DEAL, market order)."""
        info = self.symbol_info(symbol)
        tick = self.tick(symbol)
        filling = fill_type_preference(info) if info is not None else 0
        price = (tick.ask if side.upper() in ("BUY", "LONG") else tick.bid) if tick else 0.0
        order_type = 0 if side.upper() in ("BUY", "LONG") else 1  # ORDER_TYPE_BUY / ORDER_TYPE_SELL
        magic_default = int(self.env.get("MT5_MAGIC", str(self.MAGIC_DEFAULT)))
        return {
            "action": 1,  # TRADE_ACTION_DEAL
            "symbol": symbol,
            "volume": float(volume),
            "type": order_type,
            "price": float(price),
            "sl": float(sl),
            "tp": float(tp),
            "deviation": int(deviation),
            "magic": int(magic or magic_default),
            "comment": comment[:31],
            "type_filling": filling,
        }

    def disconnect(self) -> None:  # pragma: no cover - needs terminal
        if mt5 is not None and self.connected:
            try:
                mt5.shutdown()
            except Exception:
                pass
        self.connected = False


__all__ = [
    "MT5Client",
    "normalize_volume",
    "validate_sl_tp",
    "fill_type_preference",
    "retcode_to_message",
    "RETCODE_MESSAGES",
]