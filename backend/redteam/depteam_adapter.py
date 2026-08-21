"""Adapter for external Depteam red-team framework.
Depteam 外部红队框架适配器，提供攻击用例的导入/导出接口。
"""

from __future__ import annotations

from backend.orchestrator.state import AttackCaseState


class DepteamAdapter:
    """Depteam 适配器：为后续集成 Depteam 框架保留稳定的边界接口。"""

    def export_cases(self, attack_cases: list[AttackCaseState]) -> list[dict]:
        """将攻击用例导出为 Depteam 兼容格式。
        参数：
            attack_cases: 攻击用例列表
        返回：
            Depteam 格式的字典列表（仅包含核心字段）
        """
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
        """从 Depteam 格式导入攻击用例。
        参数：
            payload: Depteam 格式的字典列表
        返回：
            攻击用例状态列表
        """
        cases: list[AttackCaseState] = []
        for item in payload:
            # 跳过缺少必要字段的项
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