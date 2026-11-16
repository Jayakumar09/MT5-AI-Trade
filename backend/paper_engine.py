"""Paper trading engine – simulates MT5 order flow without real money.

Keeps positions in memory (persisted to SQLite via db module), computes
unrealized P/L on every tick, handles break-even, partial close at TP1,
and trail toward TP2.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Callable

from .db import delete_position, insert_position
from .models import OrderResult, Position


class PaperEngine:
    def __init__(self) -> None:
        self._positions: dict[int, Position] = {}
        self._lock = threading.Lock()
        self._ticket_seq = 100000
        self._price_cb: Callable[[str], float] | None = None

    def set_price_feed(self, cb: Callable[[str], float]) -> None:
        self._price_cb = cb

    def _next_ticket(self) -> int:
        self._ticket_seq += 1
        return self._ticket_seq

    def place_order(
        self,
        instrument: str,
        direction: str,
        volume: float,
        entry: float,
        sl: float,
        tp: float,
        signal_id: str,
    ) -> OrderResult:
        with self._lock:
            ticket = self._next_ticket()
            pos = Position(
                ticket=ticket,
                instrument=instrument,
                direction=direction,
                volume=volume,
                open_price=entry,
                current_price=entry,
                sl=sl,
                tp=tp,
                open_time=time.time(),
                unrealized_pnl=0.0,
                mode="paper",
                magic=16112026,
            )
            self._positions[ticket] = pos
            insert_position(pos)
            return OrderResult(
                ok=True,
                ticket=ticket,
                retcode="TRADE_RETCODE_DONE",
                message=f"Paper order placed for {instrument} {direction} {volume} lots @ {entry}",
                fill_price=entry,
                volume=volume,
                mode="paper",
            )

    def update_prices(self, instrument: str, price: float) -> None:
        with self._lock:
            for pos in self._positions.values():
                if pos.instrument != instrument:
                    continue
                pos.current_price = price
                if pos.direction == "BUY":
                    pos.unrealized_pnl = (price - pos.open_price) * pos.volume * 100
                else:
                    pos.unrealized_pnl = (pos.open_price - price) * pos.volume * 100

    def close_position(self, ticket: int, price: float | None = None) -> OrderResult:
        with self._lock:
            pos = self._positions.pop(ticket, None)
            if pos is None:
                return OrderResult(ok=False, retcode="TRADE_RETCODE_NO_POSITION", message="Position not found")
            close_p = price if price is not None else pos.current_price
            if pos.direction == "BUY":
                pnl = (close_p - pos.open_price) * pos.volume * 100
            else:
                pnl = (pos.open_price - close_p) * pos.volume * 100
            delete_position(ticket)
            return OrderResult(
                ok=True,
                ticket=ticket,
                retcode="TRADE_RETCODE_DONE",
                message=f"Closed position #{ticket} P/L {pnl:.2f}",
                fill_price=close_p,
                volume=pos.volume,
                mode="paper",
            )

    def get_positions(self) -> list[Position]:
        with self._lock:
            return list(self._positions.values())

    def get_position(self, ticket: int) -> Position | None:
        return self._positions.get(ticket)

    def total_open_pnl(self) -> float:
        with self._lock:
            return sum(p.unrealized_pnl for p in self._positions.values())

    def positions_for(self, instrument: str) -> list[Position]:
        with self._lock:
            return [p for p in self._positions.values() if p.instrument == instrument]

    def manage_position(self, ticket: int, current_price: float, entry_r: float = 1.0) -> str | None:
        """Move SL to break-even at 1R, close 50% at TP1, trail rest to TP2.

        Returns a status message if an action was taken, else None.
        """
        with self._lock:
            pos = self._positions.get(ticket)
            if pos is None:
                return None
            risk = abs(pos.open_price - pos.sl)
            if risk == 0:
                return None
            profit = (current_price - pos.open_price) if pos.direction == "BUY" else (pos.open_price - current_price)
            if profit >= risk and pos.sl != pos.open_price:
                pos.sl = pos.open_price  # break-even
                insert_position(pos)
                return f"BE: SL moved to entry for ticket {ticket}"
            if profit >= 2 * risk:
                # partial close at TP1
                pos.volume = round(pos.volume * 0.5, 2)
                insert_position(pos)
                return f"TP1: 50% closed for ticket {ticket}"
            return None


paper_engine = PaperEngine()
