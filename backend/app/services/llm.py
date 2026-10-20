from __future__ import annotations

import json
from functools import lru_cache
from typing import AsyncIterator, Protocol

import httpx

from ..config import settings
from .errors import ProviderUnavailable


class ChatProvider(Protocol):
    def stream(
        self,
        messages: list[dict],
        *,
        model: str,
        temperature: float,
        top_p: float,
        max_tokens: int,
    ) -> AsyncIterator[str]: ...


class QwenChatProvider:
    def __init__(self) -> None:
        if not settings.qwen_api_key:
            raise ProviderUnavailable("未配置 QWEN_API_KEY，无法调用通义千问")

    async def stream(
        self,
        messages: list[dict],
        *,
        model: str,
        temperature: float,
        top_p: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        headers = {
            "Authorization": f"Bearer {settings.qwen_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "stream": True,
        }
        timeout = httpx.Timeout(connect=20, read=180, write=30, pool=30)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{settings.qwen_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code >= 400:
                    body = (await response.aread()).decode("utf-8", errors="replace")
                    raise ProviderUnavailable(f"通义千问请求失败：{body[:500]}")
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        packet = json.loads(data)
                        delta = packet["choices"][0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue


class FakeChatProvider:
    async def stream(
        self,
        messages: list[dict],
        *,
        model: str,
        temperature: float,
        top_p: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        text = (
            "根据检索到的技术文档，WebSocket 连接默认空闲超时为 10 分钟。"
            "客户端应每 30 秒发送一次 ping，断线后使用指数退避并携带 request_id 重连。[1]"
        )
        for index in range(0, len(text), 6):
            yield text[index : index + 6]


@lru_cache(maxsize=1)
def get_chat_provider() -> ChatProvider:
    if settings.is_test:
        return FakeChatProvider()
    return QwenChatProvider()
