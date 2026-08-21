"""数据库表模型（SQLAlchemy ORM）
定义任务、攻击用例、检测结果、审计事件和评估报告等核心数据表。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """SQLAlchemy声明式基类，所有ORM模型继承自此。"""
    pass


class Task(Base):
    """对抗任务表，存储一次红蓝对抗评估的完整配置和状态。
    字段说明:
        id: 任务唯一标识（格式：task_xxxxxxxxxxxx）
        status: 任务状态（PENDING/RUNNING/COMPLETED/FAILED）
        target_agent: 目标智能体类型
        risk_types: 风险类型列表（JSON数组）
        attack_skills: 攻击技能列表（JSON数组）
        attack_count: 攻击用例数量
        current_round: 当前对抗轮次
        max_rounds: 最大对抗轮次
        use_llm: 是否启用LLM
        model_config: 模型配置字典（JSON）
        red_model/blue_model/target_model/eval_model: 各角色使用的模型名称
        matrix_version: 评估矩阵版本
        error: 错误信息（任务失败时记录）
    """
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    target_agent: Mapped[str] = mapped_column(String(128), index=True)
    risk_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    attack_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    attack_count: Mapped[int] = mapped_column(Integer, default=0)
    current_round: Mapped[int] = mapped_column(Integer, default=0)
    max_rounds: Mapped[int] = mapped_column(Integer, default=1)
    use_llm: Mapped[bool] = mapped_column(Boolean, default=True)
    model_config: Mapped[dict] = mapped_column(JSON, default=dict)
    red_model: Mapped[str | None] = mapped_column(String(128))
    target_model: Mapped[str | None] = mapped_column(String(128))
    blue_model: Mapped[str | None] = mapped_column(String(128))
    eval_model: Mapped[str | None] = mapped_column(String(128))
    matrix_version: Mapped[str] = mapped_column(String(64), default="ASI_2026")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    error: Mapped[str | None] = mapped_column(Text)

    # 关联关系：级联删除，删除任务时同时删除关联的用例、检测结果、审计事件和报告
    attack_cases: Mapped[list[AttackCase]] = relationship(back_populates="task", cascade="all, delete-orphan")
    detection_results: Mapped[list[DetectionResultRecord]] = relationship(back_populates="task", cascade="all, delete-orphan")
    audit_events: Mapped[list[AuditEvent]] = relationship(back_populates="task", cascade="all, delete-orphan")
    evaluation_report: Mapped[EvaluationReport | None] = relationship(
        back_populates="task", cascade="all, delete-orphan", uselist=False
    )


class AttackCase(Base):
    """攻击用例表，记录红队生成的每一次攻击提示词及其元数据。
    字段说明:
        id: 攻击用例唯一标识
        task_id: 所属任务ID（外键）
        risk_chain_id: 风险链ID（用于关联同一攻击链的不同轮次用例）
        round_no: 所在轮次
        skill_id: 使用的攻击技能ID
        risk_type: 风险类型
        target_agent: 目标智能体
        prompt: 攻击提示词
        expected_violation: 预期违规描述
        severity: 严重程度
        model_name: 使用的模型名称
        parent_case_id: 父用例ID（变异来源，自引用外键）
        mutation_strategy: 变异策略
    """
    __tablename__ = "attack_cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    risk_chain_id: Mapped[str | None] = mapped_column(String(64), index=True)
    round_no: Mapped[int] = mapped_column(Integer, default=1, index=True)
    skill_id: Mapped[str | None] = mapped_column(String(128), index=True)
    risk_type: Mapped[str | None] = mapped_column(String(64), index=True)
    target_agent: Mapped[str] = mapped_column(String(128), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    expected_violation: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str | None] = mapped_column(String(32))
    model_name: Mapped[str | None] = mapped_column(String(128))
    parent_case_id: Mapped[str | None] = mapped_column(ForeignKey("attack_cases.id"))
    mutation_strategy: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关联关系
    task: Mapped[Task] = relationship(back_populates="attack_cases")
    parent_case: Mapped[AttackCase | None] = relationship(remote_side=[id])
    detection_results: Mapped[list[DetectionResultRecord]] = relationship(back_populates="attack_case")
    audit_events: Mapped[list[AuditEvent]] = relationship(back_populates="attack_case")


class DetectionResultRecord(Base):
    """检测结果表，记录蓝队对攻击用例的检测和拦截结果。
    字段说明:
        id: 检测结果唯一标识
        task_id: 所属任务ID（外键）
        attack_case_id: 关联的攻击用例ID（外键）
        stage: 检测阶段（input/tool_call/output/target_execution）
        detector: 检测器名称
        model_name: 检测模型名称
        detected: 是否检测到攻击
        blocked: 是否拦截
        action: 执行的动作（allow/block/degrade）
        risk_level: 风险等级（low/medium/high/critical）
        risk_type: 风险类型
        reason: 检测/拦截原因
        confidence: 置信度（0-1）
        raw_output: 原始输出（JSON）
    """
    __tablename__ = "detection_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    attack_case_id: Mapped[str | None] = mapped_column(ForeignKey("attack_cases.id"), index=True)
    stage: Mapped[str] = mapped_column(String(32), index=True)
    detector: Mapped[str] = mapped_column(String(128), index=True)
    model_name: Mapped[str | None] = mapped_column(String(128))
    detected: Mapped[bool] = mapped_column(Boolean, default=False)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    action: Mapped[str] = mapped_column(String(32), default="allow")
    risk_level: Mapped[str | None] = mapped_column(String(32), index=True)
    risk_type: Mapped[str | None] = mapped_column(String(64), index=True)
    reason: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    raw_output: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    task: Mapped[Task] = relationship(back_populates="detection_results")
    attack_case: Mapped[AttackCase | None] = relationship(back_populates="detection_results")


class AuditEvent(Base):
    """审计事件表，记录红蓝对抗过程中的所有关键事件。
    字段说明:
        id: 审计事件唯一标识
        task_id: 所属任务ID（外键）
        attack_case_id: 关联攻击用例ID（外键）
        trace_id: 追踪ID（用于关联同一请求链上的事件）
        event_type: 事件类型
        event_topic: 事件主题（FAST_PATH/SLOW_PATH）
        agent: 事件相关的智能体类型
        tool_name: 相关的工具名称
        payload: 事件负载（JSON）
        allowed: 是否允许通过
        risk_level: 风险等级
        risk_type: 风险类型
        message: 事件消息
    """
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    attack_case_id: Mapped[str | None] = mapped_column(ForeignKey("attack_cases.id"), index=True)
    trace_id: Mapped[str | None] = mapped_column(String(128), index=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    event_topic: Mapped[str | None] = mapped_column(String(64), index=True)
    agent: Mapped[str | None] = mapped_column(String(128), index=True)
    tool_name: Mapped[str | None] = mapped_column(String(128), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    allowed: Mapped[bool | None] = mapped_column(Boolean)
    risk_level: Mapped[str | None] = mapped_column(String(32), index=True)
    risk_type: Mapped[str | None] = mapped_column(String(64), index=True)
    message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    task: Mapped[Task] = relationship(back_populates="audit_events")
    attack_case: Mapped[AttackCase | None] = relationship(back_populates="audit_events")


class EvaluationReport(Base):
    """评估报告表，存储一次对抗任务的最终评估指标。
    字段说明:
        id: 报告唯一标识
        task_id: 所属任务ID（外键，一对一）
        total_attacks: 攻击总数
        successful_attacks: 成功攻击数
        detected_attacks: 被检测到的攻击数
        blocked_attacks: 被拦截的攻击数
        attack_success_rate: 攻击成功率
        detection_rate: 检测率
        block_rate: 拦截率
        false_positive_rate: 误报率
        false_negative_rate: 漏报率
        risk_coverage: 风险覆盖情况（JSON）
        redbench_baseline: RedBench基准对比（JSON）
        risk_breakdown: 风险分类统计（JSON）
        recommendations: 改进建议
        summary: 总结
        eval_model: 评估使用的模型
    """
    __tablename__ = "evaluation_reports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), unique=True, index=True)
    total_attacks: Mapped[int] = mapped_column(Integer, default=0)
    successful_attacks: Mapped[int] = mapped_column(Integer, default=0)
    detected_attacks: Mapped[int] = mapped_column(Integer, default=0)
    blocked_attacks: Mapped[int] = mapped_column(Integer, default=0)
    attack_success_rate: Mapped[float] = mapped_column(Float, default=0.0)
    detection_rate: Mapped[float] = mapped_column(Float, default=0.0)
    block_rate: Mapped[float] = mapped_column(Float, default=0.0)
    false_positive_rate: Mapped[float] = mapped_column(Float, default=0.0)
    false_negative_rate: Mapped[float] = mapped_column(Float, default=0.0)
    risk_coverage: Mapped[dict] = mapped_column(JSON, default=dict)
    redbench_baseline: Mapped[dict] = mapped_column(JSON, default=dict)
    risk_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    recommendations: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    eval_model: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    task: Mapped[Task] = relationship(back_populates="evaluation_report")