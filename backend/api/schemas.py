"""Request and response schemas for API boundaries."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.config.settings import get_settings
from backend.storage.schemas import (
    AttackCaseSchema,
    AuditEventSchema,
    DetectionResultSchema,
    EvaluationReportSchema,
    TaskSchema,
)


class TaskModelConfig(BaseModel):
    target_model: str | None = None


settings = get_settings()


class TaskCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    target_agent: str
    risk_types: list[str] = Field(default_factory=list)
    attack_skills: list[str] = Field(default_factory=list)
    attack_count: int = Field(default=5, ge=1)
    max_rounds: int = Field(default_factory=lambda: settings.default_max_rounds, ge=1)
    use_llm: bool = True
    llm_models: TaskModelConfig = Field(default_factory=TaskModelConfig, alias="model_config")
    redbench_datasets: list[str] = Field(default_factory=list)
    matrix_version: str = "ASI_2026"


class RedBenchDatasetsResponse(BaseModel):
    datasets: list[str]


class TaskCreateResponse(BaseModel):
    task_id: str
    status: str
    matrix_version: str


class TaskStartResponse(BaseModel):
    task_id: str
    status: str


class TaskListResponse(BaseModel):
    tasks: list[TaskSchema]


class MutationTaskSchema(BaseModel):
    id: str
    parent_attack_case_id: str
    result_attack_case_id: str | None = None
    source_prompt: str
    mutated_prompt: str | None = None
    mutation_strategy: str | None = None
    failure_stage: str | None = None
    failure_reason: str | None = None
    status: str
    next_round: int
    queued_at: datetime
    completed_at: datetime | None = None


class TaskDetailResponse(BaseModel):
    task: TaskSchema
    attack_cases: list[AttackCaseSchema] = Field(default_factory=list)
    mutation_tasks: list[MutationTaskSchema] = Field(default_factory=list)
    detection_results: list[DetectionResultSchema] = Field(default_factory=list)
    report: EvaluationReportSchema | None = None


class TaskEventsResponse(BaseModel):
    events: list[AuditEventSchema]


class TaskReportResponse(BaseModel):
    report: EvaluationReportSchema | None = None
    message: str | None = None


class ErrorResponse(BaseModel):
    detail: str | dict[str, Any]
