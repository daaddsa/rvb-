"""Unified multi-model LLM client."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from backend.config.settings import Settings, get_settings


Message = dict[str, str]


class LLMClientError(RuntimeError):
    pass


@dataclass(slots=True)
class LLMClient:
    settings: Settings

    async def generate(self, prompt: str, model: str | None = None) -> str:
        return await self.chat([{"role": "user", "content": prompt}], model=model)

    async def chat(self, messages: list[Message], model: str | None = None) -> str:
        return await asyncio.to_thread(self._ollama_chat, messages, model or self.settings.target_model)

    async def red_chat(self, messages: list[Message], model: str | None = None) -> str:
        return await self.chat(messages, model or self.settings.red_model)

    async def target_chat(self, messages: list[Message], model: str | None = None) -> str:
        return await self.chat(messages, model or self.settings.target_model)

    async def blue_chat(self, messages: list[Message], model: str | None = None) -> str:
        return await self.chat(messages, model or self.settings.blue_model)

    async def eval_chat(self, messages: list[Message], model: str | None = None) -> str:
        eval_model = model or self.settings.eval_model
        if self.settings.external_eval_api_base_url:
            return await asyncio.to_thread(self._external_eval_chat, messages, eval_model)
        return await self.chat(messages, eval_model)

    def _ollama_chat(self, messages: list[Message], model: str) -> str:
        url = self.settings.ollama_base_url.rstrip("/") + "/api/chat"
        payload = {"model": model, "messages": messages, "stream": False}
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

        try:
            with urllib.request.urlopen(request, timeout=self.settings.llm_timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise LLMClientError(f"Ollama model call failed: {exc}") from exc

        message = result.get("message", {})
        content = message.get("content")
        if not isinstance(content, str):
            raise LLMClientError("Ollama response missing message content")
        return content

    def _external_eval_chat(self, messages: list[Message], model: str) -> str:
        base_url = self.settings.external_eval_api_base_url
        if not base_url:
            raise LLMClientError("External eval API base URL is not configured")

        payload = {"model": model, "messages": messages, "stream": False}
        headers = {"Content-Type": "application/json"}
        if self.settings.external_eval_api_key:
            headers["Authorization"] = f"Bearer {self.settings.external_eval_api_key}"

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(request, timeout=self.settings.llm_timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise LLMClientError(f"External eval model call failed: {exc}") from exc

        choices = result.get("choices")
        if isinstance(choices, list) and choices:
            content = choices[0].get("message", {}).get("content")
            if isinstance(content, str):
                return content
        raise LLMClientError("External eval response missing message content")


_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient(get_settings())
    return _client
