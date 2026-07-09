"""In-process event bus for WebSocket fan-out.

Producers (worker loops, task manager) call :meth:`EventBus.publish` from
arbitrary threads. The WebSocket endpoint registers an :class:`asyncio.Queue`
via :meth:`subscribe_async`; the loop is captured at subscribe time so a
worker-thread publish can still enqueue thread-safely via
``loop.call_soon_threadsafe``.
"""

from __future__ import annotations

import asyncio
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional, Tuple


@dataclass
class Event:
    type: str
    payload: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().astimezone().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "timestamp": self.timestamp, "payload": self.payload}

    @classmethod
    def build(cls, event_type: str, **payload: Any) -> "Event":
        return cls(type=event_type, payload=payload)


# Canonical event type names (spec section 4.5).
INSTANCE_STATUS = "instance_status"
TASK_STATUS = "task_status"
WORKER_LOG = "worker_log"
SCREENSHOT_UPDATED = "screenshot_updated"
ERROR = "error"


SyncSubscriber = Callable[[Event], None]


def _safe_put(queue: "asyncio.Queue", event: Event) -> None:
    try:
        queue.put_nowait(event)
    except asyncio.QueueFull:  # noqa: PERF203 - slow consumer; drop oldest-ish
        pass


class EventBus:
    """A small fan-out bus with both sync and async sinks."""

    def __init__(self, history_size: int = 200) -> None:
        self._lock = threading.Lock()
        self._sync_subscribers: list[SyncSubscriber] = []
        self._async_subs: list[Tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = []
        self._recent: deque[Event] = deque(maxlen=history_size)

    # --- publishing -----------------------------------------------------

    def publish(self, event_type: str, **payload: Any) -> Event:
        event = Event.build(event_type, **payload)
        with self._lock:
            self._recent.append(event)
            sync_subs = list(self._sync_subscribers)
            async_subs = list(self._async_subs)
        # Sync callbacks (run in the publishing thread; must be cheap).
        for sub in sync_subs:
            try:
                sub(event)
            except Exception:  # noqa: BLE001 - a bad listener must not break the bus
                pass
        # Async sinks: enqueue from the captured loop, thread-safe.
        for loop, queue in async_subs:
            try:
                loop.call_soon_threadsafe(_safe_put, queue, event)
            except Exception:  # noqa: BLE001 - loop closed, etc.
                pass
        return event

    # --- subscriptions --------------------------------------------------

    def subscribe_sync(self, callback: SyncSubscriber) -> None:
        with self._lock:
            self._sync_subscribers.append(callback)

    def unsubscribe_sync(self, callback: SyncSubscriber) -> None:
        with self._lock:
            if callback in self._sync_subscribers:
                self._sync_subscribers.remove(callback)

    def subscribe_async(self) -> "asyncio.Queue":
        """Subscribe from within a running event loop. Returns a Queue."""
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue(maxsize=500)
        with self._lock:
            self._async_subs.append((loop, queue))
        return queue

    def unsubscribe_async(self, queue: "asyncio.Queue") -> None:
        with self._lock:
            self._async_subs = [(l, q) for (l, q) in self._async_subs if q is not queue]

    # --- history --------------------------------------------------------

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._recent)
        return [e.to_dict() for e in items[-limit:]]


# Singleton bus used app-wide.
bus = EventBus()
