"""Red team attack generation and execution package.
红队攻击生成和执行包，提供攻击用例生成、变异、执行和外部框架适配能力。
"""

from backend.redteam.attack_generator import AttackLibrary, generate_attack_variant
from backend.redteam.commander import RedTeamCommander

__all__ = ["AttackLibrary", "RedTeamCommander", "generate_attack_variant"]