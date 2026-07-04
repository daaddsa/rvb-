"""Runtime settings loaded from environment and static config files."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str = "sqlite:///./red_blue_platform.db"
    ollama_base_url: str = "http://localhost:11434"
    red_model: str = "dolphin-mistral:latest"
    target_model: str = "qwen3:1.7b"
    blue_model: str = "gemma2:2b"
    eval_model: str = "deepseek-v4-flash"
    default_max_rounds: int = 2
    llm_timeout: float = 120.0
    external_eval_api_base_url: str | None = "https://api.deepseek.com"
    external_eval_api_key: str | None = "sk-5fd2a64792284261b60a44cf429e46a8"


def get_settings() -> Settings:
    defaults = Settings()
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
