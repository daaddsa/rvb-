"""LLM集成包
提供统一的LLM客户端（LLMClient）和提示词解析工具。
"""

from .client import LLMClient, get_llm_client
from .prompts import parse_llm_json

__all__ = ["LLMClient", "get_llm_client", "parse_llm_json"]