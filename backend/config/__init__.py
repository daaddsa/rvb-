"""配置包
提供Settings配置类和get_settings工厂函数，从环境变量和默认值加载运行时配置。
"""

from .settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]