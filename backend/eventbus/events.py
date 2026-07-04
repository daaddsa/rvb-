"""Domain events for the dual-bus confrontation runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4


class FastPathEventType(StrEnum):
    ATTACK_REQUEST = "ATTACK_REQUEST"
    INPUT_RECEIVED = "INPUT_RECEIVED"
    INPUT_ALLOWED = "INPUT_ALLOWED"
    AGENT_ACTION = "AGENT_ACTION"
    TOOL_ALLOWED = "TOOL_ALLOWED"
    TOOL_BLOCKED = "TOOL_BLOCKED"
    TOOL_DEGRADED = "TOOL_DEGRADED"
    TARGET_EXECUTION_RESULT = "TARGET_EXECUTION_RESULT"
    OUTPUT_ALLOWED = "OUTPUT_ALLOWED"
    OUTPUT_BLOCKED = "OUTPUT_BLOCKED"
    ROUND_OUTCOME = "ROUND_OUTCOME"
    NEXT_ROUND_REQUEST = "NEXT_ROUND_REQUEST"


class SlowPathEventType(StrEnum):
    DEFENSE_FEEDBACK = "DEFENSE_FEEDBACK"
    EVALUATION_METRIC = "EVALUATION_METRIC"
    AUDIT_LOG = "AUDIT_LOG"
    MODEL_TRACE = "MODEL_TRACE"
    TOOL_TRACE = "TOOL_TRACE"
    REPORT_EVENT = "REPORT_EVENT"
    WEBSOCKET_EVENT = "WEBSOCKET_EVENT"
    TASK_LIFECYCLE = "TASK_LIFECYCLE"


@dataclass(slots=True)
class EventContext:
    task_id: str
    trace_id: str
    round_id: str | None = None
    attack_case_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FastPathEvent:
    event_type: FastPathEventType
    context: EventContext
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "context": self.context.to_dict(),
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(slots=True)
class SlowPathEvent:
    event_type: SlowPathEventType
    context: EventContext
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "context": self.context.to_dict(),
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(slots=True)
class ToolFeedback:
    tool_name: str | None = None
    decision: Literal["allow", "block", "degrade", "not_reached"] = "not_reached"
    reason: str | None = None
    degraded_to: dict[str, Any] | None = None


@dataclass(slots=True)
class LayerFeedback:
    decision: Literal["allow", "block", "degrade", "not_reached"] = "not_reached"
    reason: str | None = None
    risk_type: str | None = None


@dataclass(slots=True)
class RoundOutcome:
    context: EventContext
    outcome: Literal["success", "blocked", "degraded", "allowed_but_failed", "partial_success"]
    successful: bool
    blocked: bool
    stage: Literal["input", "tool_call", "output", "target_execution", "round"]
    action: Literal["allow", "block", "degrade", "none"]
    reason: str
    risk_type: str | None = None
    risk_level: Literal["low", "medium", "high", "critical"] | None = None
    confidence: float | None = None
    matched_policy_summary: list[str] = field(default_factory=list)
    successful_steps: list[str] = field(default_factory=list)
    failed_step: str | None = None
    failed_objective: str | None = None
    input_feedback: LayerFeedback | None = None
    tool_feedback: ToolFeedback | None = None
    output_feedback: LayerFeedback | None = None
    redteam_hint: str | None = None
    suggested_mutation_strategy: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "successful": self.successful,
            "blocked": self.blocked,
            "stage": self.stage,
            "action": self.action,
            "reason": self.reason,
            "risk_type": self.risk_type,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "matched_policy_summary": self.matched_policy_summary,
            "successful_steps": self.successful_steps,
            "failed_step": self.failed_step,
            "failed_objective": self.failed_objective,
            "input_feedback": asdict(self.input_feedback) if self.input_feedback else None,
            "tool_feedback": asdict(self.tool_feedback) if self.tool_feedback else None,
            "output_feedback": asdict(self.output_feedback) if self.output_feedback else None,
            "redteam_hint": self.redteam_hint,
            "suggested_mutation_strategy": self.suggested_mutation_strategy,
        }

    def to_fast_path_event(self) -> FastPathEvent:
        return FastPathEvent(
            event_type=FastPathEventType.ROUND_OUTCOME,
            context=self.context,
            payload=self.to_payload(),
        )


@dataclass(slots=True)
class DefenseFeedback:
    context: EventContext
    stage: str
    action: Literal["allow", "block", "degrade", "none"]
    reason: str
    risk_type: str | None = None
    risk_level: str | None = None
    matched_rules: list[str] = field(default_factory=list)
    confidence: float | None = None
    detector_version: str | None = None
    model_trace_id: str | None = None
    tool_trace_id: str | None = None
    latency_ms: int | None = None
    raw_details: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "action": self.action,
            "reason": self.reason,
            "risk_type": self.risk_type,
            "risk_level": self.risk_level,
            "matched_rules": self.matched_rules,
            "confidence": self.confidence,
            "detector_version": self.detector_version,
            "model_trace_id": self.model_trace_id,
            "tool_trace_id": self.tool_trace_id,
            "latency_ms": self.latency_ms,
            "raw_details": self.raw_details,
        }

    def to_slow_path_event(self) -> SlowPathEvent:
        return SlowPathEvent(
            event_type=SlowPathEventType.DEFENSE_FEEDBACK,
            context=self.context,
            payload=self.to_payload(),
        )
