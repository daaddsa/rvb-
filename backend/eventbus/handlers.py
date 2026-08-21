"""慢路径处理器注册辅助函数
提供处理器注册工具和内存遥测收集器（InMemoryTelemetrySink）。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .events import SlowPathEvent, SlowPathEventType
from .slow_path import SlowPathBus, SlowPathHandler


@dataclass(slots=True)
class InMemoryTelemetrySink:
    """内存遥测数据收集器，按事件类型分类存储慢路径事件。
    用于在不需要持久化时收集遥测数据，也可用于测试。
    字段说明:
        defense_feedback: 防御反馈事件列表
        evaluation_metrics: 评估指标事件列表
        audit_logs: 审计日志事件列表
        model_traces: 模型追踪事件列表
        tool_traces: 工具追踪事件列表
        report_events: 报告事件列表
        websocket_events: WebSocket事件列表
        task_lifecycle: 任务生命周期事件列表
        failures: 处理失败的事件列表
    """
    defense_feedback: list[dict[str, Any]] = field(default_factory=list)
    evaluation_metrics: list[dict[str, Any]] = field(default_factory=list)
    audit_logs: list[dict[str, Any]] = field(default_factory=list)
    model_traces: list[dict[str, Any]] = field(default_factory=list)
    tool_traces: list[dict[str, Any]] = field(default_factory=list)
    report_events: list[dict[str, Any]] = field(default_factory=list)
    websocket_events: list[dict[str, Any]] = field(default_factory=list)
    task_lifecycle: list[dict[str, Any]] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)

    def append(self, event: SlowPathEvent) -> None:
        """根据事件类型将事件追加到对应的分类列表中。
        参数:
            event: 慢路径事件
        """
        # 根据事件类型获取对应的存储桶名称
        target = _event_bucket_name(event.event_type)
        # 将事件序列化后追加到对应列表
        getattr(self, target).append(event.to_dict())

    def record_failure(self, event: SlowPathEvent, exc: Exception) -> None:
        """记录处理器失败的事件和异常信息。
        参数:
            event: 失败的事件
            exc: 异常对象
        """
        self.failures.append({"event": event.to_dict(), "error": str(exc)})


def register_handlers(
    bus: SlowPathBus,
    handlers: dict[SlowPathEventType, list[SlowPathHandler]],
    failure_handler: Callable[[SlowPathEvent, Exception], None] | None = None,
) -> SlowPathBus:
    """向慢路径总线注册一组处理器。
    参数:
        bus: 慢路径总线实例
        handlers: 按事件类型分组的处理器字典
        failure_handler: 可选的失败回调函数
    返回:
        SlowPathBus: 注册后的总线实例（与传入的bus是同一个）
    """
    # 遍历每种事件类型，注册对应的处理器列表
    for event_type, event_handlers in handlers.items():
        for handler in event_handlers:
            bus.subscribe(event_type, handler)

    # 如果提供了失败回调，则注册
    if failure_handler is not None:
        bus.on_failure(failure_handler)

    return bus


def register_default_handlers(bus: SlowPathBus, sink: InMemoryTelemetrySink | None = None) -> InMemoryTelemetrySink:
    """注册默认处理器：将所有慢路径事件收集到InMemoryTelemetrySink中。
    参数:
        bus: 慢路径总线实例
        sink: 可选的遥测收集器，不提供则创建新的
    返回:
        InMemoryTelemetrySink: 注册后的遥测收集器
    """
    # 使用传入的收集器或创建新的
    telemetry_sink = sink or InMemoryTelemetrySink()
    # 订阅所有慢路径事件类型到收集器的append方法
    for event_type in SlowPathEventType:
        bus.subscribe(event_type, telemetry_sink.append)
    # 注册失败回调
    bus.on_failure(telemetry_sink.record_failure)
    return telemetry_sink


def _event_bucket_name(event_type: SlowPathEventType) -> str:
    """将慢路径事件类型映射到InMemoryTelemetrySink中对应的存储桶属性名。
    参数:
        event_type: 慢路径事件类型枚举值
    返回:
        str: 对应的属性名字符串
    """
    return {
        SlowPathEventType.DEFENSE_FEEDBACK: "defense_feedback",
        SlowPathEventType.EVALUATION_METRIC: "evaluation_metrics",
        SlowPathEventType.AUDIT_LOG: "audit_logs",
        SlowPathEventType.MODEL_TRACE: "model_traces",
        SlowPathEventType.TOOL_TRACE: "tool_traces",
        SlowPathEventType.REPORT_EVENT: "report_events",
        SlowPathEventType.WEBSOCKET_EVENT: "websocket_events",
        SlowPathEventType.TASK_LIFECYCLE: "task_lifecycle",
    }[event_type]