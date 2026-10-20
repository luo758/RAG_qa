from __future__ import annotations

import re
import threading
from functools import lru_cache
from typing import Protocol

from ..config import settings
from .errors import ProviderUnavailable


class RerankerProvider(Protocol):
    def score(self, query: str, passages: list[str]) -> list[float]: ...


class BgeM3Reranker:
    def __init__(self) -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise ProviderUnavailable("BGE reranker 依赖未安装") from exc
        try:
            self.model = CrossEncoder(
                settings.bge_reranker_model,
                device=settings.bge_device,
                local_files_only=settings.bge_local_files_only,
                trust_remote_code=True,
                max_length=1024,
            )
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailable(f"BGE reranker 加载失败：{exc}") from exc
        self._lock = threading.Lock()

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        with self._lock:
            values = self.model.predict([(query, passage) for passage in passages])
        return [float(value) for value in values]


class FakeReranker:
    def score(self, query: str, passages: list[str]) -> list[float]:
        query_tokens = set(re.findall(r"[\w\u4e00-\u9fff]+", query.lower()))
        scores = []
        for passage in passages:
            passage_tokens = set(re.findall(r"[\w\u4e00-\u9fff]+", passage.lower()))
            union = query_tokens | passage_tokens
            scores.append(len(query_tokens & passage_tokens) / len(union) if union else 0.0)
        return scores


@lru_cache(maxsize=1)
def get_reranker() -> RerankerProvider | None:
    if not settings.reranker_enabled:
        return None
    if settings.is_test:
        return FakeReranker()
    return BgeM3Reranker()
