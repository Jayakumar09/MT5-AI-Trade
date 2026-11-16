"""Thread-safe event bus with WebSocket subscriber fan-out."""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Callable

logger = logging.getLogger("quantpilot.events")


class EventBus:
    """Publish/subscribe bus. WebSocket handlers subscribe a coroutine."""

    def __init__(self) -> None:
        self._subs: list[Callable[[dict[str, Any]], None]] = []
        self._lock = __import__("threading").Lock()
        self.history: list[dict[str, Any]] = []

    def subscribe(self, cb: Callable[[dict[str, Any]], None]) -> Callable[[], None]:
        with self._lock:
            self._subs.append(cb)

        def _unsub() -> None:
            with self._lock:
                if cb in self._subs:
                    self._subs.remove(cb)

        return _unsub

    def publish(self, event_type: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        evt = {
            "event_id": str(uuid.uuid4()),
            "type": event_type,
            "timestamp": time.time(),
            "data": data or {},
        }
        self.history.append(evt)
        if len(self.history) > 500:
            self.history = self.history[-500:]
        with self._lock:
            subs = list(self._subs)
        for cb in subs:
            try:
                cb(evt)
            except Exception as e:  # pragma: no cover - subscriber failure must not break publisher
                logger.warning("subscriber error: %s", e)
        return evt

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.history[-limit:]


bus = EventBus()
