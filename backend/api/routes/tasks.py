"""任务管理API路由
提供任务的创建、启动、查询、事件审计和报告获取等REST端点。
"""

from __future__ import annotations

import threading
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# 导入API层的请求/响应Schema模型
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
# 导入RedBench基准数据集相关工具函数
from backend.evaluation.redbench_runner import list_redbench_datasets, risk_types_for_datasets, sample_count_for_datasets
# 导入任务编排器，用于在后台线程中执行对抗任务
from backend.orchestrator import run_task
from backend.storage import crud
from backend.storage.database import SessionLocal, get_db

# 创建路由实例，设置URL前缀和接口标签
router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/redbench/datasets", response_model=RedBenchDatasetsResponse)
def get_redbench_datasets() -> RedBenchDatasetsResponse:
    """获取所有可用的RedBench基准数据集列表。
    返回:
        RedBenchDatasetsResponse: 包含数据集名称列表的响应
    """
    return RedBenchDatasetsResponse(datasets=list_redbench_datasets())


@router.post("", response_model=TaskCreateResponse, status_code=status.HTTP_201_CREATED)
def create_task(request: TaskCreateRequest, db: Session = Depends(get_db)) -> TaskCreateResponse:
    """创建新的对抗评估任务。
    参数:
        request: 任务创建请求体，包含目标智能体、数据集等配置
        db: 数据库会话（由FastAPI依赖注入）
    返回:
        TaskCreateResponse: 包含新任务ID、状态和矩阵版本的响应
    异常:
        HTTPException 400: 数据集为空或包含无效数据集
    """
    # 获取所有可用数据集，用于校验前端传入的数据集是否有效
    available_datasets = set(list_redbench_datasets())
    # 筛选出无效的数据集名称
    invalid_datasets = [dataset for dataset in request.redbench_datasets if dataset not in available_datasets]
    # 校验：至少选择一个数据集
    if not request.redbench_datasets:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择至少一个 RedBench 数据集")
    # 校验：所有数据集名称必须有效
    if invalid_datasets:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"invalid_datasets": invalid_datasets})

    settings = get_settings()
    # 构建模型配置字典，合并默认配置和前端指定的配置
    model_config = {
        "red_model": settings.red_model,
        "target_model": request.llm_models.target_model or settings.target_model,
        "blue_model": settings.blue_model,
        "eval_model": settings.eval_model,
        "redbench_datasets": request.redbench_datasets,
    }
    # 调用CRUD层创建任务记录
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
    """启动指定任务，在后台线程中开始红蓝对抗执行。
    参数:
        task_id: 要启动的任务ID
        db: 数据库会话
    返回:
        TaskStartResponse: 包含任务ID和更新后状态的响应
    异常:
        HTTPException 404: 任务不存在
        HTTPException 400: 任务状态不允许启动（非PENDING状态）
        HTTPException 503: Ollama服务不可用
    """
    # 查询任务，若不存在则返回404
    task = crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    # 只有PENDING状态的任务才允许启动
    if task.status != "PENDING":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只有待开始任务才能执行")

    # 启动前检查Ollama服务是否健康
    try:
        get_llm_client().ensure_ollama_healthy()
    except LLMClientError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Ollama 服务不可用：{exc}") from exc

    # 更新任务状态为RUNNING并持久化
    task.status = "RUNNING"
    task.error = None
    task.updated_at = datetime.utcnow()
    db.add(task)
    db.commit()
    db.refresh(task)
    # 在后台守护线程中启动对抗执行，不阻塞API响应
    threading.Thread(target=_run_task_in_background, args=(task.id,), daemon=True, name=f"task-runner-{task.id}").start()
    return TaskStartResponse(task_id=task.id, status=task.status)


@router.get("", response_model=TaskListResponse)
def list_tasks(db: Session = Depends(get_db)) -> TaskListResponse:
    """获取所有任务列表，按创建时间降序排列。
    参数:
        db: 数据库会话
    返回:
        TaskListResponse: 包含任务列表的响应
    """
    return TaskListResponse(tasks=crud.list_tasks(db))


