"""轻量级追踪（Tracing）辅助模块
提供TraceSpan和TraceRecorder，用于记录任务执行过程中的性能追踪数据。
支持上下文管理器（with语句）自动记录span的开始和结束。
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Iterator
from uuid import uuid4


@dataclass(slots=True)
class TraceSpan:
    """追踪跨度，表示一次操作的时间范围。
    字段说明:
        span_id: 跨度唯一标识
        trace_id: 追踪ID（关联同一请求链上的spans）
        name: 跨度名称（如"llm_call"、"db_query"等）
        task_id: 所属任务ID
        attack_case_id: 所属攻击用例ID
        parent_span_id: 父跨度ID（用于构建调用树）
        attributes: 自定义属性
        started_at: 开始时间
        ended_at: 结束时间
        duration_ms: 耗时（毫秒）
        status: 状态（OK/ERROR）
        error: 错误信息
    """
    span_id: str
    trace_id: str
    name: str
    task_id: str | None = None
    attack_case_id: str | None = None
    parent_span_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    duration_ms: float | None = None
    status: str = "OK"
    error: str | None = None

    def finish(self, *, status: str = "OK", error: str | None = None, started_perf: float | None = None) -> None:
        """标记跨度为完成状态，记录结束时间和耗时。
        参数:
            status: 完成状态，默认OK
            error: 错误信息（仅当status=ERROR时）
            started_perf: 性能计数器开始值，用于精确计算耗时
        """
        self.ended_at = datetime.now(timezone.utc)
        self.status = status
        self.error = error
        # 如果提供了perf_counter开始值，计算精确耗时
        if started_perf is not None:
            self.duration_ms = round((perf_counter() - started_perf) * 1000, 3)

    def to_dict(self) -> dict[str, Any]:
        """将追踪跨度序列化为字典。"""
        data = asdict(self)
        data["started_at"] = self.started_at.isoformat()
        data["ended_at"] = self.ended_at.isoformat() if self.ended_at else None
        return data


class TraceRecorder:
    """追踪记录器，管理一组TraceSpan。
    提供start_span方法创建span，以及span上下文管理器自动记录。
    """

    def __init__(self) -> None:
        self._spans: list[TraceSpan] = []

    @property
    def spans(self) -> list[TraceSpan]:
        """获取所有已记录的span副本。"""
        return list(self._spans)

    def start_span(
        self,
        name: str,
        *,
        trace_id: str | None = None,
        task_id: str | None = None,
        attack_case_id: str | None = None,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> TraceSpan:
        """创建并开始一个新的追踪跨度。
        参数:
            name: 跨度名称
            trace_id: 追踪ID，不提供则自动生成
            task_id: 任务ID
            attack_case_id: 攻击用例ID
            parent_span_id: 父跨度ID
            attributes: 自定义属性
        返回:
            TraceSpan: 新创建的跨度
        """
        span = TraceSpan(
            span_id=f"span_{uuid4().hex[:12]}",
            trace_id=trace_id or f"trace_{uuid4().hex[:12]}",
            name=name,
            task_id=task_id,
            attack_case_id=attack_case_id,
            parent_span_id=parent_span_id,
            attributes=attributes or {},
        )
        self._spans.append(span)
        return span

    @contextmanager
    def span(self, name: str, **kwargs: Any) -> Iterator[TraceSpan]:
        """上下文管理器：自动创建和完成span。
        用法:
            with recorder.span("llm_call", task_id="xxx") as span:
                # 执行操作
                ...
        参数:
            name: 跨度名称
            **kwargs: 传递给start_span的其他参数
        返回:
            Iterator[TraceSpan]: 追踪跨度生成器
        """
        started_perf = perf_counter()
        trace_span = self.start_span(name, **kwargs)
        try:
            yield trace_span
            # 正常完成
            trace_span.finish(started_perf=started_perf)
        except Exception as exc:
            # 异常完成，记录错误
            trace_span.finish(status="ERROR", error=str(exc), started_perf=started_perf)
            raise

    def export(self) -> list[dict[str, Any]]:
        """导出所有span为字典列表。
        返回:
            list[dict]: 所有span的序列化表示
        """
        return [span.to_dict() for span in self._spans]


def get_trace_recorder(state: dict[str, Any]) -> TraceRecorder:
    """从共享状态字典中获取或创建TraceRecorder。
    用于在任务执行上下文中共享同一个追踪记录器。
    参数:
        state: 共享状态字典
    返回:
        TraceRecorder: 追踪记录器实例
    """
    recorder = state.get("trace_recorder")
    if isinstance(recorder, TraceRecorder):
        return recorder
    # 不存在则创建新的并存入状态字典
    recorder = TraceRecorder()
    state["trace_recorder"] = recorder
    return recorder