"""Main LangGraph-backed red-blue confrontation orchestration.
基于 LangGraph 的红蓝对抗主编排入口，负责构建任务图、执行任务、
持久化进度和评估报告。
"""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.orchestrator.nodes import dispatch_defense_pipeline, evaluate_stream, init_task_state, plan_attack_chain
from backend.orchestrator.state import AttackTaskState
from backend.storage.models import AttackCase, AuditEvent, DetectionResultRecord, EvaluationReport, Task


# #region debug-point D:task-failure
# 调试环境配置文件路径，用于在任务失败时向调试服务器发送事件
_DEBUG_ENV_FILE = Path(".dbg/mutation-failed.env")


def _debug_report(hypothesis_id: str, location: str, msg: str, data: dict | None = None) -> None:
    """向本地调试服务器发送调试事件（仅在调试模式下启用）。
    参数：
        hypothesis_id: 调试假设ID
        location: 代码位置
        msg: 调试消息
        data: 附加数据字典
    """
    url = "http://127.0.0.1:7777/event"
    session_id = "mutation-failed"
    # 尝试从调试配置文件读取自定义配置
    try:
        content = _DEBUG_ENV_FILE.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith("DEBUG_SERVER_URL="):
                url = line.split("=", 1)[1] or url
            elif line.startswith("DEBUG_SESSION_ID="):
                session_id = line.split("=", 1)[1] or session_id
    except OSError:
        pass  # 文件不存在则使用默认配置
    payload = {
        "sessionId": session_id,
        "runId": "pre-fix",
        "hypothesisId": hypothesis_id,
        "location": location,
        "msg": msg,
        "data": data or {},
    }
    # 发送 HTTP POST 请求到调试服务器
    try:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(request, timeout=1).read()
    except OSError:
        pass  # 忽略网络错误，不影响主流程


# #endregion


def run_task(db: Session, task: Task) -> AttackTaskState:
    """执行红蓝对抗任务的主入口函数。
    构建 LangGraph 任务图并执行，将结果持久化到数据库。
    参数：
        db: SQLAlchemy 数据库会话
        task: 任务模型对象
    返回：
        最终的任务状态字典
    """
    # 初始化任务状态
    state = init_task_state(task)
    # 记录已持久化的审计事件ID，避免重复写入
    persisted_audit_ids: set[str] = set()
    # 构建 LangGraph 任务图
    graph = build_task_graph(db=db, task=task, persisted_audit_ids=persisted_audit_ids)
    try:
        # 执行任务图（invoke 会按边顺序依次执行各节点）
        state = graph.invoke(state)
        # 持久化尚未写入的审计事件
        _persist_pending_audit_events(db, state, persisted_audit_ids)
        # 持久化评估报告
        _persist_evaluation_report(db, task, state)

        # 更新任务状态为完成
        task.status = "COMPLETED"
        task.current_round = max((case.get("round_no", 1) for case in state.get("attack_cases", [])), default=task.current_round)
        task.error = None
    except Exception as exc:
        # 任务失败时发送调试事件
        _debug_report(
            "D",
            "backend/orchestrator/main_graph.py:48",
            "[DEBUG] task failed with exception",
            {"task_id": task.id, "error_type": type(exc).__name__, "error": str(exc)},
        )
        task.status = "FAILED"
        task.error = str(exc)
        state["status"] = "FAILED"
        state["error"] = str(exc)
        # 即使失败也尝试持久化已有的审计事件
        _persist_pending_audit_events(db, state, persisted_audit_ids)
    finally:
        # 无论如何都更新任务时间戳并提交
        task.updated_at = datetime.utcnow()
        db.add(task)
        db.commit()
        db.refresh(task)

    return state


