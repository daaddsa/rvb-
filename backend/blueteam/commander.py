"""Blue team commander for defense orchestration.
蓝队指挥官，负责防御编排：输入检测、工具审计、输出检测的统一调度入口。
"""

from __future__ import annotations

from dataclasses import asdict
import asyncio

from backend.blueteam.auditors.tool_auditor import ToolAuditRecord, ToolAuditor
from backend.blueteam.detectors.base import DetectionResult
from backend.blueteam.detectors.input_detector import InputDetector
from backend.blueteam.detectors.output_detector import OutputDetector
from backend.blueteam.policy_loader import BluePolicy, load_blue_policy
from backend.eventbus import EventContext, SlowPathBus
from backend.targets.sandbox.contracts import ToolCallPlan


class BlueTeamCommander:
    """蓝队指挥官：统一管理输入检测、输出检测和工具审计。
    支持规则检测和 LLM 模型检测双通道并行执行。
    """

    def __init__(self, policy: BluePolicy | None = None, user_role: str = "guest", slow_path: SlowPathBus | None = None, model_name: str | None = None) -> None:
        """初始化蓝队指挥官。
        参数：
            policy: 蓝队安全策略，为 None 则加载默认策略
            user_role: 用户角色，默认为 guest
            slow_path: 慢速通道事件总线，用于审计和防御反馈
            model_name: 蓝队使用的 LLM 模型名称
        """
        self.policy = policy or load_blue_policy()  # 加载安全策略
        self.slow_path = slow_path  # 慢速通道
        self.model_name = model_name  # 模型名称
        # 初始化三个防御组件
        self.tool_auditor = ToolAuditor(self.policy, user_role=user_role, model_name=model_name)
        self.input_detector = InputDetector(self.policy, use_model=True, model_name=model_name, slow_path=slow_path)
        self.output_detector = OutputDetector(self.policy, use_model=True, model_name=model_name, slow_path=slow_path)

    def inspect_input(self, payload: dict) -> DetectionResult:
        """检测输入（用户 prompt），判断是否允许通过。
        参数：
            payload: 包含 prompt、task_id、trace_id 的字典
        返回：
            DetectionResult：包含 action（allow/block/degrade）等决策信息
        """
        return asyncio.run(
            self.input_detector.detect_input(
                payload,
                EventContext(task_id=str(payload.get("task_id") or "task"), trace_id=str(payload.get("trace_id") or "trace")),
            )
        )

    def audit_tool(
        self,
        *,
        task_id: str,
        attack_case_id: str,
        trace_id: str,
        caller_agent: str,
        tool_call: ToolCallPlan | None,
        prompt: str,
    ) -> ToolAuditRecord:
        """审计目标智能体计划调用的工具。
        参数：
            task_id: 任务标识
            attack_case_id: 攻击用例ID
            trace_id: 链路追踪ID
            caller_agent: 调用方智能体ID
            tool_call: 工具调用计划
            prompt: 原始用户 prompt
        返回：
            ToolAuditRecord：包含审计决策和可能的降级方案
        """
        return self.tool_auditor.audit_tool_call(
            task_id=task_id,
            attack_case_id=attack_case_id,
            trace_id=trace_id,
            caller_agent=caller_agent,
            tool_call=tool_call,
            prompt=prompt,
        )

    def inspect_output(self, payload: dict) -> DetectionResult:
        """检测输出（目标智能体响应），判断是否允许通过。
        参数：
            payload: 包含 output、task_id、trace_id 的字典
        返回：
            DetectionResult：包含检测决策信息
        """
        return asyncio.run(
            self.output_detector.detect_output(
                payload,
                EventContext(task_id=str(payload.get("task_id") or "task"), trace_id=str(payload.get("trace_id") or "trace")),
            )
        )

    def decision_to_dict(self, result: DetectionResult) -> dict:
        """将 DetectionResult 转换为字典格式，方便序列化。
        参数：
            result: 检测结果对象
        返回：
            包含 action、risk_level、risk_type、reason 等的字典
        """
        return {
            "action": result.action,  # 决策动作：allow / block / degrade
            "risk_level": result.risk_level,  # 风险等级
            "risk_type": result.risk_type,  # 风险类型
            "reason": result.reason or "蓝队检测完成",  # 决策理由
            "confidence": result.confidence,  # 置信度
            "matched_rules": result.matched_rules,  # 命中的规则列表
            "metadata": result.metadata,  # 附加元数据
        }

    def tool_record_to_dict(self, record: ToolAuditRecord) -> dict:
        """将 ToolAuditRecord 转换为字典格式。
        参数：
            record: 工具审计记录
        返回：
            包含审计字段的字典，包含可能的降级方案
        """
        data = asdict(record)
        # 如果存在降级方案，序列化为字典
        if record.degraded_to is not None:
            data["degraded_to"] = {"tool_name": record.degraded_to.tool_name, "arguments": record.degraded_to.arguments}
        return data