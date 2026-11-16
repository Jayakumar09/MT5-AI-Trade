"""MetaTrader 5 bridge.

Only used when DATA_MODE=mt5 and the terminal is reachable. On any failure
we fall back to Demo/Paper mode with a friendly toast (never a stack trace).
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from .models import OrderResult, Position
from .settings import SETTINGS

logger = logging.getLogger("quantpilot.mt5")

# Module-level MT5 handle; None until initialize() succeeds.
_mt5 = None
_connected = False
_last_error = ""
_lock = threading.Lock()


def available() -> bool:
    """Return True if the MetaTrader5 package is importable."""
    try:
        import MetaTrader5  # noqa: F401

        return True
    except Exception:
        return False


def initialize() -> tuple[bool, str]:
    """Initialize MT5 with credentials from .env. Returns (ok, message)."""
    global _mt5, _connected, _last_error
    if SETTINGS is None or SETTINGS.data_mode != "mt5":
        _last_error = "DATA_MODE is not mt5; staying in Demo."
        return False, _last_error
    try:
        import MetaTrader5 as mt5
    except Exception as e:
        _last_error = f"MetaTrader5 package not installed: {e}"
        logger.warning(_last_error)
        return False, _last_error

    try:
        kwargs: dict[str, Any] = {}
        if SETTINGS.mt5_path:
            kwargs["path"] = SETTINGS.mt5_path
        if SETTINGS.mt5_login:
            kwargs["login"] = SETTINGS.mt5_login
            kwargs["password"] = SETTINGS.mt5_password
            kwargs["server"] = SETTINGS.mt5_server
        ok = mt5.initialize(**kwargs)
        if not ok:
            _last_error = f"mt5.initialize failed: {mt5.last_error()}"
            logger.warning(_last_error)
            return False, _last_error
        info = mt5.account_info()
        if info is None:
            _last_error = "account_info() returned None"
            return False, _last_error
        _mt5 = mt5
        _connected = True
        _last_error = ""
        logger.info("MT5 connected: login=%s server=%s", SETTINGS.mt5_login, SETTINGS.mt5_server)
        return True, "connected"
    except Exception as e:
        _last_error = f"MT5 init exception: {e}"
        logger.warning(_last_error)
        return False, _last_error


def health() -> dict[str, Any]:
    """Return a friendly status dict for the UI (never exposes password)."""
    if not available():
        return {"connected": False, "mode": "paper", "reason": "MetaTrader5 package not installed (Windows only)"}
    if not _connected:
        return {"connected": False, "mode": "paper", "reason": _last_error or "not initialized"}
    try:
        ti = _mt5.terminal_info()
        ai = _mt5.account_info()
        return {
            "connected": True,
            "mode": "mt5",
            "login": SETTINGS.mt5_login,
            "server": SETTINGS.mt5_server,
            "balance": getattr(ai, "balance", 0),
            "equity": getattr(ai, "equity", 0),
            "trade_allowed": bool(getattr(ai, "trade_allowed", False)),
            "terminal_trade_allowed": bool(getattr(ti, "trade_allowed", False)),
            "ping": 0,
        }
    except Exception as e:
        return {"connected": False, "mode": "paper", "reason": str(e)}


def symbol_map(instrument: str) -> str | None:
    """Map our canonical symbol name to the broker's name."""
    if not _connected:
        return None
    candidates = [instrument, instrument + "m", instrument.replace("USD", "USD.pro")]
    try:
        syms = _mt5.symbols_get()
        names = {s.name for s in syms}
        for c in candidates:
            if c in names:
                return c
        # fuzzy
        for s in syms:
            if instrument.upper().replace("USD", "") in s.name.upper():
                return s.name
    except Exception as e:
        logger.warning("symbol_map failed: %s", e)
    return None


def _filling_mode(symbol_info) -> int:
    """Pick a filling mode the symbol supports: FOK > IOC > RETURN."""
    for mode in ("FOK", "IOC", "RETURN"):
        if getattr(symbol_info, "filling_mode", None) and mode in str(symbol_info.filling_mode):
            return {"FOK": 0, "IOC": 1, "RETURN": 2}[mode]
    return 0


def place_order(
    instrument: str,
    direction: str,
    volume: float,
    sl: float,
    tp: float,
    signal_id: str,
) -> OrderResult:
    """Send a market order via MT5 after order_check."""
    if not _connected:
        return OrderResult(ok=False, retcode="NOT_CONNECTED", message="MT5 not connected", mode="mt5")
    try:
        sym = symbol_map(instrument)
        if sym is None:
            return OrderResult(ok=False, retcode="SYMBOL_NOT_FOUND", message=f"Symbol {instrument} not found", mode="mt5")
        info = _mt5.symbol_info(sym)
        tick = _mt5.symbol_info_tick(sym)
        if info is None or tick is None:
            return OrderResult(ok=False, retcode="NO_TICK", message="No tick data", mode="mt5")

        order_type = "ORDER_TYPE_BUY" if direction == "BUY" else "ORDER_TYPE_SELL"
        price = tick.ask if direction == "BUY" else tick.bid
        filling = _filling_mode(info)

        request = {
            "action": _mt5.TRADE_ACTION_DEAL,
            "symbol": sym,
            "volume": float(volume),
            "type": getattr(_mt5, order_type),
            "price": price,
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 20,
            "magic": 16112026,
            "comment": f"QuantPilot|{signal_id}",
            "type_time": _mt5.ORDER_TIME_GTC,
            "type_filling": filling,
        }
        check = _mt5.order_check(request)
        if check is None or check.retcode != 10009:
            rc = getattr(check, "retcode", "unknown") if check else "no_check"
            return OrderResult(
                ok=False,
                retcode=str(rc),
                message=f"order_check failed retcode={rc}",
                mode="mt5",
            )
        result = _mt5.order_send(request)
        if result is None or result.retcode != 10009:
            rc = getattr(result, "retcode", "unknown") if result else "no_result"
            return OrderResult(ok=False, retcode=str(rc), message=f"order_send failed retcode={rc}", mode="mt5")
        return OrderResult(
            ok=True,
            ticket=int(getattr(result, "order", 0) or 0),
            retcode=str(getattr(result, "retcode", "")),
            message=f"MT5 order placed ticket={getattr(result, 'order', 0)}",
            fill_price=float(getattr(result, "price", price)),
            volume=float(volume),
            mode="mt5",
        )
    except Exception as e:
        return OrderResult(ok=False, retcode="EXCEPTION", message=str(e), mode="mt5")


