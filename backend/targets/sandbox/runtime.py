"""Sandbox runtime for target agents and tools."""

from __future__ import annotations

from collections.abc import Callable

from backend.targets.sandbox.contracts import (
    SandboxContext,
    SandboxExecutionResult,
    SandboxPolicyDecision,
    ToolCallPlan,
    ToolExecutor,
)

PolicyChecker = Callable[[SandboxContext, ToolCallPlan], SandboxPolicyDecision]


def allow_all_policy(context: SandboxContext, tool_call: ToolCallPlan) -> SandboxPolicyDecision:
    return SandboxPolicyDecision(action="allow", reason="Default sandbox policy allowed the tool call")


class SandboxRuntime:
    def __init__(self, executor: ToolExecutor, policy_checker: PolicyChecker = allow_all_policy) -> None:
        self.executor = executor
        self.policy_checker = policy_checker

    def execute_tool(self, context: SandboxContext, tool_call: ToolCallPlan) -> SandboxExecutionResult:
        decision = self.policy_checker(context, tool_call)
        if decision.action == "block":
            return SandboxExecutionResult(
                tool_name=tool_call.tool_name,
                action="block",
                allowed=False,
                reason=decision.reason,
            )

        if decision.action == "degrade" and decision.degraded_to is not None:
            result = self.executor.execute(context, decision.degraded_to)
            result.action = "degrade"
            result.degraded_to = decision.degraded_to.tool_name
            result.reason = decision.reason
            return result

        return self.executor.execute(context, tool_call)
