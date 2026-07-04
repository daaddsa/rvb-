"""Security policy loader."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "blue_policies.yaml"


@dataclass(slots=True)
class RulePolicy:
    id: str
    risk_type: str
    risk_level: str
    action: str
    keywords: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RolePolicy:
    allowed_tools: list[str] = field(default_factory=list)
    denied_tools: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BluePolicy:
    roles: dict[str, RolePolicy] = field(default_factory=dict)
    thresholds: dict[str, Any] = field(default_factory=dict)
    sensitive_fields: list[str] = field(default_factory=list)
    input_rules: list[RulePolicy] = field(default_factory=list)
    output_rules: list[RulePolicy] = field(default_factory=list)
    use_rellm: bool = False
    use_rap: bool = False


def load_blue_policy(path: str | Path = _CONFIG_PATH) -> BluePolicy:
    config_path = Path(path)
    if not config_path.exists():
        return BluePolicy()

    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    detectors = data.get("detectors", {}) or {}
    input_detector = detectors.get("input", {}) or {}
    output_detector = detectors.get("output", {}) or {}

    return BluePolicy(
        roles=_load_roles(data.get("roles", {})),
        thresholds=dict(data.get("thresholds", {}) or {}),
        sensitive_fields=[str(item) for item in data.get("sensitive_fields", []) or []],
        input_rules=_load_rules(data.get("input_rules", []) or []),
        output_rules=_load_rules(data.get("output_rules", []) or []),
        use_rellm=bool(input_detector.get("use_rellm", False)),
        use_rap=bool(output_detector.get("use_rap", False)),
    )


def _load_roles(data: dict[str, Any]) -> dict[str, RolePolicy]:
    roles: dict[str, RolePolicy] = {}
    for role, raw in (data or {}).items():
        if not isinstance(raw, dict):
            continue
        roles[str(role)] = RolePolicy(
            allowed_tools=[str(item) for item in raw.get("allowed_tools", []) or []],
            denied_tools=[str(item) for item in raw.get("denied_tools", []) or []],
        )
    return roles


def _load_rules(items: list[dict[str, Any]]) -> list[RulePolicy]:
    rules: list[RulePolicy] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        rules.append(
            RulePolicy(
                id=str(item.get("id") or "unnamed_rule"),
                risk_type=str(item.get("risk_type") or "UNKNOWN"),
                risk_level=str(item.get("risk_level") or "medium"),
                action=str(item.get("action") or "allow"),
                keywords=[str(keyword) for keyword in item.get("keywords", []) or []],
            )
        )
    return rules
