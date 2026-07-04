"""Reserved WebAssembly executor interface for future isolated tools."""

from __future__ import annotations

from pathlib import Path

from backend.targets.sandbox.contracts import SandboxContext, SandboxExecutionResult, ToolCallPlan


class WasmToolExecutor:
    def __init__(self, plugin_dir: str | Path) -> None:
        self.plugin_dir = Path(plugin_dir)

    def execute(self, context: SandboxContext, tool_call: ToolCallPlan) -> SandboxExecutionResult:
        return SandboxExecutionResult(
            tool_name=tool_call.tool_name,
            action="block",
            allowed=False,
            reason="WASM sandbox executor is reserved but not enabled in MVP",
        )
