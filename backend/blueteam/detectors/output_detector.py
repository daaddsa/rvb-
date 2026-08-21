"""Output detector using rule checks with optional RAP support.
输出检测器：基于规则和 RAP 模型检测目标智能体输出中的敏感数据泄露。
"""

from __future__ import annotations

from backend.blueteam.policy_loader import BluePolicy, load_blue_policy
from backend.eventbus import EventContext
from backend.llm import get_llm_client
from backend.llm.prompts import BLUE_OUTPUT_SYSTEM_PROMPT, payload_to_prompt

from .base import ConcurrentDetector, DetectionResult
from .input_detector import _normalize_action, _normalize_risk_level, _parse_model_result


async def default_output_rule_detector(payload: dict) -> DetectionResult:
    """默认输出规则检测器：基于策略中的 output_rules 进行关键词匹配。
    参数：
        payload: 包含 output 的字典
    返回：
        DetectionResult 检测结果
    """
    return detect_output_by_policy(payload, load_blue_policy())


async def default_rap_detector(payload: dict, model_name: str | None = None) -> DetectionResult:
    """默认 RAP 模型检测器：通过 LLM 检测输出中的敏感信息。
    参数：
        payload: 包含 output 的字典
        model_name: 模型名称
    返回：
        DetectionResult 检测结果
    """
    client = get_llm_client()
    # 调用蓝队 LLM 进行输出检测
    content = await client.blue_chat(
        [
            {"role": "system", "content": BLUE_OUTPUT_SYSTEM_PROMPT},
            {"role": "user", "content": payload_to_prompt("Detect this target-agent output.", payload)},
        ],
        model=model_name,
    )
    return _parse_model_result(content, payload)


def detect_output_by_policy(payload: dict, policy: BluePolicy) -> DetectionResult:
    """基于策略规则检测输出。
    先检查 output_rules 关键词匹配，再检查敏感字段泄露。
    参数：
        payload: 包含 output 的字典
        policy: 蓝队安全策略
    返回：
        DetectionResult：如果命中规则或敏感字段则返回对应动作，否则返回 allow
    """
    output = str(payload.get("output") or payload.get("target_output") or "")
    # 首先检查输出规则
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

    # 然后检查敏感字段（如手机号、身份证号）
    sensitive_matched = [field for field in policy.sensitive_fields if field and field in output]
    if sensitive_matched:
        return DetectionResult(
            action="block",  # 敏感字段直接阻断
            risk_level="high",
            risk_type="ASI07",  # 数据泄露风险类型
            reason=f"输出包含敏感字段: {', '.join(sensitive_matched)}",
            confidence=0.9,
            matched_rules=["sensitive_fields"],
            metadata={"matched_fields": sensitive_matched, "payload": payload},
        )
    return DetectionResult(action="allow", risk_level="low", reason="输出检测通过", confidence=0.5, metadata={"payload": payload})


class OutputDetector(ConcurrentDetector):
    """输出检测器：继承 ConcurrentDetector，配置规则检测和 RAP 模型检测。"""

    def __init__(self, policy: BluePolicy | None = None, use_model: bool = True, model_name: str | None = None, **kwargs) -> None:
        """初始化输出检测器。
        参数：
            policy: 蓝队安全策略
            use_model: 是否启用模型检测
            model_name: 模型名称
        """
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
        """执行输出检测的入口方法。
        参数：
            payload: 包含 output 的检测数据
            context: 事件上下文，为 None 时自动构建
        返回：
            DetectionResult 检测结果
        """
        if context is None:
            context = EventContext(task_id=str(payload.get("task_id") or "task"), trace_id=str(payload.get("trace_id") or "trace"))
        return await self.detect(payload, context)  # 调用基类的并发检测


async def _async_rule(payload: dict, policy: BluePolicy) -> DetectionResult:
    """异步包装的规则检测函数。
    参数：
        payload: 检测数据
        policy: 安全策略
    返回：
        DetectionResult
    """
    return detect_output_by_policy(payload, policy)