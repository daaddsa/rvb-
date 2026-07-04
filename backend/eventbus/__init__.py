"""Dual-bus event package."""

from .events import (
    DefenseFeedback,
    EventContext,
    FastPathEvent,
    FastPathEventType,
    LayerFeedback,
    RoundOutcome,
    SlowPathEvent,
    SlowPathEventType,
    ToolFeedback,
)
from .fast_path import FastPathBus, FastPathHandler
from .handlers import InMemoryTelemetrySink, register_default_handlers, register_handlers
from .slow_path import SlowPathBus, SlowPathHandler

__all__ = [
    "DefenseFeedback",
    "EventContext",
    "FastPathBus",
    "FastPathEvent",
    "FastPathEventType",
    "FastPathHandler",
    "InMemoryTelemetrySink",
    "LayerFeedback",
    "RoundOutcome",
    "SlowPathBus",
    "SlowPathEvent",
    "SlowPathEventType",
    "SlowPathHandler",
    "ToolFeedback",
    "register_default_handlers",
    "register_handlers",
]
