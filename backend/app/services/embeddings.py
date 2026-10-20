from __future__ import annotations

import hashlib
import math
import threading
from functools import lru_cache
from typing import Protocol

import httpx

from ..config import settings
from .errors import ProviderUnavailable


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class BgeM3EmbeddingProvider:
    def __init__(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ProviderUnavailable("BGE-M3 依赖未安装，请安装 sentence-transformers") from exc
        try:
            self.model = SentenceTransformer(
                settings.bge_m3_model,
                device=settings.bge_device,
                local_files_only=settings.bge_local_files_only,
                trust_remote_code=True,
            )
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailable(f"BGE-M3 加载失败：{exc}") from exc
        self.batch_size = max(1, int(settings.bge_batch_size))
        self._lock = threading.Lock()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        with self._lock:
            vectors = self.model.encode(
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        return vectors.tolist()

class QwenEmbeddingProvider:
    def __init__(self) -> None:
        if not settings.qwen_api_key:
            raise ProviderUnavailable("未配置 QWEN_API_KEY，无法生成向量")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        headers = {"Authorization": f"Bearer {settings.qwen_api_key}"}
        vectors: list[list[float]] = []
        with httpx.Client(timeout=60) as client:
            for start in range(0, len(texts), 10):
                batch = texts[start : start + 10]
                response = client.post(
                    f"{settings.qwen_base_url.rstrip('/')}/embeddings",
                    headers=headers,
                    json={"model": settings.qwen_embedding_model, "input": batch},
                )
                response.raise_for_status()
                payload = response.json()
                ordered = sorted(payload["data"], key=lambda item: item.get("index", 0))
                vectors.extend([item["embedding"] for item in ordered])
        return vectors


class FakeEmbeddingProvider:
    def __init__(self, dimension: int = 256) -> None:
        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        output = []
        for text in texts:
            vector = [0.0] * self.dimension
            tokens = text.lower().split()
            if not tokens:
                tokens = list(text)
            for token in tokens:
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                for offset in range(0, len(digest), 2):
                    index = int.from_bytes(digest[offset : offset + 2], "big") % self.dimension
                    vector[index] += 1.0
            norm = math.sqrt(sum(value * value for value in vector)) or 1.0
            output.append([value / norm for value in vector])
        return output


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    if settings.is_test:
        return FakeEmbeddingProvider()
    provider = settings.embedding_provider.strip().lower()
    if provider in {"bge_m3", "bge-m3", "bge"}:
        return BgeM3EmbeddingProvider()
    if provider == "qwen":
        return QwenEmbeddingProvider()
    raise ProviderUnavailable(f"未知 Embedding provider：{settings.embedding_provider}")
def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts with Redis-backed content hash caching when available."""
    from .cache import get_cache

    if not texts:
        return []
    cache = get_cache()
    cached = cache.get_embeddings(texts)
    missing_indices = [index for index, vector in enumerate(cached) if vector is None]
    if missing_indices:
        fresh = get_embedding_provider().embed([texts[index] for index in missing_indices])
        cache.set_embeddings([texts[index] for index in missing_indices], fresh)
        for index, vector in zip(missing_indices, fresh):
            cached[index] = vector
    return [vector or [] for vector in cached]