def sync_positions() -> list[Position]:
    """Pull open positions from MT5 into our Position model list."""
    if not _connected:
        return []
    try:
        pos_list = _mt5.positions_get()
        out: list[Position] = []
        for p in pos_list or []:
            out.append(
                Position(
                    ticket=int(p.ticket),
                    instrument=p.symbol,
                    direction="BUY" if p.type == 0 else "SELL",
                    volume=float(p.volume),
                    open_price=float(p.price_open),
                    current_price=float(p.price_current),
                    sl=float(p.sl or 0),
                    tp=float(p.tp or 0),
                    open_time=float(p.time),
                    unrealized_pnl=float(p.profit),
                    mode="mt5",
                    magic=int(p.magic),
                )
            )
        return out
    except Exception as e:
        logger.warning("sync_positions failed: %s", e)
        return []


def close_position(ticket: int) -> OrderResult:
    if not _connected:
        return OrderResult(ok=False, retcode="NOT_CONNECTED", message="MT5 not connected", mode="mt5")
    try:
        positions = _mt5.positions_get(ticket=ticket)
        if not positions:
            return OrderResult(ok=False, retcode="NO_POSITION", message=f"No position {ticket}", mode="mt5")
        p = positions[0]
        sym = p.symbol
        info = _mt5.symbol_info(sym)
        tick = _mt5.symbol_info_tick(sym)
        direction = "ORDER_TYPE_SELL" if p.type == 0 else "ORDER_TYPE_BUY"
        price = tick.bid if p.type == 0 else tick.ask
        request = {
            "action": _mt5.TRADE_ACTION_DEAL,
            "symbol": sym,
            "volume": float(p.volume),
            "type": getattr(_mt5, direction),
            "position": int(p.ticket),
            "price": price,
            "deviation": 20,
            "magic": int(p.magic),
            "comment": f"QuantPilot|close|{ticket}",
            "type_time": _mt5.ORDER_TIME_GTC,
            "type_filling": _filling_mode(info),
        }
        check = _mt5.order_check(request)
        if check is None or check.retcode != 10009:
            rc = getattr(check, "retcode", "unknown") if check else "no_check"
            return OrderResult(ok=False, retcode=str(rc), message=f"close check failed {rc}", mode="mt5")
        result = _mt5.order_send(request)
        rc = getattr(result, "retcode", "unknown") if result else "no_result"
        return OrderResult(
            ok=(rc == 10009),
            ticket=ticket,
            retcode=str(rc),
            message=f"Closed {ticket} retcode={rc}",
            fill_price=float(price),
            volume=float(p.volume),
            mode="mt5",
        )
    except Exception as e:
        return OrderResult(ok=False, retcode="EXCEPTION", message=str(e), mode="mt5")


def kill_switch() -> OrderResult:
    """Close all positions with our magic number."""
    if not _connected:
        return OrderResult(ok=False, retcode="NOT_CONNECTED", message="MT5 not connected", mode="mt5")
    try:
        positions = _mt5.positions_get()
        closed = 0
        for p in positions or []:
            if int(p.magic) == 16112026:
                close_position(int(p.ticket))
                closed += 1
        return OrderResult(ok=True, retcode="KILL_SWITCH", message=f"Closed {closed} positions", mode="mt5")
    except Exception as e:
        return OrderResult(ok=False, retcode="EXCEPTION", message=str(e), mode="mt5")


def send_test_order() -> OrderResult:
    """Place minimum lot on demo then close it immediately."""
    if not _connected:
        return OrderResult(ok=False, retcode="NOT_CONNECTED", message="MT5 not connected", mode="mt5")
    res = place_order("XAUUSD", "BUY", 0.01, 0.0, 0.0, "TEST")
    if res.ok and res.ticket:
        time.sleep(0.5)
        close_position(res.ticket)
    return res


def heartbeat() -> None:
    """Background loop: check terminal every 10s; disable on failure."""
    global _connected
    while True:
        if _connected:
            try:
                ti = _mt5.terminal_info()
                ai = _mt5.account_info()
                if ti is None or ai is None or not getattr(ai, "trade_allowed", False):
                    _connected = False
                    _last_error = "terminal or account not trade-allowed"
                    logger.warning("MT5 heartbeat failed; falling back to paper")
            except Exception as e:
                _connected = False
                _last_error = str(e)
                logger.warning("MT5 heartbeat exception: %s", e)
        time.sleep(10)


def start_heartbeat() -> None:
    t = threading.Thread(target=heartbeat, daemon=True)
    t.start()
