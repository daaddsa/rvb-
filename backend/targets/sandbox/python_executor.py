"""Python tool executor used by the MVP sandbox.
Python 工具执行器，在沙箱中执行注册的工具函数。
"""

from __future__ import annotations

from backend.targets.sandbox.contracts import SandboxContext, SandboxExecutionResult, ToolCallPlan, ToolRegistry


class PythonToolExecutor:
    """Python 工具执行器：从 ToolRegistry 中查找工具函数并执行。"""

    def __init__(self, registry: ToolRegistry) -> None:
        """初始化执行器。
        参数：
            registry: 工具注册表
        """
        self.registry = registry

    def execute(self, context: SandboxContext, tool_call: ToolCallPlan) -> SandboxExecutionResult:
        """执行工具调用。
        参数：
            context: 沙箱上下文
            tool_call: 工具调用计划
        返回：
            SandboxExecutionResult：包含执行结果或错误信息
        """
        # 从注册表中查找工具
        tool = self.registry.get(tool_call.tool_name)
        # 如果工具未注册，返回阻断结果
        if tool is None:
            return SandboxExecutionResult(
                tool_name=tool_call.tool_name,
                action="block",
                allowed=False,
                reason="Tool is not registered in sandbox",
            )

        # 执行工具函数并返回结果
        output = tool(tool_call.arguments)
        return SandboxExecutionResult(
            tool_name=tool_call.tool_name,
            action="allow",
            allowed=True,
            output={"context": {"task_id": context.task_id, "trace_id": context.trace_id}, "result": output},
            reason="Tool executed by Python sandbox executor",
        )