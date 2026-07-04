"""Shared blue-team detector primitives."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from backend.eventbus import EventContext, SlowPathBus, SlowPathEvent, SlowPathEventType

RiskLevel = Literal["low", "medium", "high", "critical"]
DecisionAction = Literal["allow", "block", "degrade"]
DetectorKind = Literal["input", "output"]


@dataclass(slots=True)
class DetectionResult:
    action: DecisionAction
    risk_level: RiskLevel | None = None
    risk_type: str | None = None
    reason: str | None = None
    confidence: float | None = None
    matched_rules: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_high_risk_block(self) -> bool:
        return self.action == "block" and self.risk_level in {"high", "critical"}


RuleDetector: Callable[[dict[str, Any]], Awaitable[DetectionResult]]
ModelDetector: Callable[[dict[str, Any]], Awaitable[DetectionResult]]


def normalize_detection_result(result: DetectionResult) -> DetectionResult:
    if result.risk_level in {"high", "critical"} and result.action != "block":
        reason = result.reason or "命中高风险策略，系统自动升级为阻断"
        metadata = dict(result.metadata)
        metadata["escalated_from_action"] = result.action
        return replace(result, action="block", reason=reason, metadata=metadata)
    return result


class ConcurrentDetector:
    def __init__(
        self,
        *,
        detector_kind: DetectorKind,
        model_name: str,
        rule_detector: RuleDetector,
        model_detector: ModelDetector,
        slow_path: SlowPathBus | None = None,
    ) -> None:
        self.detector_kind = detector_kind
        self.model_name = model_name
        self.rule_detector = rule_detector
        self.model_detector = model_detector
        self.slow_path = slow_path

    async def detect(self, payload: dict[str, Any], context: EventContext) -> DetectionResult:
        rule_task = asyncio.create_task(self.rule_detector(payload))
        model_task = asyncio.create_task(self.model_detector(payload))

        rule_result = normalize_detection_result(await rule_task)
        if rule_result.is_high_risk_block:
            model_task.cancel()
            await self._record_model_cancelled(context, rule_result)
            return rule_result

        try:
            model_result = normalize_detection_result(await model_task)
        except asyncio.CancelledError:
            raise

        return self._merge_results(rule_result, model_result)

    async def _record_model_cancelled(self, context: EventContext, rule_result: DetectionResult) -> None:
        if self.slow_path is None:
            return

        event = SlowPathEvent(
            event_type=SlowPathEventType.MODEL_TRACE,
            context=context,
            payload={
                "detector_kind": self.detector_kind,
                "model_name": self.model_name,
                "status": "cancelled_by_rule_hit",
                "matched_rules": rule_result.matched_rules,
                "risk_level": rule_result.risk_level,
                "risk_type": rule_result.risk_type,
                "reason": rule_result.reason,
            },
        )
        await self.slow_path.publish_and_wait(event)

    def _merge_results(self, rule_result: DetectionResult, model_result: DetectionResult) -> DetectionResult:
        if model_result.action == "block":
            return model_result
        if rule_result.action == "block":
            return rule_result
        if model_result.action == "degrade":
            return model_result
        if rule_result.action == "degrade":
            return rule_result
        return model_result if model_result.confidence else rule_result
