"""CRUD操作辅助函数
提供任务、报告、审计事件的增删查改操作，封装SQLAlchemy查询逻辑。
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.storage.models import AuditEvent, EvaluationReport, Task


def create_task(
    db: Session,
    *,
    target_agent: str,
    risk_types: list[str],
    attack_skills: list[str],
    attack_count: int,
    max_rounds: int,
    use_llm: bool,
    model_config: dict,
    matrix_version: str,
) -> Task:
    """创建新的对抗任务。
    参数:
        db: 数据库会话
        target_agent: 目标智能体类型
        risk_types: 风险类型列表
        attack_skills: 攻击技能列表
        attack_count: 攻击用例数量
        max_rounds: 最大轮次
        use_llm: 是否启用LLM
        model_config: 模型配置字典
        matrix_version: 评估矩阵版本
    返回:
        Task: 创建后的任务ORM对象（已刷新状态）
    """
    # 构造Task实例，使用UUID生成唯一ID
    task = Task(
        id=f"task_{uuid4().hex[:12]}",
        status="PENDING",
        target_agent=target_agent,
        risk_types=risk_types,
        attack_skills=attack_skills,
        attack_count=attack_count,
        max_rounds=max_rounds,
        use_llm=use_llm,
        model_config=model_config,
        red_model=model_config.get("red_model"),
        target_model=model_config.get("target_model"),
        blue_model=model_config.get("blue_model"),
        eval_model=model_config.get("eval_model"),
        matrix_version=matrix_version,
    )
    # 添加到会话并提交，然后刷新以获取数据库生成的默认值
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_tasks(db: Session) -> list[Task]:
    """获取所有任务列表，按创建时间降序排列。
    参数:
        db: 数据库会话
    返回:
        list[Task]: 任务ORM对象列表
    """
    return list(db.scalars(select(Task).order_by(Task.created_at.desc())).all())


def get_task(db: Session, task_id: str) -> Task | None:
    """根据ID获取单个任务，同时预加载关联的attack_cases、detection_results和evaluation_report。
    参数:
        db: 数据库会话
        task_id: 任务ID
    返回:
        Task | None: 任务ORM对象，不存在则返回None
    """
    return db.scalar(
        select(Task)
        .where(Task.id == task_id)
        .options(
            selectinload(Task.attack_cases),       # 预加载攻击用例
            selectinload(Task.detection_results),   # 预加载检测结果
            selectinload(Task.evaluation_report),   # 预加载评估报告
        )
    )


def get_task_report(db: Session, task_id: str) -> EvaluationReport | None:
    """根据任务ID获取评估报告。
    参数:
        db: 数据库会话
        task_id: 任务ID
    返回:
        EvaluationReport | None: 评估报告ORM对象，不存在则返回None
    """
    return db.scalar(select(EvaluationReport).where(EvaluationReport.task_id == task_id))


def list_task_events(db: Session, task_id: str) -> list[AuditEvent]:
    """获取指定任务的所有审计事件，按创建时间升序排列。
    参数:
        db: 数据库会话
        task_id: 任务ID
    返回:
        list[AuditEvent]: 审计事件ORM对象列表
    """
    return list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.task_id == task_id)
            .order_by(AuditEvent.created_at.asc())
        ).all()
    )