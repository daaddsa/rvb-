"""持久化层Pydantic Schema
定义与数据库ORM模型对应的Pydantic数据模型，用于序列化和API响应。
通过from_attributes=True配置使Pydantic能直接从SQLAlchemy ORM对象创建实例。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskSchema(BaseModel):
    """任务数据Schema，对应Task表。
    字段说明:
        llm_models: 模型配置字典，别名model_config对应数据库中的model_config列
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    status: str
    target_agent: str
    risk_types: list[str]
    attack_skills: list[str]
    attack_count: int
    current_round: int
    max_rounds: int
    use_llm: bool
    llm_models: dict[str, Any] = Field(default_factory=dict, alias="model_config")
    red_model: str | None = None
    target_model: str | None = None
    blue_model: str | None = None
    eval_model: str | None = None
    matrix_version: str
    created_at: datetime
    updated_at: datetime
    error: str | None = None


class AttackCaseSchema(BaseModel):
    """攻击用例Schema，对应AttackCase表。"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    risk_chain_id: str | None = None
    round_no: int
    skill_id: str | None = None
    risk_type: str | None = None
    target_agent: str
    prompt: str
    expected_violation: str | None = None
    severity: str | None = None
    model_name: str | None = None
    parent_case_id: str | None = None
    mutation_strategy: str | None = None
    created_at: datetime


class DetectionResultSchema(BaseModel):
    """检测结果Schema，对应DetectionResultRecord表。"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    attack_case_id: str | None = None
    stage: str
    detector: str
    model_name: str | None = None
    detected: bool
    blocked: bool
    action: str
    risk_level: str | None = None
    risk_type: str | None = None
    reason: str | None = None
    confidence: float | None = None
    raw_output: dict[str, Any]
    created_at: datetime


class AuditEventSchema(BaseModel):
    """审计事件Schema，对应AuditEvent表。"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    attack_case_id: str | None = None
    trace_id: str | None = None
    event_type: str
    event_topic: str | None = None
    agent: str | None = None
    tool_name: str | None = None
    payload: dict[str, Any]
    allowed: bool | None = None
    risk_level: str | None = None
    risk_type: str | None = None
    message: str | None = None
    created_at: datetime


class EvaluationReportSchema(BaseModel):
    """评估报告Schema，对应EvaluationReport表。"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    total_attacks: int
    successful_attacks: int
    detected_attacks: int
    blocked_attacks: int
    attack_success_rate: float
    detection_rate: float
    block_rate: float
    false_positive_rate: float
    false_negative_rate: float
    risk_coverage: dict[str, Any]
    redbench_baseline: dict[str, Any]
    risk_breakdown: dict[str, Any]
    recommendations: str | None = None
    summary: str | None = None
    eval_model: str | None = None
    created_at: datetime