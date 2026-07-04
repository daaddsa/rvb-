"""Append-only audit log helpers for attack evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class AuditLogRecord:
    id: str
    task_id: str
    event_type: str
    trace_id: str | None = None
    attack_case_id: str | None = None
    event_topic: str | None = None
    agent: str | None = None
    tool_name: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    allowed: bool | None = None
    risk_level: str | None = None
    risk_type: str | None = None
    message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


class AuditTrail:
    def __init__(self) -> None:
        self._records: list[AuditLogRecord] = []

    @property
    def records(self) -> list[AuditLogRecord]:
        return list(self._records)

    def append(self, record: AuditLogRecord | dict[str, Any]) -> AuditLogRecord:
        audit_record = record if isinstance(record, AuditLogRecord) else build_audit_record(**record)
        self._records.append(audit_record)
        return audit_record

    def extend(self, records: list[AuditLogRecord | dict[str, Any]]) -> None:
        for record in records:
            self.append(record)

    def export(self) -> list[dict[str, Any]]:
        return [record.to_dict() for record in self._records]


def build_audit_record(
    *,
    task_id: str,
    event_type: str,
    trace_id: str | None = None,
    attack_case_id: str | None = None,
    event_topic: str | None = None,
    agent: str | None = None,
    tool_name: str | None = None,
    payload: dict[str, Any] | None = None,
    allowed: bool | None = None,
    risk_level: str | None = None,
    risk_type: str | None = None,
    message: str | None = None,
    id: str | None = None,
    **_: Any,
) -> AuditLogRecord:
    return AuditLogRecord(
        id=id or f"audit_{uuid4().hex[:12]}",
        task_id=task_id,
        trace_id=trace_id,
        attack_case_id=attack_case_id,
        event_type=event_type,
        event_topic=event_topic or _default_topic(event_type),
        agent=agent,
        tool_name=tool_name,
        payload=payload or {},
        allowed=allowed,
        risk_level=risk_level,
        risk_type=risk_type,
        message=message,
    )


def get_audit_trail(state: dict[str, Any]) -> AuditTrail:
    trail = state.get("audit_trail")
    if isinstance(trail, AuditTrail):
        return trail
    trail = AuditTrail()
    state["audit_trail"] = trail
    return trail


def _default_topic(event_type: str) -> str:
    if event_type in {"EVALUATION_METRIC", "REPORT_EVENT", "MODEL_TRACE", "TOOL_TRACE"}:
        return "SLOW_PATH"
    return "FAST_PATH"
