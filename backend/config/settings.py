"""运行时配置加载模块
从环境变量和静态默认值中读取配置，支持通过环境变量覆盖所有配置项。
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """平台运行时配置数据类（不可变、使用slots优化内存）。
    所有配置项均可通过对应的环境变量覆盖。
    字段说明:
        database_url: SQLite数据库连接URL
        ollama_base_url: Ollama本地服务地址
        red_model: 红队（攻击方）使用的LLM模型名称
        target_model: 目标系统（被测智能体）使用的LLM模型名称
        blue_model: 蓝队（防御方）使用的LLM模型名称
        eval_model: 评估模型名称
        default_max_rounds: 默认最大对抗轮次
        llm_timeout: LLM请求超时时间（秒）
        external_eval_api_base_url: 外部评估API基础URL（如DeepSeek API）
        external_eval_api_key: 外部评估API密钥
    """
    database_url: str = "sqlite:///./red_blue_platform.db"
    ollama_base_url: str = "http://localhost:11434"
    red_model: str = "dolphin-mistral:latest"
    target_model: str = "qwen3:1.7b"
    blue_model: str = "gemma2:2b"
    eval_model: str = "deepseek-v4-flash"
    default_max_rounds: int = 2
    llm_timeout: float = 120.0
    external_eval_api_base_url: str | None = "https://api.deepseek.com"
    """外部评估API基础URL，需要自行配置（如DeepSeek API）"""
    external_eval_api_key: str | None = ""


def get_settings() -> Settings:
    """获取运行时配置实例。
    使用默认值初始化Settings，然后通过环境变量覆盖各配置项。
    环境变量名与Settings字段名大写一致（如DATABASE_URL、OLLAMA_BASE_URL等）。
    返回:
        Settings: 合并了环境变量覆盖的最终配置实例
    """
    # 先用默认值创建实例
    defaults = Settings()
    # 通过环境变量覆盖各配置项，若无环境变量则保持默认值
    return Settings(
        database_url=os.getenv("DATABASE_URL", defaults.database_url),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", defaults.ollama_base_url),
        red_model=os.getenv("RED_MODEL", defaults.red_model),
        target_model=os.getenv("TARGET_MODEL", defaults.target_model),
        blue_model=os.getenv("BLUE_MODEL", defaults.blue_model),
        eval_model=os.getenv("EVAL_MODEL", defaults.eval_model),
        default_max_rounds=int(os.getenv("DEFAULT_MAX_ROUNDS", str(defaults.default_max_rounds))),
        llm_timeout=float(os.getenv("LLM_TIMEOUT", str(defaults.llm_timeout))),
        external_eval_api_base_url=os.getenv("EXTERNAL_EVAL_API_BASE_URL", defaults.external_eval_api_base_url),
        external_eval_api_key=os.getenv("EXTERNAL_EVAL_API_KEY", defaults.external_eval_api_key),
    )