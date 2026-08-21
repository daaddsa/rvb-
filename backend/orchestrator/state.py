"""Runtime state for the MVP red-blue orchestration flow.
红蓝对抗编排流程的运行时状态定义，使用 TypedDict 描述各阶段数据结构。
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class AttackCaseState(TypedDict, total=False):
    """单条攻击用例的运行时状态。
    包含攻击用例的标识、风险类型、目标智能体、prompt 和演化策略等字段。
    """
    id: str  # 攻击用例唯一标识
    risk_chain_id: str  # 风险链标识
    round_no: int  # 当前轮次编号
    skill_id: str  # 攻击技能标识
    risk_type: str  # 风险类型（如 ASI01、ASI02 等）
    target_agent: str  # 目标智能体名称
    prompt: str  # 攻击提示词
    expected_violation: str  # 预期违规行为描述
    severity: str  # 严重程度：low/medium/high/critical
    parent_case_id: str | None  # 父用例ID（用于变异追踪）
    mutation_strategy: str | None  # 变异策略：semantic_rewrite / role_context_shift 等
    metadata: dict[str, Any]  # 附加元数据（来源、模型名、变异次数等）


class RoundResultState(TypedDict, total=False):
    """单轮对抗结果的运行时状态。
    记录蓝队对攻击用例的检测决策和执行结果。
    """
    attack_case_id: str  # 关联的攻击用例ID
    trace_id: str  # 链路追踪ID
    stage: str  # 检测阶段：input / tool_call / output
    action: Literal["allow", "block", "degrade"]  # 蓝队决策：放行 / 阻断 / 降级
    successful: bool  # 攻击是否成功（action=allow 时为 True）
    blocked: bool  # 是否被阻断（action=block 时为 True）
    risk_type: str | None  # 风险类型
    risk_level: str | None  # 风险等级：low/medium/high/critical
    reason: str  # 蓝队决策理由
    target_output: str | None  # 目标智能体输出
    redteam_hint: str | None  # 红队突变提示，指导下一轮变异方向
    suggested_mutation_strategy: list[str]  # 建议的变异策略列表
    round_no: int  # 轮次编号
    # 以下字段为扩展字段，由 _round_result 填充
    detector: str  # 检测器名称
    model_name: str  # 使用的模型名称
    confidence: float | None  # 置信度


class MutationTaskState(TypedDict, total=False):
    """变异任务状态，用于红队异步进化攻击用例。"""
    parent_case: AttackCaseState  # 父用例
    outcome: RoundResultState  # 上一轮对抗结果
    next_round: int  # 下一轮编号
    mutation_strategy: str  # 变异策略


class AttackTaskState(TypedDict, total=False):
    """攻击任务总状态，贯穿整个红蓝对抗编排流程。"""
    task_id: str  # 任务唯一标识
    target_agent: str  # 目标智能体
    risk_types: list[str]  # 风险类型列表
    attack_skills: list[str]  # 攻击技能列表
    attack_count: int  # 攻击用例数量
    max_rounds: int  # 最大变异轮数
    matrix_version: str  # 攻击矩阵版本
    model_config: dict[str, Any]  # 模型配置
    red_model: str  # 红队模型名称
    target_model: str  # 目标智能体模型名称
    blue_model: str  # 蓝队模型名称
    eval_model: str  # 评估模型名称
    redbench_datasets: list[str]  # RedBench 数据集列表
    attack_cases: list[AttackCaseState]  # 攻击用例列表
    mutation_tasks: list[MutationTaskState]  # 变异任务队列
    round_results: list[RoundResultState]  # 各轮对抗结果
    evaluation_result: dict[str, Any]  # 评估结果
    audit_events: list[dict[str, Any]]  # 审计事件列表
    status: str  # 任务状态：RUNNING / COMPLETED / FAILED
    error: str | None  # 错误信息