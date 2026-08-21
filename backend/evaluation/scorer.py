"""Scoring utilities for confrontation results.
攻防对抗评分工具，基于严重程度权重和动作风险分数计算攻防得分。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

# 严重程度权重映射：越严重权重越高
_SEVERITY_WEIGHTS = {
    "low": 1.0,
    "medium": 1.5,
    "high": 2.0,
    "critical": 2.5,
}
# 动作风险分数映射：allow=1.0（攻击成功），degrade=0.35（部分成功），block=0.0（攻击失败）
_ACTION_RISK_SCORE = {
    "allow": 1.0,
    "degrade": 0.35,
    "block": 0.0,
}


@dataclass(slots=True)
class RoundScore:
    """单轮评分数据类。
    记录攻击影响和防御有效性。
    """
    attack_case_id: str | None  # 攻击用例ID
    risk_type: str  # 风险类型
    action: str  # 决策动作
    severity_weight: float  # 严重程度权重
    attack_impact: float  # 攻击影响 = 动作风险分数 × 严重程度权重
    defense_effectiveness: float  # 防御有效性 = 1 - (动作风险分数 / 严重程度权重)


def score_round(result: dict[str, Any], attack_case: dict[str, Any] | None = None) -> RoundScore:
    """计算单轮对抗的攻防得分。
    参数：
        result: 本轮对抗结果
        attack_case: 关联的攻击用例（可选）
    返回：
        RoundScore 对象
    """
    action = str(result.get("action") or "allow")
    risk_type = str(result.get("risk_type") or (attack_case or {}).get("risk_type") or "UNKNOWN")
    # 获取严重程度权重
    severity = str(result.get("risk_level") or (attack_case or {}).get("severity") or "medium").lower()
    severity_weight = _SEVERITY_WEIGHTS.get(severity, _SEVERITY_WEIGHTS["medium"])
    # 计算攻击影响：动作分数 × 严重程度权重
    attack_impact = round(_ACTION_RISK_SCORE.get(action, 1.0) * severity_weight, 4)
    # 计算防御有效性：1 - (动作分数 / 严重程度权重)
    defense_effectiveness = round(1.0 - (_ACTION_RISK_SCORE.get(action, 1.0) / severity_weight), 4)
    defense_effectiveness = max(0.0, min(1.0, defense_effectiveness))  # 限制在 [0, 1]

    return RoundScore(
        attack_case_id=result.get("attack_case_id"),
        risk_type=risk_type,
        action=action,
        severity_weight=severity_weight,
        attack_impact=attack_impact,
        defense_effectiveness=defense_effectiveness,
    )


def score_task(round_results: list[dict[str, Any]], attack_cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """计算整个任务的攻防评分。
    参数：
        round_results: 各轮对抗结果
        attack_cases: 攻击用例列表
    返回：
        包含 residual_risk_score、defense_score、total_attack_impact 等的字典
    """
    # 按用例ID索引
    cases_by_id = {case.get("id"): case for case in attack_cases or []}
    # 计算每轮评分
    scores = [score_round(result, cases_by_id.get(result.get("attack_case_id"))) for result in round_results]
    # 汇总攻击影响
    total_impact = round(sum(item.attack_impact for item in scores), 4)
    max_impact = round(sum(item.severity_weight for item in scores), 4)
    # 残余风险分数 = 实际总影响 / 最大可能影响
    residual_risk_score = round(total_impact / max_impact, 4) if max_impact else 0.0
    # 防御得分 = 1 - 残余风险分数
    defense_score = round(1.0 - residual_risk_score, 4) if max_impact else 0.0

    return {
        "residual_risk_score": residual_risk_score,  # 残余风险分数
        "defense_score": defense_score,  # 防御得分
        "total_attack_impact": total_impact,  # 总攻击影响
        "max_attack_impact": max_impact,  # 最大可能攻击影响
        "round_scores": [asdict(item) for item in scores],  # 每轮评分明细
    }