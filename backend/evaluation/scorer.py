"""Scoring utilities for confrontation results."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


_SEVERITY_WEIGHTS = {
    "low": 1.0,
    "medium": 1.5,
    "high": 2.0,
    "critical": 2.5,
}
_ACTION_RISK_SCORE = {
    "allow": 1.0,
    "degrade": 0.35,
    "block": 0.0,
}


@dataclass(slots=True)
class RoundScore:
    attack_case_id: str | None
    risk_type: str
    action: str
    severity_weight: float
    attack_impact: float
    defense_effectiveness: float


def score_round(result: dict[str, Any], attack_case: dict[str, Any] | None = None) -> RoundScore:
    action = str(result.get("action") or "allow")
    risk_type = str(result.get("risk_type") or (attack_case or {}).get("risk_type") or "UNKNOWN")
    severity = str(result.get("risk_level") or (attack_case or {}).get("severity") or "medium").lower()
    severity_weight = _SEVERITY_WEIGHTS.get(severity, _SEVERITY_WEIGHTS["medium"])
    attack_impact = round(_ACTION_RISK_SCORE.get(action, 1.0) * severity_weight, 4)
    defense_effectiveness = round(1.0 - (_ACTION_RISK_SCORE.get(action, 1.0) / severity_weight), 4)
    defense_effectiveness = max(0.0, min(1.0, defense_effectiveness))

    return RoundScore(
        attack_case_id=result.get("attack_case_id"),
        risk_type=risk_type,
        action=action,
        severity_weight=severity_weight,
        attack_impact=attack_impact,
        defense_effectiveness=defense_effectiveness,
    )


def score_task(round_results: list[dict[str, Any]], attack_cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    cases_by_id = {case.get("id"): case for case in attack_cases or []}
    scores = [score_round(result, cases_by_id.get(result.get("attack_case_id"))) for result in round_results]
    total_impact = round(sum(item.attack_impact for item in scores), 4)
    max_impact = round(sum(item.severity_weight for item in scores), 4)
    residual_risk_score = round(total_impact / max_impact, 4) if max_impact else 0.0
    defense_score = round(1.0 - residual_risk_score, 4) if max_impact else 0.0

    return {
        "residual_risk_score": residual_risk_score,
        "defense_score": defense_score,
        "total_attack_impact": total_impact,
        "max_attack_impact": max_impact,
        "round_scores": [asdict(item) for item in scores],
    }
