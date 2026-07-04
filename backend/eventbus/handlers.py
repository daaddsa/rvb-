"""Slow Path handler registration helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .events import SlowPathEvent, SlowPathEventType
from .slow_path import SlowPathBus, SlowPathHandler


@dataclass(slots=True)
class InMemoryTelemetrySink:
    defense_feedback: list[dict[str, Any]] = field(default_factory=list)
    evaluation_metrics: list[dict[str, Any]] = field(default_factory=list)
    audit_logs: list[dict[str, Any]] = field(default_factory=list)
    model_traces: list[dict[str, Any]] = field(default_factory=list)
    tool_traces: list[dict[str, Any]] = field(default_factory=list)
    report_events: list[dict[str, Any]] = field(default_factory=list)
    websocket_events: list[dict[str, Any]] = field(default_factory=list)
    task_lifecycle: list[dict[str, Any]] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)

    def append(self, event: SlowPathEvent) -> None:
        target = _event_bucket_name(event.event_type)
        getattr(self, target).append(event.to_dict())

    def record_failure(self, event: SlowPathEvent, exc: Exception) -> None:
        self.failures.append({"event": event.to_dict(), "error": str(exc)})


def register_handlers(
    bus: SlowPathBus,
    handlers: dict[SlowPathEventType, list[SlowPathHandler]],
    failure_handler: Callable[[SlowPathEvent, Exception], None] | None = None,
) -> SlowPathBus:
    for event_type, event_handlers in handlers.items():
        for handler in event_handlers:
            bus.subscribe(event_type, handler)

    if failure_handler is not None:
        bus.on_failure(failure_handler)

    return bus


def register_default_handlers(bus: SlowPathBus, sink: InMemoryTelemetrySink | None = None) -> InMemoryTelemetrySink:
    telemetry_sink = sink or InMemoryTelemetrySink()
    for event_type in SlowPathEventType:
        bus.subscribe(event_type, telemetry_sink.append)
    bus.on_failure(telemetry_sink.record_failure)
    return telemetry_sink


def _event_bucket_name(event_type: SlowPathEventType) -> str:
    return {
        SlowPathEventType.DEFENSE_FEEDBACK: "defense_feedback",
        SlowPathEventType.EVALUATION_METRIC: "evaluation_metrics",
        SlowPathEventType.AUDIT_LOG: "audit_logs",
        SlowPathEventType.MODEL_TRACE: "model_traces",
        SlowPathEventType.TOOL_TRACE: "tool_traces",
        SlowPathEventType.REPORT_EVENT: "report_events",
        SlowPathEventType.WEBSOCKET_EVENT: "websocket_events",
        SlowPathEventType.TASK_LIFECYCLE: "task_lifecycle",
    }[event_type]
