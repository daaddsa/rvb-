"""Evaluation and report generation package.
评估和报告生成包，提供指标计算、评分、RedBench 对比和报告生成能力。
"""

from backend.evaluation.metrics import calculate_metrics
from backend.evaluation.redbench_runner import compare_with_redbench
from backend.evaluation.report_generator import build_evaluation_report, build_recommendations, build_summary
from backend.evaluation.scorer import RoundScore, score_round, score_task

__all__ = [
    "RoundScore",
    "build_evaluation_report",
    "build_recommendations",
    "build_summary",
    "calculate_metrics",
    "compare_with_redbench",
    "score_round",
    "score_task",
]