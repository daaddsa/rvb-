"""慢路径异步总线
用于异步遥测和审计事件处理，不阻塞核心对抗执行流程。
支持同步和异步处理器，通过后台任务异步执行。
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import TypeAlias

from .events import SlowPathEvent, SlowPathEventType

# 同步慢路径处理器：接收SlowPathEvent，无返回值
SyncSlowPathHandler: TypeAlias = Callable[[SlowPathEvent], None]
# 异步慢路径处理器：接收SlowPathEvent，返回可等待对象
AsyncSlowPathHandler: TypeAlias = Callable[[SlowPathEvent], Awaitable[None]]
# 慢路径处理器联合类型
SlowPathHandler: TypeAlias = SyncSlowPathHandler | AsyncSlowPathHandler


class SlowPathBus:
    """异步事件总线，用于遥测和审计，不得阻塞核心执行路径。
    支持同步和异步处理器，自动检测运行事件循环并创建后台任务。
    """

    def __init__(self) -> None:
        # 按事件类型分组的处理器列表字典
        self._handlers: dict[SlowPathEventType, list[SlowPathHandler]] = defaultdict(list)
        # 处理器失败时的回调函数
        self._failure_handler: Callable[[SlowPathEvent, Exception], None] | None = None
        # 事件历史记录列表
        self._history: list[SlowPathEvent] = []
        # 后台异步任务集合，用于追踪未完成的处理器任务
        self._background_tasks: set[asyncio.Task] = set()

    @property
    def history(self) -> list[SlowPathEvent]:
        """获取事件历史记录的副本。"""
        return list(self._history)

    def subscribe(self, event_type: SlowPathEventType, handler: SlowPathHandler) -> None:
        """订阅指定事件类型，注册处理器（同步或异步均可）。
        参数:
            event_type: 要订阅的事件类型
            handler: 事件处理器函数
        """
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: SlowPathEventType, handler: SlowPathHandler) -> None:
        """取消订阅指定事件类型和处理器。
        参数:
            event_type: 事件类型
            handler: 要移除的处理器
        """
        if handler in self._handlers.get(event_type, []):
            self._handlers[event_type].remove(handler)

    def on_failure(self, handler: Callable[[SlowPathEvent, Exception], None]) -> None:
        """注册处理器失败时的回调函数。
        参数:
            handler: 失败回调函数，接收失败的事件和异常
        """
        self._failure_handler = handler

    def publish(self, event: SlowPathEvent) -> None:
        """发布事件，在后台异步执行所有订阅的处理器。
        如果在已有事件循环中运行，则创建后台任务；
        如果不在事件循环中，则使用asyncio.run同步执行。
        参数:
            event: 要发布的慢路径事件
        """
        # 记录到历史
        self._history.append(event)
        handlers = self._handlers.get(event.event_type, [])
        # 尝试获取当前运行的事件循环
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # 不在事件循环中（如后台线程），使用asyncio.run同步执行
            asyncio.run(self.publish_and_wait(event, record_history=False))
            return

        # 在事件循环中：为每个处理器创建后台任务
        for handler in handlers:
            task = loop.create_task(self._run_handler(handler, event))
            # 追踪后台任务，完成时自动移除
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    async def publish_and_wait(self, event: SlowPathEvent, *, record_history: bool = True) -> None:
        """发布事件并等待所有处理器执行完成。
        参数:
            event: 要发布的慢路径事件
            record_history: 是否记录到历史（默认True）
        """
        if record_history:
            self._history.append(event)
        handlers = self._handlers.get(event.event_type, [])
        # 并发执行所有处理器并等待完成
        await asyncio.gather(*(self._run_handler(handler, event) for handler in handlers))

    async def drain(self) -> None:
        """等待所有后台任务完成，用于优雅关闭时确保遥测数据不丢失。"""
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

    def clear_history(self) -> None:
        """清空事件历史记录。"""
        self._history.clear()

    async def _run_handler(self, handler: SlowPathHandler, event: SlowPathEvent) -> None:
        """执行单个处理器，捕获并记录异常。
        参数:
            handler: 处理器函数
            event: 要处理的事件
        """
        try:
            result = handler(event)
            # 如果处理器返回可等待对象（即异步处理器），await它
            if hasattr(result, "__await__"):
                await result
        except Exception as exc:  # Slow Path failures are telemetry-only.（慢路径失败仅影响遥测，不阻塞主流程）
            # 如果配置了失败处理器，则调用它
            if self._failure_handler is not None:
                self._failure_handler(event, exc)