def build_task_graph(db: Session | None = None, task: Task | None = None, persisted_audit_ids: set[str] | None = None):
    """构建 LangGraph 任务图。
    图结构：plan_attack_chain → dispatch_defense_pipeline → evaluate_stream → END
    参数：
        db: 数据库会话（可选，传入后会在每轮完成时持久化进度）
        task: 任务对象（可选）
        persisted_audit_ids: 已持久化审计ID集合（可选）
    返回：
        编译后的 LangGraph 可执行图
    """
    from langgraph.graph import END, StateGraph

    # 创建基于 AttackTaskState 的状态图
    graph = StateGraph(AttackTaskState)
    # 添加三个节点：攻击链规划、防御管道调度、评估
    graph.add_node("plan_attack_chain", plan_attack_chain)
    graph.add_node(
        "dispatch_defense_pipeline",
        _build_dispatch_node(db=db, task=task, persisted_audit_ids=persisted_audit_ids),
    )
    graph.add_node("evaluate_stream", evaluate_stream)
    # 设置入口点和边
    graph.set_entry_point("plan_attack_chain")
    graph.add_edge("plan_attack_chain", "dispatch_defense_pipeline")
    graph.add_edge("dispatch_defense_pipeline", "evaluate_stream")
    graph.add_edge("evaluate_stream", END)
    return graph.compile()


def _build_dispatch_node(
    db: Session | None,
    task: Task | None,
    persisted_audit_ids: set[str] | None,
):
    """构建防御管道调度节点，如果提供了数据库会话则包装持久化回调。
    参数：
        db: 数据库会话
        task: 任务对象
        persisted_audit_ids: 已持久化审计ID集合
    返回：
        节点函数（可能是包装后的版本）
    """
    # 如果数据库参数缺失，直接返回原始函数
    if db is None or task is None or persisted_audit_ids is None:
        return dispatch_defense_pipeline

    # 包装 dispatch_defense_pipeline，在每轮完成时持久化进度
    def _dispatch_node(state: AttackTaskState) -> AttackTaskState:
        return dispatch_defense_pipeline(
            state,
            on_round_complete=lambda current_state, attack_case, result, audit_events: _persist_round_progress(
                db,
                task,
                attack_case,
                result,
                audit_events,
                persisted_audit_ids,
            ),
        )

    return _dispatch_node


def _persist_round_progress(
    db: Session,
    task: Task,
    attack_case: dict,
    result: dict,
    audit_events: list[dict],
    persisted_audit_ids: set[str],
) -> None:
    """持久化单轮对抗进度到数据库。
    保存攻击用例、检测结果和审计事件。
    参数：
        db: 数据库会话
        task: 任务对象
        attack_case: 攻击用例字典
        result: 本轮对抗结果
        audit_events: 本轮新增的审计事件
        persisted_audit_ids: 已持久化审计ID集合（用于去重）
    """
    # 如果攻击用例尚未持久化，则创建 AttackCase 记录
    if db.get(AttackCase, attack_case["id"]) is None:
        db.add(
            AttackCase(
                id=attack_case["id"],
                task_id=task.id,
                risk_chain_id=attack_case.get("risk_chain_id"),
                round_no=attack_case.get("round_no", 1),
                skill_id=attack_case.get("skill_id"),
                risk_type=attack_case.get("risk_type"),
                target_agent=attack_case.get("target_agent", task.target_agent),
                prompt=attack_case["prompt"],
                expected_violation=attack_case.get("expected_violation"),
                severity=attack_case.get("severity"),
                model_name=task.red_model,
                parent_case_id=attack_case.get("parent_case_id"),
                mutation_strategy=attack_case.get("mutation_strategy"),
            )
        )

    # 持久化检测结果记录
    action = result.get("action", "allow")
    db.add(
        DetectionResultRecord(
            id=f"detect_{uuid4().hex[:12]}",
            task_id=task.id,
            attack_case_id=result.get("attack_case_id"),
            stage=result.get("stage", "round"),
            detector=result.get("detector", "dual_bus_detector"),
            model_name=result.get("model_name"),
            detected=action in {"block", "degrade"},  # 阻断或降级视为检测到
            blocked=bool(result.get("blocked")),
            action=action,
            risk_level=result.get("risk_level"),
            risk_type=result.get("risk_type"),
            reason=result.get("reason"),
            confidence=result.get("confidence") or (0.9 if action in {"block", "degrade"} else 0.5),
            raw_output=dict(result),
        )
    )

    # 持久化审计事件（去重）
    for event in audit_events:
        if event["id"] in persisted_audit_ids:
            continue  # 跳过已持久化的事件
        db.add(
            AuditEvent(
                id=event["id"],
                task_id=event["task_id"],
                attack_case_id=event.get("attack_case_id"),
                trace_id=event.get("trace_id"),
                event_type=event["event_type"],
                event_topic=event.get("event_topic"),
                agent=event.get("agent"),
                tool_name=event.get("tool_name"),
                payload=event.get("payload", {}),
                allowed=event.get("allowed"),
                risk_level=event.get("risk_level"),
                risk_type=event.get("risk_type"),
                message=event.get("message"),
            )
        )
        persisted_audit_ids.add(event["id"])  # 标记为已持久化

    # 更新任务进度并提交
    task.current_round = max(task.current_round, int(result.get("round_no", 1)))
    task.updated_at = datetime.utcnow()
    db.add(task)
    db.commit()
    db.refresh(task)