@router.get("/{task_id}", response_model=TaskDetailResponse)
def get_task(task_id: str, db: Session = Depends(get_db)) -> TaskDetailResponse:
    """获取指定任务的详细信息，包括关联的攻击用例、变异任务、检测结果和报告。
    参数:
        task_id: 任务ID
        db: 数据库会话
    返回:
        TaskDetailResponse: 任务详情响应
    异常:
        HTTPException 404: 任务不存在
    """
    task = crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    # 从任务ORM对象上获取关联的attack_cases、detection_results等
    return TaskDetailResponse(
        task=task,
        attack_cases=task.attack_cases,
        mutation_tasks=_build_mutation_tasks(task),
        detection_results=task.detection_results,
        report=task.evaluation_report,
    )


@router.get("/{task_id}/report", response_model=TaskReportResponse)
def get_task_report(task_id: str, db: Session = Depends(get_db)) -> TaskReportResponse:
    """获取指定任务的评估报告。
    参数:
        task_id: 任务ID
        db: 数据库会话
    返回:
        TaskReportResponse: 包含评估报告或提示信息的响应
    异常:
        HTTPException 404: 任务不存在
    """
    task = crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # 查询报告，若尚未生成则返回提示信息
    report = crud.get_task_report(db, task_id)
    if report is None:
        return TaskReportResponse(report=None, message="Task report has not been generated")
    return TaskReportResponse(report=report)


@router.get("/{task_id}/events", response_model=TaskEventsResponse)
def list_task_events(task_id: str, db: Session = Depends(get_db)) -> TaskEventsResponse:
    """获取指定任务的审计事件列表。
    参数:
        task_id: 任务ID
        db: 数据库会话
    返回:
        TaskEventsResponse: 包含审计事件列表的响应
    异常:
        HTTPException 404: 任务不存在
    """
    task = crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return TaskEventsResponse(events=crud.list_task_events(db, task_id))


def _run_task_in_background(task_id: str) -> None:
    """在后台线程中执行对抗任务。
    创建独立的数据库会话，调用编排器执行任务，执行完毕后关闭会话。
    参数:
        task_id: 要执行的任务ID
    """
    # 创建独立的数据库会话（不能使用依赖注入的会话，因为后台线程生命周期不同）
    db = SessionLocal()
    try:
        task = crud.get_task(db, task_id)
        if task is None:
            return
        # 调用任务编排器执行完整的红蓝对抗流程
        run_task(db, task)
    finally:
        # 确保数据库会话被关闭
        db.close()


def _build_mutation_tasks(task) -> list[MutationTaskSchema]:
    """从任务的攻击用例中构建变异任务列表。
    将具有相同parent_case_id的攻击用例分组为变异任务，
    每组取第一个子用例作为变异结果。
    参数:
        task: 任务ORM对象，需包含attack_cases关联
    返回:
        list[MutationTaskSchema]: 按入队时间排序的变异任务列表
    """
    # 按父用例ID分组攻击用例（只处理有parent_case_id的用例，即变异产生的子用例）
    cases_by_parent: dict[str, list] = {}
    for case in task.attack_cases:
        parent_case_id = getattr(case, "parent_case_id", None)
        # 如果有父用例ID，则归入对应的分组
        if parent_case_id:
            cases_by_parent.setdefault(parent_case_id, []).append(case)

    # 遍历每个分组构建MutationTaskSchema
    mutation_tasks: list[MutationTaskSchema] = []
    for parent_case_id, children in cases_by_parent.items():
        # 按创建时间排序，取第一个子用例作为变异结果
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

    # 按入队时间排序后返回
    return sorted(mutation_tasks, key=lambda item: item.queued_at)


def _find_case_prompt(cases, case_id: str) -> str:
    """在攻击用例列表中查找指定ID的用例的提示词。
    参数:
        cases: 攻击用例列表
        case_id: 要查找的用例ID
    返回:
        str: 找到的提示词，若未找到则返回空字符串
    """
    for case in cases:
        if case.id == case_id:
            return case.prompt
    return ""