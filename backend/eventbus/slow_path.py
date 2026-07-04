"""Slow Path bus for asynchronous telemetry and audit events."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import TypeAlias

from .events import SlowPathEvent, SlowPathEventType

SyncSlowPathHandler: TypeAlias = Callable[[SlowPathEvent], None]
AsyncSlowPathHandler: TypeAlias = Callable[[SlowPathEvent], Awaitable[None]]
SlowPathHandler: TypeAlias = SyncSlowPathHandler | AsyncSlowPathHandler


class SlowPathBus:
    """Async bus for telemetry that must not block the core execution path."""

    def __init__(self) -> None:
        self._handlers: dict[SlowPathEventType, list[SlowPathHandler]] = defaultdict(list)
        self._failure_handler: Callable[[SlowPathEvent, Exception], None] | None = None
        self._history: list[SlowPathEvent] = []
        self._background_tasks: set[asyncio.Task] = set()

    @property
    def history(self) -> list[SlowPathEvent]:
        return list(self._history)

    def subscribe(self, event_type: SlowPathEventType, handler: SlowPathHandler) -> None:
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: SlowPathEventType, handler: SlowPathHandler) -> None:
        if handler in self._handlers.get(event_type, []):
            self._handlers[event_type].remove(handler)

    def on_failure(self, handler: Callable[[SlowPathEvent, Exception], None]) -> None:
        self._failure_handler = handler

    def publish(self, event: SlowPathEvent) -> None:
        self._history.append(event)
        handlers = self._handlers.get(event.event_type, [])
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self.publish_and_wait(event, record_history=False))
            return

        for handler in handlers:
            task = loop.create_task(self._run_handler(handler, event))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    async def publish_and_wait(self, event: SlowPathEvent, *, record_history: bool = True) -> None:
        if record_history:
            self._history.append(event)
        handlers = self._handlers.get(event.event_type, [])
        await asyncio.gather(*(self._run_handler(handler, event) for handler in handlers))

    async def drain(self) -> None:
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

    def clear_history(self) -> None:
        self._history.clear()

    async def _run_handler(self, handler: SlowPathHandler, event: SlowPathEvent) -> None:
        try:
            result = handler(event)
            if hasattr(result, "__await__"):
                await result
        except Exception as exc:  # Slow Path failures are telemetry-only.
            if self._failure_handler is not None:
                self._failure_handler(event, exc)
