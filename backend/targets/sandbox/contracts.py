"""Shared sandbox contracts for target tool execution.
沙箱共享契约，定义目标工具执行相关的数据结构和接口。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, Literal

# 沙箱决策类型：允许 / 阻断 / 降级
SandboxDecision = Literal["allow", "block", "degrade"]
# 工具函数签名：接收参数字典，返回结果字典
ToolFunction = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(slots=True)
class SandboxContext:
    """沙箱执行上下文。
    包含任务标识、追踪信息和目标智能体信息。
    """
    task_id: str  # 任务标识
    trace_id: str  # 链路追踪ID
    attack_case_id: str  # 攻击用例ID
    target_agent: str  # 目标智能体名称
    user_role: str = "guest"  # 用户角色，默认为 guest


@dataclass(slots=True)
class ToolCallPlan:
    """工具调用计划。
    描述目标智能体计划调用的工具及参数。
    """
    tool_name: str  # 工具名称
    arguments: dict[str, Any] = field(default_factory=dict)  # 工具参数


@dataclass(slots=True)
class SandboxPolicyDecision:
    """沙箱策略决策。
    定义沙箱对工具调用的策略决策结果。
    """
    action: SandboxDecision  # 决策动作：allow / block / degrade
    reason: str  # 决策理由
    degraded_to: ToolCallPlan | None = None  # 降级后的工具调用方案


@dataclass(slots=True)
class SandboxExecutionResult:
    """沙箱执行结果。
    记录工具在沙箱中的执行结果。
    """
    tool_name: str  # 工具名称
    action: SandboxDecision  # 执行动作
    allowed: bool  # 是否允许执行
    output: dict[str, Any] | None = None  # 执行输出
    reason: str | None = None  # 执行理由
    degraded_to: str | None = None  # 降级后的工具名称


class ToolExecutor(Protocol):
    """工具执行器协议接口。
    所有工具执行器必须实现 execute 方法。
    """
    def execute(self, context: SandboxContext, tool_call: ToolCallPlan) -> SandboxExecutionResult:
        ...


class ToolRegistry:
    """工具注册表：管理工具的注册和查找。"""

    def __init__(self, tools: Mapping[str, ToolFunction] | None = None) -> None:
        """初始化工具注册表。
        参数：
            tools: 工具名称到函数映射
        """
        self._tools: dict[str, ToolFunction] = dict(tools or {})

    def register(self, name: str, tool: ToolFunction) -> None:
        """注册一个新工具。
        参数：
            name: 工具名称
            tool: 工具函数
        """
        self._tools[name] = tool

    def get(self, name: str) -> ToolFunction | None:
        """根据名称查找工具。
        参数：
            name: 工具名称
        返回：
            工具函数，如果未注册则返回 None
        """
        return self._tools.get(name)

    def names(self) -> list[str]:
        """获取所有已注册工具的名称列表。
        返回：
            排序后的工具名称列表
        """
        return sorted(self._tools)