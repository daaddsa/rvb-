"""Metric calculation for attack and defense results.
攻防结果指标计算模块，计算检测率、阻断率、误报率和风险覆盖等核心指标。
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def calculate_metrics(
    round_results: list[dict[str, Any]],
    *,
    requested_risk_types: list[str] | None = None,
    attack_cases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """计算攻防评估的核心指标。
    参数：
        round_results: 各轮对抗结果列表
        requested_risk_types: 请求覆盖的风险类型列表
        attack_cases: 攻击用例列表（用于风险细分）
    返回：
        包含 total_attacks、detection_rate、block_rate、risk_coverage 等指标的字典
    """
    total = len(round_results)  # 总攻击数
    # 统计各类结果数量
    blocked = sum(1 for item in round_results if item.get("action") == "block" or item.get("blocked"))
    degraded = sum(1 for item in round_results if item.get("action") == "degrade")
    successful = sum(1 for item in round_results if item.get("action") == "allow" or item.get("successful"))
    detected = blocked + degraded  # 检测到 = 阻断 + 降级
    covered = _covered_risks(round_results)  # 已覆盖的风险类型
    requested = sorted(set(requested_risk_types or []))

    return {
        "total_attacks": total,  # 总攻击数
        "successful_attacks": successful,  # 成功攻击数
        "detected_attacks": detected,  # 检测到攻击数
        "blocked_attacks": blocked,  # 阻断攻击数
        "degraded_attacks": degraded,  # 降级攻击数
        "attack_success_rate": _rate(successful, total),  # 攻击成功率
        "detection_rate": _rate(detected, total),  # 检测率
        "block_rate": _rate(blocked, total),  # 阻断率
        "degrade_rate": _rate(degraded, total),  # 降级率
        "false_positive_rate": _false_positive_rate(round_results),  # 误报率
        "false_negative_rate": _rate(successful, total),  # 漏报率（= 攻击成功率）
        "risk_coverage": _risk_coverage(covered, requested),  # 风险覆盖情况
        "risk_breakdown": _risk_breakdown(round_results, attack_cases or []),  # 按风险类型细分
    }


def _covered_risks(round_results: list[dict[str, Any]]) -> list[str]:
    """提取已覆盖的风险类型列表。
    参数：
        round_results: 对抗结果列表
    返回：
        排序后的风险类型列表
    """
    return sorted({str(item.get("risk_type")) for item in round_results if item.get("risk_type")})


def _risk_coverage(covered: list[str], requested: list[str]) -> dict[str, Any]:
    """计算风险覆盖情况。
    参数：
        covered: 已覆盖的风险类型
        requested: 请求覆盖的风险类型
    返回：
        包含 requested、covered、missing、count、coverage_rate 的字典
    """
    requested_set = set(requested)
    covered_set = set(covered)
    denominator = len(requested_set) or len(covered_set)
    return {
        "requested": requested,  # 请求覆盖的
        "covered": covered,  # 实际覆盖的
        "missing": sorted(requested_set - covered_set),  # 未覆盖的
        "count": len(covered_set),  # 覆盖数量
        "coverage_rate": _rate(len(covered_set & requested_set), denominator) if requested_set else _rate(len(covered_set), denominator),  # 覆盖率
    }


def _risk_breakdown(round_results: list[dict[str, Any]], attack_cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """按风险类型细分统计各指标。
    参数：
        round_results: 对抗结果列表
        attack_cases: 攻击用例列表
    返回：
        风险类型 → 指标字典的映射
    """
    cases_by_id = {case.get("id"): case for case in attack_cases}
    breakdown: dict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0, "blocked": 0, "degraded": 0, "successful": 0})

    for result in round_results:
        attack_case = cases_by_id.get(result.get("attack_case_id"), {})
        # 确定风险类型：优先使用结果中的，其次用用例中的
        risk_type = str(result.get("risk_type") or attack_case.get("risk_type") or "UNKNOWN")
        bucket = breakdown[risk_type]
        bucket["total"] += 1
        bucket["blocked"] += int(result.get("action") == "block" or bool(result.get("blocked")))
        bucket["degraded"] += int(result.get("action") == "degrade")
        bucket["successful"] += int(result.get("action") == "allow" or bool(result.get("successful")))

    # 为每种风险类型补充比率指标
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
    """计算误报率：良性样本中被误判为恶意（block/degrade）的比例。
    参数：
        round_results: 对抗结果列表
    返回：
        误报率（0-1）
    """
    benign = [item for item in round_results if item.get("risk_type") in {None, "BENIGN", "SAFE"}]
    false_positive = sum(1 for item in benign if item.get("action") in {"block", "degrade"})
    return _rate(false_positive, len(benign))


def _rate(value: int, total: int) -> float:
    """计算比率，保留4位小数。
    参数：
        value: 分子
        total: 分母
    返回：
        比率值（0-1），分母为 0 时返回 0.0
    """
    return round(value / total, 4) if total else 0.0