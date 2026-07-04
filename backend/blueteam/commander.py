"""Blue team commander for defense orchestration."""

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
    def __init__(self, policy: BluePolicy | None = None, user_role: str = "guest", slow_path: SlowPathBus | None = None, model_name: str | None = None) -> None:
        self.policy = policy or load_blue_policy()
        self.slow_path = slow_path
        self.model_name = model_name
        self.tool_auditor = ToolAuditor(self.policy, user_role=user_role, model_name=model_name)
        self.input_detector = InputDetector(self.policy, use_model=True, model_name=model_name, slow_path=slow_path)
        self.output_detector = OutputDetector(self.policy, use_model=True, model_name=model_name, slow_path=slow_path)

    def inspect_input(self, payload: dict) -> DetectionResult:
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
        return self.tool_auditor.audit_tool_call(
            task_id=task_id,
            attack_case_id=attack_case_id,
            trace_id=trace_id,
            caller_agent=caller_agent,
            tool_call=tool_call,
            prompt=prompt,
        )

    def inspect_output(self, payload: dict) -> DetectionResult:
        return asyncio.run(
            self.output_detector.detect_output(
                payload,
                EventContext(task_id=str(payload.get("task_id") or "task"), trace_id=str(payload.get("trace_id") or "trace")),
            )
        )

    def decision_to_dict(self, result: DetectionResult) -> dict:
        return {
            "action": result.action,
            "risk_level": result.risk_level,
            "risk_type": result.risk_type,
            "reason": result.reason or "蓝队检测完成",
            "confidence": result.confidence,
            "matched_rules": result.matched_rules,
            "metadata": result.metadata,
        }

    def tool_record_to_dict(self, record: ToolAuditRecord) -> dict:
        data = asdict(record)
        if record.degraded_to is not None:
            data["degraded_to"] = {"tool_name": record.degraded_to.tool_name, "arguments": record.degraded_to.arguments}
        return data
