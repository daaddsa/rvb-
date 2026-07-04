"""Security assessment report generation."""

from __future__ import annotations

import asyncio
from typing import Any

from backend.evaluation.metrics import calculate_metrics
from backend.evaluation.redbench_runner import compare_with_redbench
from backend.evaluation.scorer import score_task
from backend.llm import get_llm_client
from backend.llm.client import LLMClientError
from backend.llm.prompts import EVAL_SYSTEM_PROMPT, payload_to_prompt


def build_evaluation_report(state: dict[str, Any]) -> dict[str, Any]:
    round_results = list(state.get("round_results", []))
    attack_cases = list(state.get("attack_cases", []))
    metrics = calculate_metrics(
        round_results,
        requested_risk_types=list(state.get("risk_types", [])),
        attack_cases=attack_cases,
    )
    scores = score_task(round_results, attack_cases)
    redbench_baseline = compare_with_redbench(metrics["risk_breakdown"], selected_datasets=state.get("redbench_datasets") or [])

    report = {
        **metrics,
        **scores,
        "redbench_baseline": redbench_baseline,
    }
    try:
        llm_summary = asyncio.run(generate_report_summary(report, model_name=state["eval_model"]))
    except LLMClientError:
        llm_summary = build_summary(report) + build_recommendations(report)
    report["recommendations"] = llm_summary
    report["summary"] = llm_summary
    return report


def build_summary(report: dict[str, Any]) -> str:
    total = report.get("total_attacks", 0)
    detection_rate = report.get("detection_rate", 0.0)
    attack_success_rate = report.get("attack_success_rate", 0.0)
    defense_score = report.get("defense_score", 0.0)
    return (
        f"本轮共评估 {total} 条攻击链，检测率 {detection_rate:.2%}，"
        f"攻击成功率 {attack_success_rate:.2%}，综合防御得分 {defense_score:.2%}。"
    )


def build_recommendations(report: dict[str, Any]) -> str:
    suggestions: list[str] = []
    if report.get("attack_success_rate", 0.0) > 0:
        suggestions.append("补强允许通过样本对应的输入检测、工具审计和输出脱敏规则")
    if report.get("false_negative_rate", 0.0) > 0.2:
        suggestions.append("优先复盘漏报样本并扩展高风险关键词、角色越权和工具链规则")
    if report.get("risk_coverage", {}).get("missing"):
        suggestions.append("补齐未覆盖风险类型的攻击模板和蓝队策略")
    if report.get("redbench_baseline", {}).get("delta", 0.0) < 0:
        suggestions.append("针对低于 RedBench 基线的风险类型增加专项回归测试")
    return "；".join(suggestions) or "当前规则集对本轮样本有效，建议持续扩充样本并进行回归验证。"


async def generate_report_summary(payload: dict, model_name: str) -> str:
    client = get_llm_client()
    return await client.eval_chat(
        [
            {"role": "system", "content": EVAL_SYSTEM_PROMPT},
            {"role": "user", "content": payload_to_prompt("Generate the evaluation summary and remediation advice.", payload)},
        ],
        model=model_name,
    )
