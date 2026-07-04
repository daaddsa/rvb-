"""State models for red team attack workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


RiskLevel = Literal["low", "medium", "high", "critical"]
MutationStrategy = Literal[
    "semantic_rewrite",
    "objective_decomposition",
    "multi_turn_indirection",
    "lower_risk_tool_sequence",
    "role_context_shift",
]


@dataclass(slots=True)
class AttackTemplate:
    id: str
    risk_type: str
    skill_id: str
    prompt: str
    expected_violation: str
    severity: RiskLevel = "high"
    target_agent: str | None = None
    source: str = "base"
    status: str = "active"

    @classmethod
    def from_mapping(cls, risk_type: str, data: dict[str, Any]) -> "AttackTemplate":
        return cls(
            id=str(data.get("id") or f"{risk_type.lower()}_template"),
            risk_type=str(data.get("risk_type") or risk_type),
            skill_id=str(data.get("skill_id") or "prompt_injection"),
            prompt=str(data.get("prompt") or ""),
            expected_violation=str(data.get("expected_violation") or data.get("violation") or risk_type.lower()),
            severity=_normalize_severity(data.get("severity")),
            target_agent=data.get("target_agent"),
            source=str(data.get("source") or "base"),
            status=str(data.get("status") or "active"),
        )


def _normalize_severity(value: Any) -> RiskLevel:
    if value in {"low", "medium", "high", "critical"}:
        return value
    return "high"


@dataclass(slots=True)
class RuntimeMutation:
    parent_case_id: str
    mutation_strategy: MutationStrategy
    prompt: str
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)
