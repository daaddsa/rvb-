"""Runtime state for the MVP red-blue orchestration flow."""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class AttackCaseState(TypedDict, total=False):
    id: str
    risk_chain_id: str
    round_no: int
    skill_id: str
    risk_type: str
    target_agent: str
    prompt: str
    expected_violation: str
    severity: str
    parent_case_id: str | None
    mutation_strategy: str | None
    metadata: dict[str, Any]


class RoundResultState(TypedDict, total=False):
    attack_case_id: str
    trace_id: str
    stage: str
    action: Literal["allow", "block", "degrade"]
    successful: bool
    blocked: bool
    risk_type: str | None
    risk_level: str | None
    reason: str
    target_output: str | None
    redteam_hint: str | None
    suggested_mutation_strategy: list[str]
    round_no: int


class MutationTaskState(TypedDict, total=False):
    parent_case: AttackCaseState
    outcome: RoundResultState
    next_round: int
    mutation_strategy: str


class AttackTaskState(TypedDict, total=False):
    task_id: str
    target_agent: str
    risk_types: list[str]
    attack_skills: list[str]
    attack_count: int
    max_rounds: int
    matrix_version: str
    model_config: dict[str, Any]
    red_model: str
    target_model: str
    blue_model: str
    eval_model: str
    redbench_datasets: list[str]
    attack_cases: list[AttackCaseState]
    mutation_tasks: list[MutationTaskState]
    round_results: list[RoundResultState]
    evaluation_result: dict[str, Any]
    audit_events: list[dict[str, Any]]
    status: str
    error: str | None
