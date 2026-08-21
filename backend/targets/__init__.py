"""Target agent sandbox package.
目标智能体沙箱包，管理目标智能体的注册、动作规划和工具执行。
"""

from backend.targets.manager import TargetAgent, TargetAgentAction, TargetManager, load_target_agents

__all__ = ["TargetAgent", "TargetAgentAction", "TargetManager", "load_target_agents"]