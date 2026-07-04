"""Shared sandbox contracts for target tool execution."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, Literal

SandboxDecision = Literal["allow", "block", "degrade"]
ToolFunction = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(slots=True)
class SandboxContext:
    task_id: str
    trace_id: str
    attack_case_id: str
    target_agent: str
    user_role: str = "guest"


@dataclass(slots=True)
class ToolCallPlan:
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SandboxPolicyDecision:
    action: SandboxDecision
    reason: str
    degraded_to: ToolCallPlan | None = None


@dataclass(slots=True)
class SandboxExecutionResult:
    tool_name: str
    action: SandboxDecision
    allowed: bool
    output: dict[str, Any] | None = None
    reason: str | None = None
    degraded_to: str | None = None


class ToolExecutor(Protocol):
    def execute(self, context: SandboxContext, tool_call: ToolCallPlan) -> SandboxExecutionResult:
        ...


class ToolRegistry:
    def __init__(self, tools: Mapping[str, ToolFunction] | None = None) -> None:
        self._tools: dict[str, ToolFunction] = dict(tools or {})

    def register(self, name: str, tool: ToolFunction) -> None:
        self._tools[name] = tool

    def get(self, name: str) -> ToolFunction | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)
