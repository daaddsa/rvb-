"""Sandbox runtime for target agents and tools.
沙箱运行时，管理工具执行的策略检查和安全决策。
"""

from __future__ import annotations

from collections.abc import Callable

from backend.targets.sandbox.contracts import (
    SandboxContext,
    SandboxExecutionResult,
    SandboxPolicyDecision,
    ToolCallPlan,
    ToolExecutor,
)

# 策略检查器函数签名：接收沙箱上下文和工具调用，返回策略决策
PolicyChecker = Callable[[SandboxContext, ToolCallPlan], SandboxPolicyDecision]


def allow_all_policy(context: SandboxContext, tool_call: ToolCallPlan) -> SandboxPolicyDecision:
    """默认策略：允许所有工具调用。
    参数：
        context: 沙箱上下文
        tool_call: 工具调用计划
    返回：
        SandboxPolicyDecision：总是允许
    """
    return SandboxPolicyDecision(action="allow", reason="Default sandbox policy allowed the tool call")


class SandboxRuntime:
    """沙箱运行时：在执行工具前进行策略检查，支持阻断和降级。"""

    def __init__(self, executor: ToolExecutor, policy_checker: PolicyChecker = allow_all_policy) -> None:
        """初始化沙箱运行时。
        参数：
            executor: 工具执行器
            policy_checker: 策略检查函数，默认为全部允许
        """
        self.executor = executor
        self.policy_checker = policy_checker

    def execute_tool(self, context: SandboxContext, tool_call: ToolCallPlan) -> SandboxExecutionResult:
        """执行工具调用：先进行策略检查，再根据决策执行。
        参数：
            context: 沙箱上下文
            tool_call: 工具调用计划
        返回：
            SandboxExecutionResult 执行结果
        """
        decision = self.policy_checker(context, tool_call)
        # 策略阻断：直接返回阻断结果
        if decision.action == "block":
            return SandboxExecutionResult(
                tool_name=tool_call.tool_name,
                action="block",
                allowed=False,
                reason=decision.reason,
            )

        # 策略降级：执行降级后的工具
        if decision.action == "degrade" and decision.degraded_to is not None:
            result = self.executor.execute(context, decision.degraded_to)
            result.action = "degrade"
            result.degraded_to = decision.degraded_to.tool_name
            result.reason = decision.reason
            return result

        # 策略允许：正常执行
        return self.executor.execute(context, tool_call)