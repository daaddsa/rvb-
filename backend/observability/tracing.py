"""Lightweight tracing helpers for task execution."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Iterator
from uuid import uuid4


@dataclass(slots=True)
class TraceSpan:
    span_id: str
    trace_id: str
    name: str
    task_id: str | None = None
    attack_case_id: str | None = None
    parent_span_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    duration_ms: float | None = None
    status: str = "OK"
    error: str | None = None

    def finish(self, *, status: str = "OK", error: str | None = None, started_perf: float | None = None) -> None:
        self.ended_at = datetime.now(timezone.utc)
        self.status = status
        self.error = error
        if started_perf is not None:
            self.duration_ms = round((perf_counter() - started_perf) * 1000, 3)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["started_at"] = self.started_at.isoformat()
        data["ended_at"] = self.ended_at.isoformat() if self.ended_at else None
        return data


class TraceRecorder:
    def __init__(self) -> None:
        self._spans: list[TraceSpan] = []

    @property
    def spans(self) -> list[TraceSpan]:
        return list(self._spans)

    def start_span(
        self,
        name: str,
        *,
        trace_id: str | None = None,
        task_id: str | None = None,
        attack_case_id: str | None = None,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> TraceSpan:
        span = TraceSpan(
            span_id=f"span_{uuid4().hex[:12]}",
            trace_id=trace_id or f"trace_{uuid4().hex[:12]}",
            name=name,
            task_id=task_id,
            attack_case_id=attack_case_id,
            parent_span_id=parent_span_id,
            attributes=attributes or {},
        )
        self._spans.append(span)
        return span

    @contextmanager
    def span(self, name: str, **kwargs: Any) -> Iterator[TraceSpan]:
        started_perf = perf_counter()
        trace_span = self.start_span(name, **kwargs)
        try:
            yield trace_span
            trace_span.finish(started_perf=started_perf)
        except Exception as exc:
            trace_span.finish(status="ERROR", error=str(exc), started_perf=started_perf)
            raise

    def export(self) -> list[dict[str, Any]]:
        return [span.to_dict() for span in self._spans]


def get_trace_recorder(state: dict[str, Any]) -> TraceRecorder:
    recorder = state.get("trace_recorder")
    if isinstance(recorder, TraceRecorder):
        return recorder
    recorder = TraceRecorder()
    state["trace_recorder"] = recorder
    return recorder
