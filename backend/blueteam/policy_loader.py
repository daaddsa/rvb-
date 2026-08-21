"""Security policy loader.
安全策略加载器，支持从 YAML 配置文件加载蓝队防御策略。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# 默认蓝队策略配置文件路径
_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "blue_policies.yaml"


@dataclass(slots=True)
class RulePolicy:
    """单条防御规则策略。
    定义关键词匹配规则，用于输入和输出检测。
    """
    id: str  # 规则唯一标识
    risk_type: str  # 风险类型（如 ASI01、ASI02 等）
    risk_level: str  # 风险等级：low/medium/high/critical
    action: str  # 命中后的动作：allow/block/degrade
    keywords: list[str] = field(default_factory=list)  # 匹配关键词列表


@dataclass(slots=True)
class RolePolicy:
    """角色权限策略。
    定义角色的允许工具列表和禁止工具列表。
    """
    allowed_tools: list[str] = field(default_factory=list)  # 允许的工具列表
    denied_tools: list[str] = field(default_factory=list)  # 禁止的工具列表


@dataclass(slots=True)
class BluePolicy:
    """蓝队完整安全策略。
    包含角色、阈值、敏感字段、输入/输出规则和检测器配置。
    """
    roles: dict[str, RolePolicy] = field(default_factory=dict)  # 角色 → 权限策略
    thresholds: dict[str, Any] = field(default_factory=dict)  # 检测阈值配置
    sensitive_fields: list[str] = field(default_factory=list)  # 敏感字段列表
    input_rules: list[RulePolicy] = field(default_factory=list)  # 输入检测规则
    output_rules: list[RulePolicy] = field(default_factory=list)  # 输出检测规则
    use_rellm: bool = False  # 是否启用 ReLLM 输入检测模型
    use_rap: bool = False  # 是否启用 RAP 输出检测模型


def load_blue_policy(path: str | Path = _CONFIG_PATH) -> BluePolicy:
    """从 YAML 文件加载蓝队安全策略。
    参数：
        path: 策略配置文件路径
    返回：
        BluePolicy 对象，如果文件不存在则返回默认空策略
    """
    config_path = Path(path)
    if not config_path.exists():
        return BluePolicy()  # 文件不存在返回空策略

    # 读取 YAML 配置
    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    # 提取检测器配置
    detectors = data.get("detectors", {}) or {}
    input_detector = detectors.get("input", {}) or {}
    output_detector = detectors.get("output", {}) or {}

    return BluePolicy(
        roles=_load_roles(data.get("roles", {})),  # 加载角色权限
        thresholds=dict(data.get("thresholds", {}) or {}),  # 加载阈值
        sensitive_fields=[str(item) for item in data.get("sensitive_fields", []) or []],  # 加载敏感字段
        input_rules=_load_rules(data.get("input_rules", []) or []),  # 加载输入规则
        output_rules=_load_rules(data.get("output_rules", []) or []),  # 加载输出规则
        use_rellm=bool(input_detector.get("use_rellm", False)),  # 是否启用 ReLLM
        use_rap=bool(output_detector.get("use_rap", False)),  # 是否启用 RAP
    )


def _load_roles(data: dict[str, Any]) -> dict[str, RolePolicy]:
    """从 YAML 数据加载角色权限策略。
    参数：
        data: 角色配置字典
    返回：
        角色名 → RolePolicy 的映射字典
    """
    roles: dict[str, RolePolicy] = {}
    for role, raw in (data or {}).items():
        if not isinstance(raw, dict):
            continue  # 跳过非字典项
        roles[str(role)] = RolePolicy(
            allowed_tools=[str(item) for item in raw.get("allowed_tools", []) or []],
            denied_tools=[str(item) for item in raw.get("denied_tools", []) or []],
        )
    return roles


def _load_rules(items: list[dict[str, Any]]) -> list[RulePolicy]:
    """从 YAML 数据加载防御规则列表。
    参数：
        items: 规则配置列表
    返回：
        RulePolicy 列表
    """
    rules: list[RulePolicy] = []
    for item in items:
        if not isinstance(item, dict):
            continue  # 跳过非字典项
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