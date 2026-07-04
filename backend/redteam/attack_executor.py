"""Attack execution helpers used by the MVP orchestrator."""

from __future__ import annotations

from backend.orchestrator.state import AttackCaseState


class AttackExecutor:
    def build_request(self, attack_case: AttackCaseState, trace_id: str) -> dict:
        return {
            "task_id": attack_case.get("metadata", {}).get("task_id"),
            "attack_case_id": attack_case["id"],
            "trace_id": trace_id,
            "round_no": attack_case.get("round_no", 1),
            "risk_type": attack_case.get("risk_type"),
            "skill_id": attack_case.get("skill_id"),
            "target_agent": attack_case.get("target_agent"),
            "prompt": attack_case.get("prompt"),
            "expected_violation": attack_case.get("expected_violation"),
        }
