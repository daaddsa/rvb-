"""领域事件定义
定义双总线对抗运行时的核心数据结构和事件类型枚举。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4


class FastPathEventType(StrEnum):
    """快路径事件类型枚举。
    快路径事件用于同步驱动红蓝对抗的核心执行流程，必须被同步处理。
    """
    ATTACK_REQUEST = "ATTACK_REQUEST"             # 红队发起攻击请求
    INPUT_RECEIVED = "INPUT_RECEIVED"             # 目标系统收到输入
    INPUT_ALLOWED = "INPUT_ALLOWED"               # 输入被允许通过
    AGENT_ACTION = "AGENT_ACTION"                 # 智能体执行动作
    TOOL_ALLOWED = "TOOL_ALLOWED"                 # 工具调用被允许
    TOOL_BLOCKED = "TOOL_BLOCKED"                 # 工具调用被拦截
    TOOL_DEGRADED = "TOOL_DEGRADED"               # 工具调用被降级
    TARGET_EXECUTION_RESULT = "TARGET_EXECUTION_RESULT"  # 目标系统执行结果
    OUTPUT_ALLOWED = "OUTPUT_ALLOWED"             # 输出被允许
    OUTPUT_BLOCKED = "OUTPUT_BLOCKED"             # 输出被拦截
    ROUND_OUTCOME = "ROUND_OUTCOME"               # 轮次结果
    NEXT_ROUND_REQUEST = "NEXT_ROUND_REQUEST"     # 请求下一轮


class SlowPathEventType(StrEnum):
    """慢路径事件类型枚举。
    慢路径事件用于异步遥测、审计和报告，不阻塞核心执行流程。
    """
    DEFENSE_FEEDBACK = "DEFENSE_FEEDBACK"     # 防御反馈
    EVALUATION_METRIC = "EVALUATION_METRIC"   # 评估指标
    AUDIT_LOG = "AUDIT_LOG"                   # 审计日志
    MODEL_TRACE = "MODEL_TRACE"               # 模型追踪
    TOOL_TRACE = "TOOL_TRACE"                 # 工具追踪
    REPORT_EVENT = "REPORT_EVENT"             # 报告事件
    WEBSOCKET_EVENT = "WEBSOCKET_EVENT"       # WebSocket事件
    TASK_LIFECYCLE = "TASK_LIFECYCLE"         # 任务生命周期


@dataclass(slots=True)
class EventContext:
    """事件上下文，携带当前事件的任务、追踪、轮次和用例标识。
    字段说明:
        task_id: 任务ID
        trace_id: 追踪ID（关联同一请求链上的事件）
        round_id: 轮次ID（可选）
        attack_case_id: 攻击用例ID（可选）
    """
    task_id: str
    trace_id: str
    round_id: str | None = None
    attack_case_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """将事件上下文序列化为字典。"""
        return asdict(self)


@dataclass(slots=True)
class FastPathEvent:
    """快路径事件，用于同步驱动核心对抗流程。
    字段说明:
        event_type: 事件类型
        context: 事件上下文
        payload: 事件负载数据
        event_id: 事件唯一标识（自动生成UUID）
        created_at: 事件创建时间（UTC）
    """
    event_type: FastPathEventType
    context: EventContext
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """将快路径事件序列化为字典。"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "context": self.context.to_dict(),
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(slots=True)
class SlowPathEvent:
    """慢路径事件，用于异步遥测和审计。
    字段说明:
        event_type: 事件类型
        context: 事件上下文
        payload: 事件负载数据
        event_id: 事件唯一标识（自动生成UUID）
        created_at: 事件创建时间（UTC）
    """
    event_type: SlowPathEventType
    context: EventContext
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """将慢路径事件序列化为字典。"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "context": self.context.to_dict(),
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(slots=True)
class ToolFeedback:
    """工具调用反馈，描述蓝队对某次工具调用的判定结果。
    字段说明:
        tool_name: 工具名称
        decision: 判定结果（allow/block/degrade/not_reached）
        reason: 判定原因
        degraded_to: 降级后的替代参数（仅当decision=degrade时）
    """
    tool_name: str | None = None
    decision: Literal["allow", "block", "degrade", "not_reached"] = "not_reached"
    reason: str | None = None
    degraded_to: dict[str, Any] | None = None


@dataclass(slots=True)
class LayerFeedback:
    """防御层反馈，描述蓝队在某一防御层（输入/工具/输出）的判定结果。
    字段说明:
        decision: 判定结果（allow/block/degrade/not_reached）
        reason: 判定原因
        risk_type: 风险类型
    """
    decision: Literal["allow", "block", "degrade", "not_reached"] = "not_reached"
    reason: str | None = None
    risk_type: str | None = None


@dataclass(slots=True)
class RoundOutcome:
    """轮次结果，描述一次完整的红蓝对抗轮次的结果。
    字段说明:
        context: 事件上下文
        outcome: 结果类型（success/blocked/degraded/allowed_but_failed/partial_success）
        successful: 是否成功
        blocked: 是否被拦截
        stage: 最终阶段（input/tool_call/output/target_execution/round）
        action: 最终动作（allow/block/degrade/none）
        reason: 原因描述
        risk_type: 风险类型
        risk_level: 风险等级（low/medium/high/critical）
        confidence: 置信度（0-1）
        matched_policy_summary: 匹配的策略摘要
        successful_steps: 成功的步骤列表
        failed_step: 失败的步骤
        failed_objective: 失败的目标
        input_feedback: 输入层反馈
        tool_feedback: 工具层反馈
        output_feedback: 输出层反馈
        redteam_hint: 给红队的提示（用于下一轮变异）
        suggested_mutation_strategy: 建议的变异策略
    """
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
        """将轮次结果序列化为负载字典，用于事件传递。"""
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
        """将轮次结果转换为快路径事件，用于在快路径总线上发布。"""
        return FastPathEvent(
            event_type=FastPathEventType.ROUND_OUTCOME,
            context=self.context,
            payload=self.to_payload(),
        )


@dataclass(slots=True)
class DefenseFeedback:
    """防御反馈，描述蓝队防御组件对一次攻击的详细判定信息。
    字段说明:
        context: 事件上下文
        stage: 防御阶段
        action: 动作（allow/block/degrade/none）
        reason: 原因
        risk_type: 风险类型
        risk_level: 风险等级
        matched_rules: 匹配的规则列表
        confidence: 置信度
        detector_version: 检测器版本
        model_trace_id: 模型追踪ID
        tool_trace_id: 工具追踪ID
        latency_ms: 延迟（毫秒）
        raw_details: 原始细节
    """
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
        """将防御反馈序列化为负载字典。"""
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
        """将防御反馈转换为慢路径事件，用于异步遥测和审计。"""
        return SlowPathEvent(
            event_type=SlowPathEventType.DEFENSE_FEEDBACK,
            context=self.context,
            payload=self.to_payload(),
        )