def _persist_pending_audit_events(db: Session, state: AttackTaskState, persisted_audit_ids: set[str]) -> None:
    """持久化所有尚未写入的待处理审计事件。
    参数：
        db: 数据库会话
        state: 任务状态
        persisted_audit_ids: 已持久化审计ID集合
    """
    # 筛选出尚未持久化的审计事件
    pending_events = [event for event in state.get("audit_events", []) if event["id"] not in persisted_audit_ids]
    if not pending_events:
        return  # 没有待处理事件则直接返回

    for event in pending_events:
        db.add(
            AuditEvent(
                id=event["id"],
                task_id=event["task_id"],
                attack_case_id=event.get("attack_case_id"),
                trace_id=event.get("trace_id"),
                event_type=event["event_type"],
                event_topic=event.get("event_topic"),
                agent=event.get("agent"),
                tool_name=event.get("tool_name"),
                payload=event.get("payload", {}),
                allowed=event.get("allowed"),
                risk_level=event.get("risk_level"),
                risk_type=event.get("risk_type"),
                message=event.get("message"),
            )
        )
        persisted_audit_ids.add(event["id"])  # 标记为已持久化
    db.commit()


def _persist_evaluation_report(db: Session, task: Task, state: AttackTaskState) -> None:
    """持久化评估报告到数据库。
    参数：
        db: 数据库会话
        task: 任务对象
        state: 任务状态（包含 evaluation_result）
    """
    evaluation = state.get("evaluation_result", {})
    db.add(
        EvaluationReport(
            id=f"report_{uuid4().hex[:12]}",
            task_id=task.id,
            total_attacks=evaluation.get("total_attacks", 0),  # 总攻击数
            successful_attacks=evaluation.get("successful_attacks", 0),  # 成功攻击数
            detected_attacks=evaluation.get("detected_attacks", 0),  # 检测到攻击数
            blocked_attacks=evaluation.get("blocked_attacks", 0),  # 阻断攻击数
            attack_success_rate=evaluation.get("attack_success_rate", 0.0),  # 攻击成功率
            detection_rate=evaluation.get("detection_rate", 0.0),  # 检测率
            block_rate=evaluation.get("block_rate", 0.0),  # 阻断率
            false_positive_rate=evaluation.get("false_positive_rate", 0.0),  # 误报率
            false_negative_rate=evaluation.get("false_negative_rate", 0.0),  # 漏报率
            risk_coverage=evaluation.get("risk_coverage", {}),  # 风险覆盖情况
            redbench_baseline=evaluation.get("redbench_baseline", {}),  # RedBench 基线对比
            risk_breakdown=evaluation.get("risk_breakdown", {}),  # 按风险类型细分
            recommendations=evaluation.get("recommendations"),  # 改进建议
            summary=evaluation.get("summary"),  # 评估摘要
            eval_model=task.eval_model,  # 评估模型
        )
    )
    db.commit()