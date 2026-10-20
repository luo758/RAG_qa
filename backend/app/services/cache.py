from __future__ import annotations

import hashlib
import json
import logging
from functools import lru_cache
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from ..config import settings

logger = logging.getLogger(__name__)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class RedisCache:
    def __init__(self) -> None:
        self.enabled = settings.redis_enabled
        self._available = self.enabled
        self._client: Redis | None = None
        if not self.enabled:
            return
        try:
            self._client = Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=settings.redis_socket_timeout,
                socket_timeout=settings.redis_socket_timeout,
                health_check_interval=30,
            )
            self._client.ping()
            logger.info("Redis cache connected: %s", settings.redis_url)
        except RedisError as exc:
            self._available = False
            logger.warning("Redis cache unavailable, continuing without cache: %s", exc)

    @property
    def available(self) -> bool:
        return self._available and self._client is not None

    def _safe(self, operation: str, func, fallback):
        if not self.available:
            return fallback
        try:
            return func()
        except RedisError as exc:
            self._available = False
            logger.warning("Redis %s failed, cache disabled for this process: %s", operation, exc)
            return fallback

    def health(self) -> bool:
        if not self.available:
            return False
        return bool(self._safe("ping", self._client.ping, False))

    @property
    def embedding_model_id(self) -> str:
        if settings.is_test:
            return "fake-256"
        provider = settings.embedding_provider.lower()
        if provider in {"bge_m3", "bge-m3", "bge"}:
            return f"bge-m3:{settings.bge_m3_model}"
        return f"qwen:{settings.qwen_embedding_model}"

    def _embedding_key(self, text: str) -> str:
        return f"docflow:embedding:{_sha(self.embedding_model_id)}:{_sha(text)}"

    def get_embeddings(self, texts: list[str]) -> list[list[float] | None]:
        if not self.available or not texts:
            return [None] * len(texts)
        keys = [self._embedding_key(text) for text in texts]
        values = self._safe("mget", lambda: self._client.mget(keys), [None] * len(keys))
        output: list[list[float] | None] = []
        for value in values or []:
            try:
                output.append(json.loads(value) if value else None)
            except (TypeError, json.JSONDecodeError):
                output.append(None)
        if len(output) < len(texts):
            output.extend([None] * (len(texts) - len(output)))
        return output

    def set_embeddings(self, texts: list[str], vectors: list[list[float]]) -> None:
        if not self.available or not texts:
            return
        ttl = max(60, int(settings.redis_embedding_ttl_seconds))
        def write():
            pipe = self._client.pipeline(transaction=False)
            for text, vector in zip(texts, vectors):
                pipe.setex(self._embedding_key(text), ttl, json.dumps(vector, separators=(",", ":")))
            pipe.execute()
        self._safe("set_embeddings", write, None)

    def kb_versions(self, kb_ids: list[int]) -> list[int]:
        if not self.available:
            return [0] * len(kb_ids)
        keys = [f"docflow:kbver:{int(kb_id)}" for kb_id in kb_ids]
        values = self._safe("kb_versions", lambda: self._client.mget(keys), [None] * len(keys))
        return [int(value or 0) for value in values or []]

    def bump_kb_versions(self, kb_ids: list[int]) -> None:
        if not self.available or not kb_ids:
            return
        def write():
            pipe = self._client.pipeline(transaction=False)
            for kb_id in set(kb_ids):
                pipe.incr(f"docflow:kbver:{int(kb_id)}")
            pipe.execute()
        self._safe("bump_kb_versions", write, None)

    def answer_key(
        self,
        *,
        user_id: int,
        kb_ids: list[int],
        question: str,
        model: str,
        temperature: float,
        top_p: float,
        max_tokens: int,
        history_turns: int,
    ) -> str:
        versions = self.kb_versions(kb_ids)
        payload = json.dumps(
            {
                "user_id": int(user_id),
                "kb_ids": sorted(int(item) for item in kb_ids),
                "kb_versions": versions,
                "question": " ".join(question.lower().split()),
                "model": model,
                "temperature": round(float(temperature), 3),
                "top_p": round(float(top_p), 3),
                "max_tokens": int(max_tokens),
                "history_turns": int(history_turns),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return f"docflow:answer:{_sha(payload)}"

    def get_answer(self, key: str) -> dict[str, Any] | None:
        if not self.available:
            return None
        raw = self._safe("get_answer", lambda: self._client.get(key), None)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def set_answer(self, key: str, payload: dict[str, Any]) -> None:
        if not self.available:
            return
        ttl = max(60, int(settings.redis_answer_ttl_seconds))
        self._safe(
            "set_answer",
            lambda: self._client.setex(
                key,
                ttl,
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            ),
            None,
        )


@lru_cache(maxsize=1)
def get_cache() -> RedisCache:
    return RedisCache()
