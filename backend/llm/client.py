"""统一多模型LLM客户端
提供对Ollama本地模型和外部API模型（如DeepSeek）的统一调用接口。
支持红队、蓝队、目标系统和评估模型四种角色的模型调用。
"""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from backend.config.settings import Settings, get_settings


# 消息类型：{role: str, content: str}
Message = dict[str, str]


class LLMClientError(RuntimeError):
    """LLM客户端调用异常，用于封装所有LLM调用相关的错误。"""
    pass


@dataclass(slots=True)
class LLMClient:
    """统一的LLM客户端，封装Ollama本地模型和外部API的调用。
    字段说明:
        settings: 平台运行时配置，包含各模型名称和API地址
    """
    settings: Settings

    async def generate(self, prompt: str, model: str | None = None) -> str:
        """使用单个提示词生成回复（便捷方法，内部转为chat调用）。
        参数:
            prompt: 提示词字符串
            model: 模型名称，None则使用默认目标模型
        返回:
            str: 模型生成的文本
        """
        return await self.chat([{"role": "user", "content": prompt}], model=model)

    async def chat(self, messages: list[Message], model: str | None = None) -> str:
        """通用聊天接口，调用Ollama进行对话生成。
        参数:
            messages: 聊天消息列表
            model: 模型名称，None则使用默认目标模型
        返回:
            str: 模型生成的文本
        """
        # 在后台线程中执行同步HTTP请求，避免阻塞事件循环
        return await asyncio.to_thread(self._ollama_chat, messages, model or self.settings.target_model)

    async def red_chat(self, messages: list[Message], model: str | None = None) -> str:
        """红队（攻击方）角色对话，使用red_model进行攻击生成。
        参数:
            messages: 聊天消息列表
            model: 覆盖默认红队模型
        返回:
            str: 红队模型生成的文本
        """
        return await self.chat(messages, model or self.settings.red_model)

    async def target_chat(self, messages: list[Message], model: str | None = None) -> str:
        """目标系统角色对话，使用target_model模拟被攻击系统。
        参数:
            messages: 聊天消息列表
            model: 覆盖默认目标模型
        返回:
            str: 目标模型生成的文本
        """
        return await self.chat(messages, model or self.settings.target_model)

    async def blue_chat(self, messages: list[Message], model: str | None = None) -> str:
        """蓝队（防御方）角色对话，使用blue_model进行安全检测。
        参数:
            messages: 聊天消息列表
            model: 覆盖默认蓝队模型
        返回:
            str: 蓝队模型生成的文本
        """
        return await self.chat(messages, model or self.settings.blue_model)

    async def eval_chat(self, messages: list[Message], model: str | None = None) -> str:
        """评估模型角色对话，用于生成评估报告。
        如果配置了外部API（如DeepSeek），则优先使用外部API；
        否则回退到Ollama本地模型。
        参数:
            messages: 聊天消息列表
            model: 覆盖默认评估模型
        返回:
            str: 评估模型生成的文本
        """
        eval_model = model or self.settings.eval_model
        # 如果配置了外部评估API，使用外部API调用
        if self.settings.external_eval_api_base_url:
            return await asyncio.to_thread(self._external_eval_chat, messages, eval_model)
        # 否则使用Ollama本地调用
        return await self.chat(messages, eval_model)

    def ensure_ollama_healthy(self) -> None:
        """检查Ollama服务是否健康可用。
        通过调用Ollama的/api/tags接口验证服务是否正常响应。
        异常:
            LLMClientError: 服务不可用或响应格式异常
        """
        # 解析Ollama基础URL，构建健康检查URL
        parsed = urlparse(self.settings.ollama_base_url)
        scheme = parsed.scheme or "http"
        netloc = parsed.netloc or parsed.path
        health_url = f"{scheme}://{netloc.rstrip('/')}/api/tags"
        # 发送GET请求到/api/tags接口
        request = urllib.request.Request(health_url, headers={"Content-Type": "application/json"}, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=min(self.settings.llm_timeout, 5.0)) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise LLMClientError(f"Ollama service is unavailable: {exc}") from exc
        # 验证响应格式：models字段必须为列表
        if not isinstance(result.get("models"), list):
            raise LLMClientError("Ollama service is unavailable: /api/tags returned invalid response")

    def _ollama_chat(self, messages: list[Message], model: str) -> str:
        """调用Ollama本地聊天API（同步方法，在后台线程中执行）。
        参数:
            messages: 聊天消息列表
            model: 模型名称
        返回:
            str: 模型生成的文本内容
        异常:
            LLMClientError: 调用失败或响应格式异常
        """
        # 构建Ollama聊天API请求URL
        url = self.settings.ollama_base_url.rstrip("/") + "/api/chat"
        # 构建请求负载：关闭流式输出以获取完整响应
        payload = {"model": model, "messages": messages, "stream": False}
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

        try:
            with urllib.request.urlopen(request, timeout=self.settings.llm_timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise LLMClientError(f"Ollama model call failed: {exc}") from exc

        # 从响应中提取message.content字段
        message = result.get("message", {})
        content = message.get("content")
        if not isinstance(content, str):
            raise LLMClientError("Ollama response missing message content")
        return content

    def _external_eval_chat(self, messages: list[Message], model: str) -> str:
        """调用外部评估API（如DeepSeek OpenAI兼容接口，同步方法）。
        参数:
            messages: 聊天消息列表
            model: 模型名称
        返回:
            str: 模型生成的文本内容
        异常:
            LLMClientError: 调用失败或响应格式异常
        """
        base_url = self.settings.external_eval_api_base_url
        if not base_url:
            raise LLMClientError("External eval API base URL is not configured")

        # 构建OpenAI兼容的聊天请求负载
        payload = {"model": model, "messages": messages, "stream": False}
        headers = {"Content-Type": "application/json"}
        # 如果配置了API密钥，添加Bearer认证头
        if self.settings.external_eval_api_key:
            headers["Authorization"] = f"Bearer {self.settings.external_eval_api_key}"

        data = json.dumps(payload).encode("utf-8")
        # 请求外部API的/chat/completions端点
        request = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(request, timeout=self.settings.llm_timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise LLMClientError(f"External eval model call failed: {exc}") from exc

        # 从OpenAI兼容响应中提取choices[0].message.content
        choices = result.get("choices")
        if isinstance(choices, list) and choices:
            content = choices[0].get("message", {}).get("content")
            if isinstance(content, str):
                return content
        raise LLMClientError("External eval response missing message content")


# 全局LLM客户端单例
_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """获取全局LLM客户端单例，延迟初始化。
    返回:
        LLMClient: 配置好的LLM客户端实例
    """
    global _client
    if _client is None:
        _client = LLMClient(get_settings())
    return _client