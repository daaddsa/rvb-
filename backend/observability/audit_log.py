"""追加式审计日志辅助模块
提供AuditLogRecord和AuditTrail，用于记录攻击证据链。
支持构建审计记录、追加到审计追踪、导出为字典列表。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class AuditLogRecord:
    """审计日志记录，表示一次攻击事件的关键信息。
    字段说明:
        id: 记录唯一标识
        task_id: 所属任务ID
        event_type: 事件类型
        trace_id: 追踪ID
        attack_case_id: 关联攻击用例ID
        event_topic: 事件主题（FAST_PATH/SLOW_PATH）
        agent: 相关智能体
        tool_name: 相关工具名称
        payload: 事件负载数据
        allowed: 是否被允许
        risk_level: 风险等级
        risk_type: 风险类型
        message: 事件消息
        created_at: 创建时间（UTC）
    """
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
        """将审计记录序列化为字典。"""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


class AuditTrail:
    """审计追踪，维护一个追加式（append-only）的审计记录列表。
    支持追加单条记录、批量扩展和导出。
    """

    def __init__(self) -> None:
        self._records: list[AuditLogRecord] = []

    @property
    def records(self) -> list[AuditLogRecord]:
        """获取所有审计记录的副本。"""
        return list(self._records)

    def append(self, record: AuditLogRecord | dict[str, Any]) -> AuditLogRecord:
        """追加一条审计记录。
        参数:
            record: AuditLogRecord实例或字典（将自动构建为AuditLogRecord）
        返回:
            AuditLogRecord: 添加的审计记录
        """
        # 如果是字典，则通过build_audit_record构建
        audit_record = record if isinstance(record, AuditLogRecord) else build_audit_record(**record)
        self._records.append(audit_record)
        return audit_record

    def extend(self, records: list[AuditLogRecord | dict[str, Any]]) -> None:
        """批量追加多条审计记录。
        参数:
            records: 审计记录列表
        """
        for record in records:
            self.append(record)

    def export(self) -> list[dict[str, Any]]:
        """导出所有审计记录为字典列表。
        返回:
            list[dict]: 所有记录的序列化表示
        """
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
    """构建审计记录，自动生成ID和默认事件主题。
    参数:
        task_id: 任务ID（必填）
        event_type: 事件类型（必填）
        trace_id: 追踪ID
        attack_case_id: 攻击用例ID
        event_topic: 事件主题，不提供则根据event_type自动推断
        agent: 智能体类型
        tool_name: 工具名称
        payload: 负载数据
        allowed: 是否允许
        risk_level: 风险等级
        risk_type: 风险类型
        message: 消息
        id: 记录ID，不提供则自动生成UUID
        **_: 忽略额外的未知字段
    返回:
        AuditLogRecord: 构建好的审计记录
    """
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
    """从共享状态字典中获取或创建AuditTrail。
    用于在任务执行上下文中共享同一个审计追踪。
    参数:
        state: 共享状态字典
    返回:
        AuditTrail: 审计追踪实例
    """
    trail = state.get("audit_trail")
    if isinstance(trail, AuditTrail):
        return trail
    # 不存在则创建新的并存入状态字典
    trail = AuditTrail()
    state["audit_trail"] = trail
    return trail


def _default_topic(event_type: str) -> str:
    """根据事件类型推断默认事件主题。
    评估指标、报告事件、模型追踪和工具追踪归为SLOW_PATH；
    其余归为FAST_PATH。
    参数:
        event_type: 事件类型字符串
    返回:
        str: 默认事件主题
    """
    if event_type in {"EVALUATION_METRIC", "REPORT_EVENT", "MODEL_TRACE", "TOOL_TRACE"}:
        return "SLOW_PATH"
    return "FAST_PATH"