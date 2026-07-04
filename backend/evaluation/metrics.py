"""Metric calculation for attack and defense results."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def calculate_metrics(
    round_results: list[dict[str, Any]],
    *,
    requested_risk_types: list[str] | None = None,
    attack_cases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    total = len(round_results)
    blocked = sum(1 for item in round_results if item.get("action") == "block" or item.get("blocked"))
    degraded = sum(1 for item in round_results if item.get("action") == "degrade")
    successful = sum(1 for item in round_results if item.get("action") == "allow" or item.get("successful"))
    detected = blocked + degraded
    covered = _covered_risks(round_results)
    requested = sorted(set(requested_risk_types or []))

    return {
        "total_attacks": total,
        "successful_attacks": successful,
        "detected_attacks": detected,
        "blocked_attacks": blocked,
        "degraded_attacks": degraded,
        "attack_success_rate": _rate(successful, total),
        "detection_rate": _rate(detected, total),
        "block_rate": _rate(blocked, total),
        "degrade_rate": _rate(degraded, total),
        "false_positive_rate": _false_positive_rate(round_results),
        "false_negative_rate": _rate(successful, total),
        "risk_coverage": _risk_coverage(covered, requested),
        "risk_breakdown": _risk_breakdown(round_results, attack_cases or []),
    }


def _covered_risks(round_results: list[dict[str, Any]]) -> list[str]:
    return sorted({str(item.get("risk_type")) for item in round_results if item.get("risk_type")})


def _risk_coverage(covered: list[str], requested: list[str]) -> dict[str, Any]:
    requested_set = set(requested)
    covered_set = set(covered)
    denominator = len(requested_set) or len(covered_set)
    return {
        "requested": requested,
        "covered": covered,
        "missing": sorted(requested_set - covered_set),
        "count": len(covered_set),
        "coverage_rate": _rate(len(covered_set & requested_set), denominator) if requested_set else _rate(len(covered_set), denominator),
    }


def _risk_breakdown(round_results: list[dict[str, Any]], attack_cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    cases_by_id = {case.get("id"): case for case in attack_cases}
    breakdown: dict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0, "blocked": 0, "degraded": 0, "successful": 0})

    for result in round_results:
        attack_case = cases_by_id.get(result.get("attack_case_id"), {})
        risk_type = str(result.get("risk_type") or attack_case.get("risk_type") or "UNKNOWN")
        bucket = breakdown[risk_type]
        bucket["total"] += 1
        bucket["blocked"] += int(result.get("action") == "block" or bool(result.get("blocked")))
        bucket["degraded"] += int(result.get("action") == "degrade")
        bucket["successful"] += int(result.get("action") == "allow" or bool(result.get("successful")))

    return {
        risk_type: {
            **bucket,
            "attack_success_rate": _rate(bucket["successful"], bucket["total"]),
            "detection_rate": _rate(bucket["blocked"] + bucket["degraded"], bucket["total"]),
            "block_rate": _rate(bucket["blocked"], bucket["total"]),
        }
        for risk_type, bucket in sorted(breakdown.items())
    }


def _false_positive_rate(round_results: list[dict[str, Any]]) -> float:
    benign = [item for item in round_results if item.get("risk_type") in {None, "BENIGN", "SAFE"}]
    false_positive = sum(1 for item in benign if item.get("action") in {"block", "degrade"})
    return _rate(false_positive, len(benign))


def _rate(value: int, total: int) -> float:
    return round(value / total, 4) if total else 0.0
