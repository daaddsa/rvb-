"""Tool call auditor for blue-team policy enforcement.
工具调用审计器：基于角色权限和敏感数据检测对工具调用进行安全审计。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from backend.blueteam.policy_loader import BluePolicy, RolePolicy, load_blue_policy
from backend.blueteam.detectors.base import DetectionResult, normalize_detection_result
from backend.llm import get_llm_client, parse_llm_json
from backend.llm.prompts import BLUE_TOOL_SYSTEM_PROMPT, payload_to_prompt
from backend.targets.sandbox.contracts import ToolCallPlan


@dataclass(slots=True)
class ToolAuditRecord:
    """工具审计记录数据类。
    记录工具调用的审计结果，包括是否允许、阻断、降级等信息。
    """
    task_id: str  # 任务标识
    attack_case_id: str  # 攻击用例ID
    trace_id: str  # 链路追踪ID
    caller_agent: str  # 调用方智能体标识
    tool_name: str  # 工具名称
    tool_args: dict[str, Any]  # 工具参数
    allowed: bool  # 是否允许
    blocked: bool  # 是否阻断
    action: str = "allow"  # 审计动作：allow / block / degrade
    risk_level: str | None = None  # 风险等级
    risk_type: str | None = None  # 风险类型
    reason: str | None = None  # 审计理由
    degraded_to: ToolCallPlan | None = None  # 降级后的工具调用方案
    matched_rules: list[str] = field(default_factory=list)  # 命中的规则
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))  # 创建时间


class ToolAuditor:
    """工具调用审计器：基于角色权限、安全策略和 LLM 进行工具调用安全审计。"""

    def __init__(self, policy: BluePolicy | None = None, user_role: str = "guest", model_name: str | None = None) -> None:
        """初始化工具审计器。
        参数：
            policy: 蓝队安全策略
            user_role: 用户角色（用于权限检查）
            model_name: LLM 模型名称
        """
        self.policy = policy or load_blue_policy()
        self.user_role = user_role
        self.model_name = model_name

    def audit_tool_call(
        self,
        *,
        task_id: str,
        attack_case_id: str,
        trace_id: str,
        caller_agent: str,
        tool_call: ToolCallPlan | None,
        prompt: str = "",
    ) -> ToolAuditRecord:
        """审计工具调用计划。
        参数：
            task_id: 任务标识
            attack_case_id: 攻击用例ID
            trace_id: 链路追踪ID
            caller_agent: 调用方智能体
            tool_call: 工具调用计划，为 None 表示无工具调用
            prompt: 原始用户 prompt
        返回：
            ToolAuditRecord 审计记录
        """
        # 如果无工具调用计划，直接返回放行记录
        if tool_call is None:
            return ToolAuditRecord(
                task_id=task_id,
                attack_case_id=attack_case_id,
                trace_id=trace_id,
                caller_agent=caller_agent,
                tool_name="none",
                tool_args={},
                allowed=True,
                blocked=False,
                reason="无工具调用计划",
            )

        # 执行审计评估并规范化结果
        decision = normalize_detection_result(self.evaluate(tool_call, prompt=prompt))
        action = decision.action
        return ToolAuditRecord(
            task_id=task_id,
            attack_case_id=attack_case_id,
            trace_id=trace_id,
            caller_agent=caller_agent,
            tool_name=tool_call.tool_name,
            tool_args=tool_call.arguments,
            allowed=action != "block",  # 非阻断即为允许
            blocked=action == "block",
            action=action,
            risk_level=decision.risk_level,
            risk_type=decision.risk_type,
            reason=decision.reason,
            degraded_to=decision.metadata.get("degraded_to"),  # 降级方案
            matched_rules=decision.matched_rules,
        )

    def evaluate(self, tool_call: ToolCallPlan, prompt: str = "") -> DetectionResult:
        """评估工具调用：先检查策略规则，再通过 LLM 进行深度审计。
        参数：
            tool_call: 工具调用计划
            prompt: 原始用户 prompt
        返回：
            DetectionResult 检测结果
        """
        # 先执行基于策略的规则评估
        policy_result = self._evaluate_by_policy(tool_call, prompt)
        if policy_result is not None:
            return policy_result  # 规则命中则直接返回，不调用 LLM

        # 规则未命中，通过 LLM 进行深度审计
        content = asyncio.run(
            get_llm_client().blue_chat(
                [
                    {"role": "system", "content": BLUE_TOOL_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": payload_to_prompt(
                            "Audit this planned tool call.",
                            {
                                "user_role": self.user_role,
                                "prompt": prompt,
                                "tool_name": tool_call.tool_name,
                                "tool_args": tool_call.arguments,
                            },
                        ),
                    },
                ],
                model=self.model_name,
            )
        )
        return _parse_tool_model_result(content)  # 解析 LLM 返回结果

    def _evaluate_by_policy(self, tool_call: ToolCallPlan, prompt: str = "") -> DetectionResult | None:
        """基于安全策略规则评估工具调用。
        检查顺序：角色权限 → 敏感数据请求。
        参数：
            tool_call: 工具调用计划
            prompt: 原始用户 prompt
        返回：
            DetectionResult 或 None（规则未命中时返回 None）
        """
        # 检查角色权限
        role_policy = self.policy.roles.get(self.user_role)
        role_result = _evaluate_role_policy(role_policy, self.user_role, tool_call)
        if role_result is not None:
            return role_result

        # 检查是否请求敏感数据
        if _requests_sensitive_data(prompt, tool_call, self.policy.sensitive_fields):
            return _degrade_decision(
                "工具请求涉及敏感字段，已降级为安全摘要查询",
                ["sensitive_fields"],
                "ASI07",
            )

        return None  # 规则未命中

    def audit_call(
        self,
        *,
        task_id: str,
        attack_case_id: str,
        trace_id: str,
        caller_agent: str,
        tool_name: str,
        tool_args: dict[str, Any],
        allowed: bool = True,
        reason: str | None = None,
    ) -> ToolAuditRecord:
        """直接创建审计记录（用于简单场景，不经过评估流程）。
        参数：
            task_id: 任务标识
            attack_case_id: 攻击用例ID
            trace_id: 链路追踪ID
            caller_agent: 调用方智能体
            tool_name: 工具名称
            tool_args: 工具参数
            allowed: 是否允许
            reason: 理由
        返回：
            ToolAuditRecord
        """
        return ToolAuditRecord(
            task_id=task_id,
            attack_case_id=attack_case_id,
            trace_id=trace_id,
            caller_agent=caller_agent,
            tool_name=tool_name,
            tool_args=tool_args,
            allowed=allowed,
            blocked=not allowed,
            action="allow" if allowed else "block",
            reason=reason,
        )


def _evaluate_role_policy(role_policy: RolePolicy | None, user_role: str, tool_call: ToolCallPlan) -> DetectionResult | None:
    """基于角色权限评估工具调用。
    参数：
        role_policy: 角色权限策略
        user_role: 用户角色名
        tool_call: 工具调用计划
    返回：
        DetectionResult 或 None（无策略命中时）
    """
    if role_policy is None:
        return None  # 没有角色策略则跳过

    # 检查工具是否在禁止列表中
    if tool_call.tool_name in role_policy.denied_tools:
        return DetectionResult(
            action="block",
            risk_level="high",
            risk_type="ASI02",
            reason=f"角色 {user_role} 禁止调用工具 {tool_call.tool_name}",
            confidence=0.99,
            matched_rules=[f"role_denied:{user_role}"],
        )

    # 检查工具是否不在允许列表中（如果允许列表非空）
    if role_policy.allowed_tools and tool_call.tool_name not in role_policy.allowed_tools:
        return DetectionResult(
            action="block",
            risk_level="high",
            risk_type="ASI02",
            reason=f"角色 {user_role} 不允许调用工具 {tool_call.tool_name}",
            confidence=0.99,
            matched_rules=[f"role_allowlist:{user_role}"],
        )

    return None  # 通过角色权限检查


def _parse_tool_model_result(content: str) -> DetectionResult:
    """解析 LLM 工具审计模型返回的结果 JSON。
    参数：
        content: LLM 返回的原始内容
    返回：
        DetectionResult 对象
    """
    data = parse_llm_json(content)
    if not isinstance(data, dict):
        raise ValueError("蓝方工具审计模型必须返回 JSON 对象")
    # 规范化动作
    action = str(data.get("action") or "allow")
    if action not in {"allow", "block", "degrade"}:
        action = "allow"
    # 提取降级方案
    degraded_to = data.get("degraded_to")
    metadata = {"raw_model_output": content}
    if isinstance(degraded_to, dict) and degraded_to.get("tool_name"):
        arguments = degraded_to.get("arguments")
        metadata["degraded_to"] = ToolCallPlan(str(degraded_to["tool_name"]), arguments if isinstance(arguments, dict) else {})
    # 提取置信度
    confidence = data.get("confidence")
    if not isinstance(confidence, int | float):
        confidence = None
    return DetectionResult(
        action=action,
        risk_level=data.get("risk_level") if data.get("risk_level") in {"low", "medium", "high", "critical"} else None,
        risk_type=data.get("risk_type"),
        reason=data.get("reason"),
        confidence=confidence,
        metadata=metadata,
    )


def _degrade_decision(reason: str, matched_rules: list[str], risk_type: str) -> DetectionResult:
    """构建降级决策结果。
    参数：
        reason: 降级理由
        matched_rules: 命中的规则
        risk_type: 风险类型
    返回：
        DetectionResult，action 为 degrade
    """
    return DetectionResult(
        action="degrade",
        risk_level="medium",
        risk_type=risk_type,
        reason=reason,
        confidence=0.9,
        matched_rules=matched_rules,
        metadata={"degraded_to": ToolCallPlan("query_customer_summary", {})},  # 降级为安全摘要查询
    )


def _requests_sensitive_data(prompt: str, tool_call: ToolCallPlan, sensitive_fields: list[str]) -> bool:
    """判断工具调用是否请求敏感数据。
    参数：
        prompt: 用户 prompt
        tool_call: 工具调用计划
        sensitive_fields: 敏感字段列表
    返回：
        True 如果检测到敏感数据请求
    """
    # 敏感关键词列表
    sensitive_terms = ("手机号", "身份证", "银行卡", "联系方式", "明细")
    # 检查 prompt 中是否包含敏感词，或工具参数中的 fields 是否包含敏感字段
    fields = set(str(field) for field in tool_call.arguments.get("fields", []) or [])
    return any(term in prompt for term in sensitive_terms) or bool(fields & set(sensitive_fields))