"""Database table models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Task(Base):
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

    attack_cases: Mapped[list[AttackCase]] = relationship(back_populates="task", cascade="all, delete-orphan")
    detection_results: Mapped[list[DetectionResultRecord]] = relationship(back_populates="task", cascade="all, delete-orphan")
    audit_events: Mapped[list[AuditEvent]] = relationship(back_populates="task", cascade="all, delete-orphan")
    evaluation_report: Mapped[EvaluationReport | None] = relationship(
        back_populates="task", cascade="all, delete-orphan", uselist=False
    )


class AttackCase(Base):
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

    task: Mapped[Task] = relationship(back_populates="attack_cases")
    parent_case: Mapped[AttackCase | None] = relationship(remote_side=[id])
    detection_results: Mapped[list[DetectionResultRecord]] = relationship(back_populates="attack_case")
    audit_events: Mapped[list[AuditEvent]] = relationship(back_populates="attack_case")


class DetectionResultRecord(Base):
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
