"""Attack execution helpers used by the MVP orchestrator.
攻击执行辅助类，用于构建攻击请求字典。
"""

from __future__ import annotations

from backend.orchestrator.state import AttackCaseState


class AttackExecutor:
    """攻击执行器：将攻击用例转换为可执行的请求字典。"""

    def build_request(self, attack_case: AttackCaseState, trace_id: str) -> dict:
        """根据攻击用例构建请求字典，供下游节点使用。
        参数：
            attack_case: 攻击用例状态
            trace_id: 链路追踪ID
        返回：
            包含 task_id、attack_case_id、trace_id、prompt 等字段的请求字典
        """
        return {
            "task_id": attack_case.get("metadata", {}).get("task_id"),  # 从元数据中取 task_id
            "attack_case_id": attack_case["id"],  # 攻击用例ID
            "trace_id": trace_id,  # 链路追踪ID
            "round_no": attack_case.get("round_no", 1),  # 轮次编号
            "risk_type": attack_case.get("risk_type"),  # 风险类型
            "skill_id": attack_case.get("skill_id"),  # 攻击技能
            "target_agent": attack_case.get("target_agent"),  # 目标智能体
            "prompt": attack_case.get("prompt"),  # 攻击提示词
            "expected_violation": attack_case.get("expected_violation"),  # 预期违规行为
        }