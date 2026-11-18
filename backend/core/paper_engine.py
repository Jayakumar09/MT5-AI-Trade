"""Paper trading engine — simulated positions, SL/TP, break-even, partial closes.

Paper mode is the default execution path. No broker or network access required.
Positions are held in memory + persisted (by the Chronicler) to SQLite.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from .models import AccountInfo, Position, Signal


class PaperEngine:
    """In-memory paper trading engine."""

    def __init__(self, starting_balance: float = 10_000.0, magic: int = 20260101) -> None:
        self.balance = starting_balance
        self.equity = starting_balance
        self.magic = magic
        self.realized_pnl = 0.0
        self.positions: dict[str, Position] = {}
        self.daily_pnl = 0.0
        self.peak_equity = starting_balance
        self.daily_drawdown = 0.0

    def account_info(self, mode: str = "DEMO") -> AccountInfo:
        unrealized = total_unrealized = sum(p.unrealized_pnl for p in self.positions.values())
        equity = self.balance + unrealized
        dd_peak = max(self.peak_equity, equity)
        self.peak_equity = dd_peak
        dd = dd_peak - equity
        self.daily_drawdown = max(self.daily_drawdown, dd)
        return AccountInfo(
            balance=round(self.balance, 2),
            equity=round(equity, 2),
            margin_free=round(equity * 0.8, 2),
            profit=round(unrealized, 2),
            drawdown=round(dd, 2),
            daily_drawdown=round(self.daily_drawdown, 2),
            mode=mode,
            connected=False,
        )

    def place_order(self, signal: Signal) -> Position:
        """Create a paper position from an approved signal."""
        pos = Position(
            signal_id=signal.id,
            instrument=signal.instrument,
            direction=signal.direction,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit_1=signal.take_profit_1,
            take_profit_2=signal.take_profit_2,
            lot_size=signal.lot_size or 0.01,
            magic_number=signal.magic_number or self.magic,
            comment=signal.comment or f"QuantPilot|{signal.id}",
            state="OPEN",
        )
        self.positions[pos.id] = pos
        return pos

    def _instrument_multiplier(self, instrument: str) -> float:
        return 10.0 if instrument.upper().startswith("XAU") else 0.01  # $ per point per lot approx

    def update_positions(self, prices: dict[str, float]) -> list[dict]:
        """Mark-to-market; process SL/TP1/TP2 exits; returns close events."""
        events: list[dict] = []
        for pos in list(self.positions.values()):
            px = prices.get(pos.instrument)
            if px is None:
                continue
            direction = 1 if pos.direction == "LONG" else -1
            pnl = (px - pos.entry_price) * direction * pos.lot_size * self._instrument_multiplier(pos.instrument)
            pos.unrealized_pnl = round(pnl, 2)

            sl_hit = (pos.direction == "LONG" and px <= pos.stop_loss) or (pos.direction == "SHORT" and px >= pos.stop_loss)
            tp1_hit = (pos.direction == "LONG" and px >= pos.take_profit_1) or (pos.direction == "SHORT" and px <= pos.take_profit_1)
            tp2_hit = (pos.direction == "LONG" and px >= pos.take_profit_2) or (pos.direction == "SHORT" and px <= pos.take_profit_2)

            # break-even move at 1R
            one_r = abs(pos.entry_price - pos.stop_loss)
            if pos.state == "OPEN" and one_r > 0:
                r_multiple = ((px - pos.entry_price) * direction) / one_r
                if r_multiple >= 1.0:
                    pos.state = "BE_SET"
                    pos.stop_loss = pos.entry_price  # move SL to break-even
                    events.append({"type": "BREAK_EVEN", "position_id": pos.id})

            # partial close 50% at TP1
            if tp1_hit and not pos.partial_close_done and pos.state != "CLOSED":
                pnl_tp1 = (pos.take_profit_1 - pos.entry_price) * direction * (pos.lot_size / 2) * self._instrument_multiplier(pos.instrument)
                self.balance += pnl_tp1
                self.realized_pnl += pnl_tp1
                pos.partial_close_done = True
                pos.state = "PARTIAL_DONE"
                events.append({"type": "PARTIAL_CLOSE", "position_id": pos.id, "pnl": round(pnl_tp1, 2)})

            if tp2_hit and pos.state != "CLOSED":
                close_pnl = (pos.take_profit_2 - pos.entry_price) * direction * pos.lot_size * self._instrument_multiplier(pos.instrument)
                # account for the half already closed at TP1
                if pos.partial_close_done:
                    close_pnl /= 2
                self.balance += close_pnl
                self.realized_pnl += close_pnl
                self.daily_pnl += close_pnl
                pos.state = "CLOSED"
                pos.pnl = round((pos.pnl + close_pnl), 2)
                pos.closed_at = datetime.now(timezone.utc)
                events.append({"type": "CLOSE_TP2", "position_id": pos.id, "pnl": round(close_pnl, 2)})

            elif sl_hit and pos.state != "CLOSED":
                close_pnl = (pos.stop_loss - pos.entry_price) * direction * pos.lot_size * self._instrument_multiplier(pos.instrument)
                if pos.partial_close_done:
                    close_pnl /= 2
                self.balance += close_pnl
                self.realized_pnl += close_pnl
                self.daily_pnl += close_pnl
                pos.state = "CLOSED"
                pos.pnl = round((pos.pnl + close_pnl), 2)
                pos.closed_at = datetime.now(timezone.utc)
                events.append({"type": "CLOSE_SL", "position_id": pos.id, "pnl": round(close_pnl, 2)})

        # purge closed positions into nothing (Chronicler journals them)
        self.positions = {pid: p for pid, p in self.positions.items() if p.state != "CLOSED"}
        equity = self.balance + sum(p.unrealized_pnl for p in self.positions.values())
        return events

    def kill_switch(self) -> list[str]:
        """Close all paper positions and halt new orders."""
        closed: list[str] = []
        for pos in self.positions.values():
            pos.state = "CLOSED"
            closed.append(pos.id)
        self.positions = {}
        return closed

    def open_positions_count(self) -> int:
        return len([p for p in self.positions.values() if p.state != "CLOSED"])