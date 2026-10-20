from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import httpx

from ..config import settings
from .errors import ProviderUnavailable


class VisionProvider(Protocol):
    def describe_image(self, path: Path) -> str: ...


class QwenVisionProvider:
    def __init__(self) -> None:
        if not settings.qwen_api_key:
            raise ProviderUnavailable("未配置 QWEN_API_KEY，无法解析图片")

    def describe_image(self, path: Path) -> str:
        mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }.get(path.suffix.lower(), "image/png")
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        payload = {
            "model": settings.qwen_vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "请完整提取图片中的技术文档文字、代码和表格内容，只返回识别结果。",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{encoded}"},
                        },
                    ],
                }
            ],
        }
        response = httpx.post(
            f"{settings.qwen_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.qwen_api_key}"},
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


class FakeVisionProvider:
    def describe_image(self, path: Path) -> str:
        return f"图片文档 {path.name} 的测试 OCR 内容。"


@lru_cache(maxsize=1)
def get_vision_provider() -> VisionProvider:
    if settings.is_test:
        return FakeVisionProvider()
    return QwenVisionProvider()
