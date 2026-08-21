"""API边界的请求与响应数据模型（Schema）
定义前端与后端交互时使用的Pydantic模型，用于请求验证和响应序列化。
"""

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
    """任务中使用的LLM模型配置，前端可指定目标模型覆写默认值。"""
    target_model: str | None = None


# 获取全局配置实例（用于设置默认值）
settings = get_settings()


class TaskCreateRequest(BaseModel):
    """创建任务的请求体模型。
    字段说明:
        target_agent: 目标智能体类型（如"chatbot"、"assistant"等）
        risk_types: 风险类型列表，从RedBench数据集推导
        attack_skills: 攻击技能列表
        attack_count: 生成的攻击用例数量，默认5，最小1
        max_rounds: 最大对抗轮次，默认从配置读取，最小1
        use_llm: 是否启用LLM辅助
        llm_models: LLM模型配置（前端发送时字段名为model_config）
        redbench_datasets: 选用的RedBench基准数据集列表
        matrix_version: 评估矩阵版本，默认ASI_2026
    """
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
    """RedBench可用数据集列表响应。"""
    datasets: list[str]


class TaskCreateResponse(BaseModel):
    """创建任务成功后的响应体。"""
    task_id: str
    status: str
    matrix_version: str


class TaskStartResponse(BaseModel):
    """启动任务后的响应体。"""
    task_id: str
    status: str


class TaskListResponse(BaseModel):
    """任务列表查询响应体。"""
    tasks: list[TaskSchema]


class MutationTaskSchema(BaseModel):
    """变异任务数据模型，描述一次攻击用例的变异/改进过程。
    字段说明:
        id: 变异任务ID
        parent_attack_case_id: 父攻击用例ID（变异前的原始用例）
        result_attack_case_id: 变异后生成的攻击用例ID
        source_prompt: 原始提示词
        mutated_prompt: 变异后的提示词
        mutation_strategy: 使用的变异策略名称
        failure_stage: 失败所在的阶段
        failure_reason: 失败原因
        status: 变异任务状态
        next_round: 所在轮次
        queued_at: 入队时间
        completed_at: 完成时间
    """
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
    """任务详情响应体，包含任务基本信息及关联的攻击用例、变异任务、检测结果和评估报告。"""
    task: TaskSchema
    attack_cases: list[AttackCaseSchema] = Field(default_factory=list)
    mutation_tasks: list[MutationTaskSchema] = Field(default_factory=list)
    detection_results: list[DetectionResultSchema] = Field(default_factory=list)
    report: EvaluationReportSchema | None = None


class TaskEventsResponse(BaseModel):
    """任务审计事件列表响应体。"""
    events: list[AuditEventSchema]


class TaskReportResponse(BaseModel):
    """任务评估报告响应体，可能报告尚未生成。"""
    report: EvaluationReportSchema | None = None
    message: str | None = None


class ErrorResponse(BaseModel):
    """通用错误响应体。"""
    detail: str | dict[str, Any]