"""双总线事件包
提供快路径（Fast Path）同步总线和慢路径（Slow Path）异步总线，
用于红蓝对抗执行流程中的事件驱动通信。
"""

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