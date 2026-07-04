"""Task management API routes."""

from __future__ import annotations

import threading
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.api.schemas import (
    MutationTaskSchema,
    RedBenchDatasetsResponse,
    TaskCreateRequest,
    TaskCreateResponse,
    TaskDetailResponse,
    TaskEventsResponse,
    TaskListResponse,
    TaskReportResponse,
    TaskStartResponse,
)
from backend.config.settings import get_settings
from backend.evaluation.redbench_runner import list_redbench_datasets, risk_types_for_datasets, sample_count_for_datasets
from backend.orchestrator import run_task
from backend.storage import crud
from backend.storage.database import SessionLocal, get_db

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/redbench/datasets", response_model=RedBenchDatasetsResponse)
def get_redbench_datasets() -> RedBenchDatasetsResponse:
    return RedBenchDatasetsResponse(datasets=list_redbench_datasets())


@router.post("", response_model=TaskCreateResponse, status_code=status.HTTP_201_CREATED)
def create_task(request: TaskCreateRequest, db: Session = Depends(get_db)) -> TaskCreateResponse:
    available_datasets = set(list_redbench_datasets())
    invalid_datasets = [dataset for dataset in request.redbench_datasets if dataset not in available_datasets]
    if not request.redbench_datasets:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择至少一个 RedBench 数据集")
    if invalid_datasets:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"invalid_datasets": invalid_datasets})

    settings = get_settings()
    model_config = {
        "red_model": settings.red_model,
        "target_model": request.llm_models.target_model or settings.target_model,
        "blue_model": settings.blue_model,
        "eval_model": settings.eval_model,
        "redbench_datasets": request.redbench_datasets,
    }
    task = crud.create_task(
        db,
        target_agent=request.target_agent,
        risk_types=risk_types_for_datasets(request.redbench_datasets),
        attack_skills=request.attack_skills,
        attack_count=max(1, sample_count_for_datasets(request.redbench_datasets)),
        max_rounds=request.max_rounds,
        use_llm=True,
        model_config=model_config,
        matrix_version=request.matrix_version,
    )
    return TaskCreateResponse(task_id=task.id, status=task.status, matrix_version=task.matrix_version)


@router.post("/{task_id}/start", response_model=TaskStartResponse)
def start_task(task_id: str, db: Session = Depends(get_db)) -> TaskStartResponse:
    task = crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.status != "PENDING":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只有待开始任务才能执行")

    task.status = "RUNNING"
    task.error = None
    task.updated_at = datetime.utcnow()
    db.add(task)
    db.commit()
    db.refresh(task)
    threading.Thread(target=_run_task_in_background, args=(task.id,), daemon=True, name=f"task-runner-{task.id}").start()
    return TaskStartResponse(task_id=task.id, status=task.status)


@router.get("", response_model=TaskListResponse)
def list_tasks(db: Session = Depends(get_db)) -> TaskListResponse:
    return TaskListResponse(tasks=crud.list_tasks(db))


@router.get("/{task_id}", response_model=TaskDetailResponse)
def get_task(task_id: str, db: Session = Depends(get_db)) -> TaskDetailResponse:
    task = crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return TaskDetailResponse(
        task=task,
        attack_cases=task.attack_cases,
        mutation_tasks=_build_mutation_tasks(task),
        detection_results=task.detection_results,
        report=task.evaluation_report,
    )


@router.get("/{task_id}/report", response_model=TaskReportResponse)
def get_task_report(task_id: str, db: Session = Depends(get_db)) -> TaskReportResponse:
    task = crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    report = crud.get_task_report(db, task_id)
    if report is None:
        return TaskReportResponse(report=None, message="Task report has not been generated")
    return TaskReportResponse(report=report)


@router.get("/{task_id}/events", response_model=TaskEventsResponse)
def list_task_events(task_id: str, db: Session = Depends(get_db)) -> TaskEventsResponse:
    task = crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return TaskEventsResponse(events=crud.list_task_events(db, task_id))


def _run_task_in_background(task_id: str) -> None:
    db = SessionLocal()
    try:
        task = crud.get_task(db, task_id)
        if task is None:
            return
        run_task(db, task)
    finally:
        db.close()


def _build_mutation_tasks(task) -> list[MutationTaskSchema]:
    cases_by_parent: dict[str, list] = {}
    for case in task.attack_cases:
        parent_case_id = getattr(case, "parent_case_id", None)
        if parent_case_id:
            cases_by_parent.setdefault(parent_case_id, []).append(case)

    mutation_tasks: list[MutationTaskSchema] = []
    for parent_case_id, children in cases_by_parent.items():
        children.sort(key=lambda item: item.created_at)
        first_child = children[0]
        mutation_tasks.append(
            MutationTaskSchema(
                id=f"mutation_{first_child.id}",
                parent_attack_case_id=parent_case_id,
                result_attack_case_id=first_child.id,
                source_prompt=_find_case_prompt(task.attack_cases, parent_case_id),
                mutated_prompt=first_child.prompt,
                mutation_strategy=first_child.mutation_strategy,
                failure_stage=None,
                failure_reason=None,
                status="COMPLETED",
                next_round=first_child.round_no,
                queued_at=first_child.created_at,
                completed_at=first_child.created_at,
            )
        )

    return sorted(mutation_tasks, key=lambda item: item.queued_at)


def _find_case_prompt(cases, case_id: str) -> str:
    for case in cases:
        if case.id == case_id:
            return case.prompt
    return ""
