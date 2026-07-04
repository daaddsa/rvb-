"""Fast Path bus for synchronous confrontation execution."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import TypeAlias

from .events import FastPathEvent, FastPathEventType, RoundOutcome

FastPathHandler: TypeAlias = Callable[[FastPathEvent], FastPathEvent | RoundOutcome | None]


class FastPathBus:
    """Synchronous bus that drives the red-blue execution path."""

    def __init__(self) -> None:
        self._handlers: dict[FastPathEventType, list[FastPathHandler]] = defaultdict(list)
        self._history: list[FastPathEvent] = []

    @property
    def history(self) -> list[FastPathEvent]:
        return list(self._history)

    def subscribe(self, event_type: FastPathEventType, handler: FastPathHandler) -> None:
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: FastPathEventType, handler: FastPathHandler) -> None:
        if handler in self._handlers.get(event_type, []):
            self._handlers[event_type].remove(handler)

    def publish(self, event: FastPathEvent) -> list[FastPathEvent | RoundOutcome]:
        self._history.append(event)
        results: list[FastPathEvent | RoundOutcome] = []
        for handler in self._handlers.get(event.event_type, []):
            result = handler(event)
            if result is not None:
                results.append(result)
        return results

    def publish_until_outcome(self, event: FastPathEvent) -> RoundOutcome | None:
        self._history.append(event)
        for handler in self._handlers.get(event.event_type, []):
            result = handler(event)
            if isinstance(result, RoundOutcome):
                return result
        return None

    def clear_history(self) -> None:
        self._history.clear()
