"""Python tool executor used by the MVP sandbox."""

from __future__ import annotations

from backend.targets.sandbox.contracts import SandboxContext, SandboxExecutionResult, ToolCallPlan, ToolRegistry


class PythonToolExecutor:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def execute(self, context: SandboxContext, tool_call: ToolCallPlan) -> SandboxExecutionResult:
        tool = self.registry.get(tool_call.tool_name)
        if tool is None:
            return SandboxExecutionResult(
                tool_name=tool_call.tool_name,
                action="block",
                allowed=False,
                reason="Tool is not registered in sandbox",
            )

        output = tool(tool_call.arguments)
        return SandboxExecutionResult(
            tool_name=tool_call.tool_name,
            action="allow",
            allowed=True,
            output={"context": {"task_id": context.task_id, "trace_id": context.trace_id}, "result": output},
            reason="Tool executed by Python sandbox executor",
        )
