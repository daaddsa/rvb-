"""Evaluation and report generation package."""

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
