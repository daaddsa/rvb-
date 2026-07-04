"""Input detector using rule checks with optional ReLLM support."""

from __future__ import annotations

from backend.blueteam.policy_loader import BluePolicy, load_blue_policy
from backend.eventbus import EventContext
from backend.llm import get_llm_client, parse_llm_json
from backend.llm.prompts import BLUE_INPUT_SYSTEM_PROMPT, payload_to_prompt

from .base import ConcurrentDetector, DetectionResult


async def default_input_rule_detector(payload: dict) -> DetectionResult:
    return detect_input_by_policy(payload, load_blue_policy())


async def default_rellm_detector(payload: dict, model_name: str | None = None) -> DetectionResult:
    client = get_llm_client()
    content = await client.blue_chat(
        [
            {"role": "system", "content": BLUE_INPUT_SYSTEM_PROMPT},
            {"role": "user", "content": payload_to_prompt("Detect this incoming target-agent input.", payload)},
        ],
        model=model_name,
    )
    return _parse_model_result(content, payload)


def detect_input_by_policy(payload: dict, policy: BluePolicy) -> DetectionResult:
    prompt = str(payload.get("prompt") or payload.get("input") or "")
    for rule in policy.input_rules:
        matched = [keyword for keyword in rule.keywords if keyword and keyword in prompt]
        if matched:
            return DetectionResult(
                action=_normalize_action(rule.action),
                risk_level=_normalize_risk_level(rule.risk_level),
                risk_type=rule.risk_type,
                reason=f"输入命中规则 {rule.id}: {', '.join(matched)}",
                confidence=0.95,
                matched_rules=[rule.id],
                metadata={"matched_keywords": matched, "payload": payload},
            )
    return DetectionResult(action="allow", risk_level="low", reason="输入检测通过", confidence=0.5, metadata={"payload": payload})


def _parse_model_result(content: str, payload: dict) -> DetectionResult:
    try:
        data = parse_llm_json(content)
    except ValueError:
        return DetectionResult(action="allow", reason=content, confidence=0.1, metadata={"payload": payload, "raw_model_output": content})

    action = _normalize_action(data.get("action", "allow"))
    risk_level = _normalize_risk_level(data.get("risk_level"))
    confidence = data.get("confidence")
    if not isinstance(confidence, int | float):
        confidence = None

    return DetectionResult(
        action=action,
        risk_level=risk_level,
        risk_type=data.get("risk_type"),
        reason=data.get("reason"),
        confidence=confidence,
        metadata={"payload": payload, "raw_model_output": content},
    )


def _normalize_action(value: object) -> str:
    return str(value) if value in {"allow", "block", "degrade"} else "allow"


def _normalize_risk_level(value: object) -> str | None:
    return str(value) if value in {"low", "medium", "high", "critical"} else None


class InputDetector(ConcurrentDetector):
    def __init__(self, policy: BluePolicy | None = None, use_model: bool = True, model_name: str | None = None, **kwargs) -> None:
        self.policy = policy or load_blue_policy()
        self.use_model = use_model
        self.model_name = model_name
        super().__init__(
            detector_kind="input",
            model_name=model_name or "ReLLM",
            rule_detector=kwargs.pop("rule_detector", lambda payload: _async_rule(payload, self.policy)),
            model_detector=kwargs.pop("model_detector", lambda payload: default_rellm_detector(payload, self.model_name)),
            **kwargs,
        )

    async def detect_input(self, payload: dict, context: EventContext | None = None) -> DetectionResult:
        if context is None:
            context = EventContext(task_id=str(payload.get("task_id") or "task"), trace_id=str(payload.get("trace_id") or "trace"))
        return await self.detect(payload, context)


async def _async_rule(payload: dict, policy: BluePolicy) -> DetectionResult:
    return detect_input_by_policy(payload, policy)
