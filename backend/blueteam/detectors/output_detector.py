"""Output detector using rule checks with optional RAP support."""

from __future__ import annotations

from backend.blueteam.policy_loader import BluePolicy, load_blue_policy
from backend.eventbus import EventContext
from backend.llm import get_llm_client
from backend.llm.prompts import BLUE_OUTPUT_SYSTEM_PROMPT, payload_to_prompt

from .base import ConcurrentDetector, DetectionResult
from .input_detector import _normalize_action, _normalize_risk_level, _parse_model_result


async def default_output_rule_detector(payload: dict) -> DetectionResult:
    return detect_output_by_policy(payload, load_blue_policy())


async def default_rap_detector(payload: dict, model_name: str | None = None) -> DetectionResult:
    client = get_llm_client()
    content = await client.blue_chat(
        [
            {"role": "system", "content": BLUE_OUTPUT_SYSTEM_PROMPT},
            {"role": "user", "content": payload_to_prompt("Detect this target-agent output.", payload)},
        ],
        model=model_name,
    )
    return _parse_model_result(content, payload)


def detect_output_by_policy(payload: dict, policy: BluePolicy) -> DetectionResult:
    output = str(payload.get("output") or payload.get("target_output") or "")
    for rule in policy.output_rules:
        matched = [keyword for keyword in rule.keywords if keyword and keyword in output]
        if matched:
            return DetectionResult(
                action=_normalize_action(rule.action),
                risk_level=_normalize_risk_level(rule.risk_level),
                risk_type=rule.risk_type,
                reason=f"输出命中规则 {rule.id}: {', '.join(matched)}",
                confidence=0.95,
                matched_rules=[rule.id],
                metadata={"matched_keywords": matched, "payload": payload},
            )

    sensitive_matched = [field for field in policy.sensitive_fields if field and field in output]
    if sensitive_matched:
        return DetectionResult(
            action="block",
            risk_level="high",
            risk_type="ASI07",
            reason=f"输出包含敏感字段: {', '.join(sensitive_matched)}",
            confidence=0.9,
            matched_rules=["sensitive_fields"],
            metadata={"matched_fields": sensitive_matched, "payload": payload},
        )
    return DetectionResult(action="allow", risk_level="low", reason="输出检测通过", confidence=0.5, metadata={"payload": payload})


class OutputDetector(ConcurrentDetector):
    def __init__(self, policy: BluePolicy | None = None, use_model: bool = True, model_name: str | None = None, **kwargs) -> None:
        self.policy = policy or load_blue_policy()
        self.use_model = use_model
        self.model_name = model_name
        super().__init__(
            detector_kind="output",
            model_name=model_name or "RAP",
            rule_detector=kwargs.pop("rule_detector", lambda payload: _async_rule(payload, self.policy)),
            model_detector=kwargs.pop("model_detector", lambda payload: default_rap_detector(payload, self.model_name)),
            **kwargs,
        )

    async def detect_output(self, payload: dict, context: EventContext | None = None) -> DetectionResult:
        if context is None:
            context = EventContext(task_id=str(payload.get("task_id") or "task"), trace_id=str(payload.get("trace_id") or "trace"))
        return await self.detect(payload, context)


async def _async_rule(payload: dict, policy: BluePolicy) -> DetectionResult:
    return detect_output_by_policy(payload, policy)
