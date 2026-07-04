"""Adapter for local RedBench parquet benchmark statistics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

_REDBENCH_DIR = Path(__file__).resolve().parents[2] / "redbench"
_RISK_DATASET_MAP = {
    "ASI01": ("DAN", "GPTFuzzer", "GandalfIgnoreInstructions", "LatentJailbreak", "JADE", "AdvBench10"),
    "ASI02": ("CyberattackAssistance", "MaliciousInstruct", "MaliciousInstructions", "HarmBench", "FinancialAbusePrompts"),
    "ASI03": ("ForbiddenQuestions", "DoNotAnswer", "StrongREJECT", "ORBench"),
    "ASI07": ("SafeText", "ToxiGen", "XSTest", "XSafety", "PhysicalSafetyInstructions"),
}


@dataclass(slots=True)
class RedBenchResult:
    dataset: str
    score: float
    baseline_detection_rate: float
    delta: float
    risk_scores: dict[str, dict[str, float]]
    dataset_stats: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "score": self.score,
            "baseline_detection_rate": self.baseline_detection_rate,
            "delta": self.delta,
            "risk_scores": self.risk_scores,
            "dataset_stats": self.dataset_stats,
        }


def compare_with_redbench(risk_breakdown: dict[str, dict[str, Any]], selected_datasets: list[str] | None = None) -> dict[str, Any]:
    redbench_stats = load_redbench_stats(selected_datasets=selected_datasets)
    risk_scores: dict[str, dict[str, float]] = {}
    weighted_score = 0.0
    weighted_baseline = 0.0
    total = 0

    for risk_type, bucket in risk_breakdown.items():
        if risk_type == "UNKNOWN":
            continue
        count = int(bucket.get("total") or 0)
        detection_rate = float(bucket.get("detection_rate") or 0.0)
        baseline = _baseline_for_risk(risk_type, redbench_stats)
        risk_scores[risk_type] = {
            "detection_rate": round(detection_rate, 4),
            "baseline_detection_rate": baseline,
            "delta": round(detection_rate - baseline, 4),
            "redbench_samples": float(redbench_stats["by_risk"].get(risk_type, {}).get("samples", 0)),
        }
        weighted_score += detection_rate * count
        weighted_baseline += baseline * count
        total += count

    score = round(weighted_score / total, 4) if total else 0.0
    baseline_detection_rate = round(weighted_baseline / total, 4) if total else 0.0
    return RedBenchResult(
        dataset="RedBench-selected-parquet" if selected_datasets else "RedBench-all-parquet",
        score=score,
        baseline_detection_rate=baseline_detection_rate,
        delta=round(score - baseline_detection_rate, 4),
        risk_scores=risk_scores,
        dataset_stats=redbench_stats,
    ).to_dict()


def list_redbench_datasets(redbench_dir: Path = _REDBENCH_DIR) -> list[str]:
    if not redbench_dir.exists():
        return []
    return sorted(
        item.name
        for item in redbench_dir.iterdir()
        if item.is_dir() and (item / f"{item.name}.parquet").exists()
    )


def risk_types_for_datasets(dataset_names: list[str]) -> list[str]:
    risks = [_risk_for_dataset(dataset_name) for dataset_name in dataset_names]
    return sorted({risk for risk in risks if risk != "UNKNOWN"})


def sample_count_for_datasets(dataset_names: list[str]) -> int:
    available = set(list_redbench_datasets())
    total = 0
    for dataset_name in dataset_names:
        if dataset_name not in available:
            continue
        total += _count_parquet_rows(_REDBENCH_DIR / dataset_name / f"{dataset_name}.parquet")
    return total


def load_redbench_prompt_records(
    redbench_dir: Path = _REDBENCH_DIR,
    selected_datasets: list[str] | None = None,
) -> list[dict[str, Any]]:
    available = set(list_redbench_datasets(redbench_dir))
    dataset_names = [name for name in (selected_datasets or []) if name in available]
    records: list[dict[str, Any]] = []

    for dataset_name in dataset_names:
        parquet_path = redbench_dir / dataset_name / f"{dataset_name}.parquet"
        dataframe = pd.read_parquet(parquet_path)
        risk_type = _risk_for_dataset(dataset_name)

        for row_index, row in dataframe.iterrows():
            prompt = str(row.get("prompt") or "").strip()
            if not prompt:
                continue
            records.append(
                {
                    "dataset_name": dataset_name,
                    "row_index": int(row_index),
                    "prompt": prompt,
                    "risk_type": risk_type,
                    "category": row.get("category"),
                    "domain": row.get("domain"),
                    "source": row.get("source"),
                }
            )
    return records


def load_redbench_stats(redbench_dir: Path = _REDBENCH_DIR, selected_datasets: list[str] | None = None) -> dict[str, Any]:
    available = list_redbench_datasets(redbench_dir)
    requested = [name for name in (selected_datasets or []) if name in available]
    dataset_names = requested or available
    by_dataset: dict[str, dict[str, Any]] = {}
    by_risk: dict[str, dict[str, int]] = {}

    for dataset_name in dataset_names:
        parquet_path = redbench_dir / dataset_name / f"{dataset_name}.parquet"
        samples = _count_parquet_rows(parquet_path)
        risk_type = _risk_for_dataset(dataset_name)
        by_dataset[dataset_name] = {"risk_type": risk_type, "samples": samples}
        bucket = by_risk.setdefault(risk_type, {"datasets": 0, "samples": 0})
        bucket["datasets"] += 1
        bucket["samples"] += samples

    return {
        "selected_datasets": dataset_names,
        "ignored_datasets": [name for name in (selected_datasets or []) if name not in available],
        "total_datasets": len(dataset_names),
        "total_samples": sum(item["samples"] for item in by_dataset.values()),
        "by_dataset": by_dataset,
        "by_risk": by_risk,
    }


def _count_parquet_rows(path: Path) -> int:
    dataframe = pd.read_parquet(path)
    return int(len(dataframe.index))


def _risk_for_dataset(dataset_name: str) -> str:
    for risk_type, dataset_names in _RISK_DATASET_MAP.items():
        if dataset_name in dataset_names:
            return risk_type
    return "UNKNOWN"


def _baseline_for_risk(risk_type: str, stats: dict[str, Any]) -> float:
    samples = stats["by_risk"].get(risk_type, {}).get("samples", 0)
    if samples <= 0:
        return 0.65
    if samples >= 1000:
        return 0.75
    if samples >= 500:
        return 0.7
    if samples >= 100:
        return 0.65
    return 0.6
