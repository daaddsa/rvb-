"""Reserved WebAssembly executor interface for future isolated tools.
预留的 WebAssembly 执行器接口，用于未来隔离执行工具的场景。
"""

from __future__ import annotations

from pathlib import Path

from backend.targets.sandbox.contracts import SandboxContext, SandboxExecutionResult, ToolCallPlan


class WasmToolExecutor:
    """WASM 工具执行器：预留接口，当前 MVP 版本禁用。"""

    def __init__(self, plugin_dir: str | Path) -> None:
        """初始化 WASM 执行器。
        参数：
            plugin_dir: WASM 插件目录路径
        """
        self.plugin_dir = Path(plugin_dir)

    def execute(self, context: SandboxContext, tool_call: ToolCallPlan) -> SandboxExecutionResult:
        """执行工具调用（当前版本返回阻断）。
        参数：
            context: 沙箱上下文
            tool_call: 工具调用计划
        返回：
            SandboxExecutionResult：总是返回阻断
        """
        return SandboxExecutionResult(
            tool_name=tool_call.tool_name,
            action="block",
            allowed=False,
            reason="WASM sandbox executor is reserved but not enabled in MVP",
        )