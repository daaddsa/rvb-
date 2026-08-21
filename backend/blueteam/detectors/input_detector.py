"""Input detector using rule checks with optional ReLLM support.
输入检测器：基于规则和 ReLLM 模型检测攻击输入。
"""

from __future__ import annotations

from backend.blueteam.policy_loader import BluePolicy, load_blue_policy
from backend.eventbus import EventContext
from backend.llm import get_llm_client, parse_llm_json
from backend.llm.prompts import BLUE_INPUT_SYSTEM_PROMPT, payload_to_prompt

from .base import ConcurrentDetector, DetectionResult


async def default_input_rule_detector(payload: dict) -> DetectionResult:
    """默认输入规则检测器：基于策略中的 input_rules 进行关键词匹配。
    参数：
        payload: 包含 prompt 的字典
    返回：
        DetectionResult 检测结果
    """
    return detect_input_by_policy(payload, load_blue_policy())


async def default_rellm_detector(payload: dict, model_name: str | None = None) -> DetectionResult:
    """默认 ReLLM 模型检测器：通过 LLM 检测输入中的攻击意图。
    参数：
        payload: 包含 prompt 的字典
        model_name: 模型名称
    返回：
        DetectionResult 检测结果
    """
    client = get_llm_client()
    # 调用蓝队 LLM 进行输入检测
    content = await client.blue_chat(
        [
            {"role": "system", "content": BLUE_INPUT_SYSTEM_PROMPT},
            {"role": "user", "content": payload_to_prompt("Detect this incoming target-agent input.", payload)},
        ],
        model=model_name,
    )
    return _parse_model_result(content, payload)


def detect_input_by_policy(payload: dict, policy: BluePolicy) -> DetectionResult:
    """基于策略规则检测输入。
    遍历 input_rules 中的规则，进行关键词匹配。
    参数：
        payload: 包含 prompt 的字典
        policy: 蓝队安全策略
    返回：
        DetectionResult：如果命中规则则返回对应动作，否则返回 allow
    """
    prompt = str(payload.get("prompt") or payload.get("input") or "")
    # 遍历输入规则列表
    for rule in policy.input_rules:
        # 检查规则关键词是否在 prompt 中出现
        matched = [keyword for keyword in rule.keywords if keyword and keyword in prompt]
        if matched:
            return DetectionResult(
                action=_normalize_action(rule.action),  # 规范化动作
                risk_level=_normalize_risk_level(rule.risk_level),  # 规范化风险等级
                risk_type=rule.risk_type,
                reason=f"输入命中规则 {rule.id}: {', '.join(matched)}",
                confidence=0.95,  # 规则匹配置信度高
                matched_rules=[rule.id],
                metadata={"matched_keywords": matched, "payload": payload},
            )
    # 没有命中任何规则，放行
    return DetectionResult(action="allow", risk_level="low", reason="输入检测通过", confidence=0.5, metadata={"payload": payload})


def _parse_model_result(content: str, payload: dict) -> DetectionResult:
    """解析 LLM 模型返回的检测结果 JSON。
    参数：
        content: LLM 返回的原始内容
        payload: 原始检测数据
    返回：
        DetectionResult 对象
    """
    try:
        data = parse_llm_json(content)  # 尝试 JSON 解析
    except ValueError:
        # JSON 解析失败时，将原始内容作为 reason，放行
        return DetectionResult(action="allow", reason=content, confidence=0.1, metadata={"payload": payload, "raw_model_output": content})

    action = _normalize_action(data.get("action", "allow"))
    risk_level = _normalize_risk_level(data.get("risk_level"))
    confidence = data.get("confidence")
    # 验证置信度类型
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
    """规范化动作值：仅允许 allow/block/degrade，否则返回 allow。
    参数：
        value: 待规范化的动作值
    返回：
        规范化后的动作字符串
    """
    return str(value) if value in {"allow", "block", "degrade"} else "allow"


def _normalize_risk_level(value: object) -> str | None:
    """规范化风险等级：仅允许 low/medium/high/critical，否则返回 None。
    参数：
        value: 待规范化的风险等级
    返回：
        规范化后的风险等级字符串或 None
    """
    return str(value) if value in {"low", "medium", "high", "critical"} else None


class InputDetector(ConcurrentDetector):
    """输入检测器：继承 ConcurrentDetector，配置规则检测和 ReLLM 模型检测。"""

    def __init__(self, policy: BluePolicy | None = None, use_model: bool = True, model_name: str | None = None, **kwargs) -> None:
        """初始化输入检测器。
        参数：
            policy: 蓝队安全策略
            use_model: 是否启用模型检测
            model_name: 模型名称
        """
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
        """执行输入检测的入口方法。
        参数：
            payload: 包含 prompt 的检测数据
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
    return detect_input_by_policy(payload, policy)