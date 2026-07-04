"""CRUD helpers for persisted task data."""

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
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_tasks(db: Session) -> list[Task]:
    return list(db.scalars(select(Task).order_by(Task.created_at.desc())).all())


def get_task(db: Session, task_id: str) -> Task | None:
    return db.scalar(
        select(Task)
        .where(Task.id == task_id)
        .options(
            selectinload(Task.attack_cases),
            selectinload(Task.detection_results),
            selectinload(Task.evaluation_report),
        )
    )


def get_task_report(db: Session, task_id: str) -> EvaluationReport | None:
    return db.scalar(select(EvaluationReport).where(EvaluationReport.task_id == task_id))


def list_task_events(db: Session, task_id: str) -> list[AuditEvent]:
    return list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.task_id == task_id)
            .order_by(AuditEvent.created_at.asc())
        ).all()
    )
