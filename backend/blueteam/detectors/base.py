"""Shared blue-team detector primitives.
蓝队检测器共享基类，提供规则检测和模型检测的并发执行框架。
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from backend.eventbus import EventContext, SlowPathBus, SlowPathEvent, SlowPathEventType

# 类型别名定义
RiskLevel = Literal["low", "medium", "high", "critical"]  # 风险等级
DecisionAction = Literal["allow", "block", "degrade"]  # 决策动作
DetectorKind = Literal["input", "output"]  # 检测器类型


@dataclass(slots=True)
class DetectionResult:
    """检测结果数据类。
    包含检测动作、风险等级、风险和理由等字段。
    """
    action: DecisionAction  # 决策动作：allow / block / degrade
    risk_level: RiskLevel | None = None  # 风险等级
    risk_type: str | None = None  # 风险类型
    reason: str | None = None  # 检测理由
    confidence: float | None = None  # 置信度（0-1）
    matched_rules: list[str] = field(default_factory=list)  # 命中的规则ID列表
    metadata: dict[str, Any] = field(default_factory=dict)  # 附加元数据

    @property
    def is_high_risk_block(self) -> bool:
        """判断是否为高风险阻断：action=block 且 risk_level 为 high 或 critical"""
        return self.action == "block" and self.risk_level in {"high", "critical"}


# 检测器函数类型别名
RuleDetector: Callable[[dict[str, Any]], Awaitable[DetectionResult]]  # 规则检测器
ModelDetector: Callable[[dict[str, Any]], Awaitable[DetectionResult]]  # 模型检测器


def normalize_detection_result(result: DetectionResult) -> DetectionResult:
    """规范化检测结果：高风险（high/critical）但未阻断的，自动升级为阻断。
    参数：
        result: 原始检测结果
    返回：
        规范化后的检测结果，高风险自动升级为 block
    """
    if result.risk_level in {"high", "critical"} and result.action != "block":
        reason = result.reason or "命中高风险策略，系统自动升级为阻断"
        metadata = dict(result.metadata)
        metadata["escalated_from_action"] = result.action  # 记录原始动作
        return replace(result, action="block", reason=reason, metadata=metadata)
    return result


class ConcurrentDetector:
    """并发检测器基类：规则检测和模型检测并行执行。
    规则检测优先：如果规则检测到高风险阻断，则取消模型检测任务。
    """

    def __init__(
        self,
        *,
        detector_kind: DetectorKind,
        model_name: str,
        rule_detector: RuleDetector,
        model_detector: ModelDetector,
        slow_path: SlowPathBus | None = None,
    ) -> None:
        """初始化并发检测器。
        参数：
            detector_kind: 检测器类型：input / output
            model_name: 模型名称
            rule_detector: 规则检测函数
            model_detector: 模型检测函数
            slow_path: 慢速通道事件总线
        """
        self.detector_kind = detector_kind
        self.model_name = model_name
        self.rule_detector = rule_detector
        self.model_detector = model_detector
        self.slow_path = slow_path

    async def detect(self, payload: dict[str, Any], context: EventContext) -> DetectionResult:
        """并发执行规则检测和模型检测。
        参数：
            payload: 检测数据（prompt 或 output）
            context: 事件上下文
        返回：
            合并后的检测结果
        """
        # 创建两个并发任务
        rule_task = asyncio.create_task(self.rule_detector(payload))
        model_task = asyncio.create_task(self.model_detector(payload))

        # 等待规则检测结果
        rule_result = normalize_detection_result(await rule_task)
        # 如果规则检测到高风险阻断，取消模型检测（短路优化）
        if rule_result.is_high_risk_block:
            model_task.cancel()
            await self._record_model_cancelled(context, rule_result)  # 记录模型取消事件
            return rule_result

        # 等待模型检测结果
        try:
            model_result = normalize_detection_result(await model_task)
        except asyncio.CancelledError:
            raise  # 正常传播取消异常

        # 合并两个检测结果
        return self._merge_results(rule_result, model_result)

    async def _record_model_cancelled(self, context: EventContext, rule_result: DetectionResult) -> None:
        """记录模型检测被取消的事件（因规则已命中高风险）。
        参数：
            context: 事件上下文
            rule_result: 规则检测结果
        """
        if self.slow_path is None:
            return  # 没有慢速通道则跳过

        event = SlowPathEvent(
            event_type=SlowPathEventType.MODEL_TRACE,
            context=context,
            payload={
                "detector_kind": self.detector_kind,
                "model_name": self.model_name,
                "status": "cancelled_by_rule_hit",  # 因规则命中而取消
                "matched_rules": rule_result.matched_rules,
                "risk_level": rule_result.risk_level,
                "risk_type": rule_result.risk_type,
                "reason": rule_result.reason,
            },
        )
        await self.slow_path.publish_and_wait(event)

    def _merge_results(self, rule_result: DetectionResult, model_result: DetectionResult) -> DetectionResult:
        """合并规则检测和模型检测的结果。
        优先级：模型阻断 > 规则阻断 > 模型降级 > 规则降级 > 模型结果（有置信度）> 规则结果
        参数：
            rule_result: 规则检测结果
            model_result: 模型检测结果
        返回：
            合并后的检测结果
        """
        if model_result.action == "block":
            return model_result  # 模型阻断优先级最高
        if rule_result.action == "block":
            return rule_result
        if model_result.action == "degrade":
            return model_result
        if rule_result.action == "degrade":
            return rule_result
        # 都放行时，优先返回有置信度的模型结果
        return model_result if model_result.confidence else rule_result