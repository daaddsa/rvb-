"""Adapter for external Depteam red-team framework."""

from __future__ import annotations

from backend.orchestrator.state import AttackCaseState


class DepteamAdapter:
    """Keeps a stable boundary for later Depteam integration."""

    def export_cases(self, attack_cases: list[AttackCaseState]) -> list[dict]:
        return [
            {
                "id": case.get("id"),
                "risk_type": case.get("risk_type"),
                "skill_id": case.get("skill_id"),
                "target_agent": case.get("target_agent"),
                "prompt": case.get("prompt"),
                "expected_violation": case.get("expected_violation"),
                "severity": case.get("severity"),
            }
            for case in attack_cases
        ]

    def import_cases(self, payload: list[dict]) -> list[AttackCaseState]:
        cases: list[AttackCaseState] = []
        for item in payload:
            if not item.get("id") or not item.get("prompt"):
                continue
            cases.append(
                {
                    "id": str(item["id"]),
                    "risk_chain_id": str(item.get("risk_chain_id") or f"chain_{item.get('risk_type', 'unknown').lower()}"),
                    "round_no": int(item.get("round_no") or 1),
                    "skill_id": str(item.get("skill_id") or "prompt_injection"),
                    "risk_type": str(item.get("risk_type") or "UNKNOWN"),
                    "target_agent": str(item.get("target_agent") or "unknown"),
                    "prompt": str(item["prompt"]),
                    "expected_violation": str(item.get("expected_violation") or "external_case"),
                    "severity": str(item.get("severity") or "medium"),
                }
            )
        return cases
