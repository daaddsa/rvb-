"""快路径同步总线
用于同步驱动红蓝对抗的核心执行流程，所有处理器必须同步执行。
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import TypeAlias

from .events import FastPathEvent, FastPathEventType, RoundOutcome

# 快路径处理器类型别名：接收FastPathEvent，返回FastPathEvent或RoundOutcome或None
FastPathHandler: TypeAlias = Callable[[FastPathEvent], FastPathEvent | RoundOutcome | None]


class FastPathBus:
    """同步事件总线，驱动红蓝对抗执行路径。
    提供事件的订阅、发布和历史记录功能。
    所有处理器在调用线程中同步执行。
    """

    def __init__(self) -> None:
        # 按事件类型分组的处理器列表字典
        self._handlers: dict[FastPathEventType, list[FastPathHandler]] = defaultdict(list)
        # 事件历史记录列表
        self._history: list[FastPathEvent] = []

    @property
    def history(self) -> list[FastPathEvent]:
        """获取事件历史记录的副本。"""
        return list(self._history)

    def subscribe(self, event_type: FastPathEventType, handler: FastPathHandler) -> None:
        """订阅指定事件类型，注册处理器。
        参数:
            event_type: 要订阅的事件类型
            handler: 事件处理器函数
        """
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: FastPathEventType, handler: FastPathHandler) -> None:
        """取消订阅指定事件类型和处理器。
        参数:
            event_type: 事件类型
            handler: 要移除的处理器
        """
        if handler in self._handlers.get(event_type, []):
            self._handlers[event_type].remove(handler)

    def publish(self, event: FastPathEvent) -> list[FastPathEvent | RoundOutcome]:
        """发布事件，调用所有订阅该事件类型的处理器。
        参数:
            event: 要发布的快路径事件
        返回:
            list: 所有处理器的返回值（非None）列表
        """
        # 记录到历史
        self._history.append(event)
        results: list[FastPathEvent | RoundOutcome] = []
        # 遍历该事件类型的所有处理器并调用
        for handler in self._handlers.get(event.event_type, []):
            result = handler(event)
            # 如果处理器返回了结果（非None），收集到列表中
            if result is not None:
                results.append(result)
        return results

    def publish_until_outcome(self, event: FastPathEvent) -> RoundOutcome | None:
        """发布事件，依次调用处理器直到某个处理器返回RoundOutcome。
        用于需要尽早得到轮次结果的场景。
        参数:
            event: 要发布的快路径事件
        返回:
            RoundOutcome | None: 第一个返回RoundOutcome的处理器结果，若没有则返回None
        """
        # 记录到历史
        self._history.append(event)
        # 遍历处理器，遇到RoundOutcome则立即返回
        for handler in self._handlers.get(event.event_type, []):
            result = handler(event)
            if isinstance(result, RoundOutcome):
                return result
        return None

    def clear_history(self) -> None:
        """清空事件历史记录。"""
        self._history.clear()