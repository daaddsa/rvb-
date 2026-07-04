"""Main LangGraph-backed red-blue confrontation orchestration."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.orchestrator.nodes import dispatch_defense_pipeline, evaluate_stream, init_task_state, plan_attack_chain
from backend.orchestrator.state import AttackTaskState
from backend.storage.models import AttackCase, AuditEvent, DetectionResultRecord, EvaluationReport, Task


def run_task(db: Session, task: Task) -> AttackTaskState:
    state = init_task_state(task)
    persisted_audit_ids: set[str] = set()
    try:
        state = plan_attack_chain(state)
        state = dispatch_defense_pipeline(
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
        state = evaluate_stream(state)
        _persist_pending_audit_events(db, state, persisted_audit_ids)
        _persist_evaluation_report(db, task, state)

        task.status = "COMPLETED"
        task.current_round = max((case.get("round_no", 1) for case in state.get("attack_cases", [])), default=task.current_round)
        task.error = None
    except Exception as exc:
        task.status = "FAILED"
        task.error = str(exc)
        state["status"] = "FAILED"
        state["error"] = str(exc)
        _persist_pending_audit_events(db, state, persisted_audit_ids)
    finally:
        task.updated_at = datetime.utcnow()
        db.add(task)
        db.commit()
        db.refresh(task)

    return state


def build_task_graph():
    from langgraph.graph import END, StateGraph

    graph = StateGraph(AttackTaskState)
    graph.add_node("plan_attack_chain", plan_attack_chain)
    graph.add_node("dispatch_defense_pipeline", dispatch_defense_pipeline)
    graph.add_node("evaluate_stream", evaluate_stream)
    graph.set_entry_point("plan_attack_chain")
    graph.add_edge("plan_attack_chain", "dispatch_defense_pipeline")
    graph.add_edge("dispatch_defense_pipeline", "evaluate_stream")
    graph.add_edge("evaluate_stream", END)
    return graph.compile()


def _persist_round_progress(
    db: Session,
    task: Task,
    attack_case: dict,
    result: dict,
    audit_events: list[dict],
    persisted_audit_ids: set[str],
) -> None:
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

    action = result.get("action", "allow")
    db.add(
        DetectionResultRecord(
            id=f"detect_{uuid4().hex[:12]}",
            task_id=task.id,
            attack_case_id=result.get("attack_case_id"),
            stage=result.get("stage", "round"),
            detector=result.get("detector", "dual_bus_detector"),
            model_name=result.get("model_name"),
            detected=action in {"block", "degrade"},
            blocked=bool(result.get("blocked")),
            action=action,
            risk_level=result.get("risk_level"),
            risk_type=result.get("risk_type"),
            reason=result.get("reason"),
            confidence=result.get("confidence") or (0.9 if action in {"block", "degrade"} else 0.5),
            raw_output=dict(result),
        )
    )

    for event in audit_events:
        if event["id"] in persisted_audit_ids:
            continue
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
        persisted_audit_ids.add(event["id"])

    task.current_round = max(task.current_round, int(result.get("round_no", 1)))
    task.updated_at = datetime.utcnow()
    db.add(task)
    db.commit()
    db.refresh(task)


def _persist_pending_audit_events(db: Session, state: AttackTaskState, persisted_audit_ids: set[str]) -> None:
    pending_events = [event for event in state.get("audit_events", []) if event["id"] not in persisted_audit_ids]
    if not pending_events:
        return

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
        persisted_audit_ids.add(event["id"])
    db.commit()


def _persist_evaluation_report(db: Session, task: Task, state: AttackTaskState) -> None:
    evaluation = state.get("evaluation_result", {})
    db.add(
        EvaluationReport(
            id=f"report_{uuid4().hex[:12]}",
            task_id=task.id,
            total_attacks=evaluation.get("total_attacks", 0),
            successful_attacks=evaluation.get("successful_attacks", 0),
            detected_attacks=evaluation.get("detected_attacks", 0),
            blocked_attacks=evaluation.get("blocked_attacks", 0),
            attack_success_rate=evaluation.get("attack_success_rate", 0.0),
            detection_rate=evaluation.get("detection_rate", 0.0),
            block_rate=evaluation.get("block_rate", 0.0),
            false_positive_rate=evaluation.get("false_positive_rate", 0.0),
            false_negative_rate=evaluation.get("false_negative_rate", 0.0),
            risk_coverage=evaluation.get("risk_coverage", {}),
            redbench_baseline=evaluation.get("redbench_baseline", {}),
            risk_breakdown=evaluation.get("risk_breakdown", {}),
            recommendations=evaluation.get("recommendations"),
            summary=evaluation.get("summary"),
            eval_model=task.eval_model,
        )
    )
    db.commit()
