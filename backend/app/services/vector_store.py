from __future__ import annotations

import math
import threading
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from pymilvus import DataType, MilvusClient

from ..config import settings


@dataclass(frozen=True)
class VectorHit:
    chunk_id: int
    score: float


class VectorStore(Protocol):
    def upsert(self, records: list[dict]) -> None: ...
    def delete(self, chunk_ids: list[int]) -> None: ...
    def search(self, query_vector: list[float], kb_ids: list[int], top_k: int) -> list[VectorHit]: ...


class MilvusVectorStore:
    def __init__(self) -> None:
        self.client = MilvusClient(
            uri=f"http://{settings.milvus_host}:{settings.milvus_port}",
            db_name=settings.milvus_database,
            timeout=20,
        )
        self.collection = settings.milvus_collection
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        if self.client.has_collection(self.collection):
            self.client.load_collection(self.collection)
            return

        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field("id", DataType.INT64, is_primary=True)
        schema.add_field("vector", DataType.FLOAT_VECTOR, dim=settings.embedding_dim)
        schema.add_field("kb_id", DataType.INT64)
        schema.add_field("document_id", DataType.INT64)
        schema.add_field("content", DataType.VARCHAR, max_length=65535)
        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="AUTOINDEX",
            metric_type="COSINE",
        )
        self.client.create_collection(
            collection_name=self.collection,
            schema=schema,
            index_params=index_params,
        )
        self.client.load_collection(self.collection)

    def upsert(self, records: list[dict]) -> None:
        if records:
            self.client.upsert(collection_name=self.collection, data=records)

    def delete(self, chunk_ids: list[int]) -> None:
        if chunk_ids:
            self.client.delete(collection_name=self.collection, ids=chunk_ids)

    def search(self, query_vector: list[float], kb_ids: list[int], top_k: int) -> list[VectorHit]:
        if not kb_ids:
            return []
        filter_expr = f"kb_id in [{', '.join(str(int(item)) for item in kb_ids)}]"
        result = self.client.search(
            collection_name=self.collection,
            data=[query_vector],
            filter=filter_expr,
            limit=top_k,
            output_fields=["kb_id", "document_id"],
            search_params={"metric_type": "COSINE", "params": {}},
        )
        hits = result[0] if result else []
        return [
            VectorHit(chunk_id=int(hit["id"]), score=float(hit.get("distance", 0.0)))
            for hit in hits
        ]


class MemoryVectorStore:
    def __init__(self) -> None:
        self._items: dict[int, tuple[list[float], dict]] = {}
        self._lock = threading.Lock()

    def upsert(self, records: list[dict]) -> None:
        with self._lock:
            for record in records:
                self._items[int(record["id"])] = (
                    [float(value) for value in record["vector"]],
                    {
                        "kb_id": int(record["kb_id"]),
                        "document_id": int(record["document_id"]),
                        "content": record.get("content", ""),
                    },
                )

    def delete(self, chunk_ids: list[int]) -> None:
        with self._lock:
            for chunk_id in chunk_ids:
                self._items.pop(int(chunk_id), None)

    def search(self, query_vector: list[float], kb_ids: list[int], top_k: int) -> list[VectorHit]:
        allowed = {int(item) for item in kb_ids}
        scored: list[VectorHit] = []
        query_norm = math.sqrt(sum(value * value for value in query_vector)) or 1.0
        with self._lock:
            for chunk_id, (vector, metadata) in self._items.items():
                if metadata["kb_id"] not in allowed:
                    continue
                denominator = (
                    math.sqrt(sum(value * value for value in vector)) * query_norm
                ) or 1.0
                score = sum(a * b for a, b in zip(query_vector, vector)) / denominator
                scored.append(VectorHit(chunk_id=chunk_id, score=score))
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStore:
    if settings.is_test:
        return MemoryVectorStore()
    return MilvusVectorStore()
