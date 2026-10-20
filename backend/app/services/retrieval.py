from __future__ import annotations

import re
from dataclasses import dataclass

from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Document, DocumentChunk
from .embeddings import embed_texts
from .reranker import get_reranker
from .vector_store import VectorHit, get_vector_store


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: int
    document_id: int
    document_name: str
    knowledge_base_id: int
    content: str
    score: float


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    tokens = re.findall(r"[a-z0-9_]+", text)
    for segment in re.findall(r"[\u4e00-\u9fff]+", text):
        if len(segment) == 1:
            tokens.append(segment)
        else:
            tokens.extend(segment[index : index + 2] for index in range(len(segment) - 1))
    return tokens


def _chunks_by_ids(db: Session, chunk_ids: list[int]) -> dict[int, tuple[DocumentChunk, Document]]:
    if not chunk_ids:
        return {}
    rows = db.execute(
        select(DocumentChunk, Document)
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(DocumentChunk.id.in_(chunk_ids))
    ).all()
    return {row[0].id: (row[0], row[1]) for row in rows}


def _bm25_hits(db: Session, kb_ids: list[int], query: str, top_k: int) -> list[tuple[int, float]]:
    chunks = db.scalars(
        select(DocumentChunk).where(DocumentChunk.knowledge_base_id.in_(kb_ids))
    ).all()
    if not chunks:
        return []
    corpus = [_tokenize(chunk.content) for chunk in chunks]
    query_tokens = _tokenize(query)
    if not any(corpus) or not query_tokens:
        return []
    scores = BM25Okapi(corpus).get_scores(query_tokens)
    ranked = sorted(zip(chunks, scores), key=lambda item: item[1], reverse=True)
    return [(chunk.id, float(score)) for chunk, score in ranked[:top_k] if score > 0]


def retrieve_chunks(
    db: Session,
    *,
    kb_ids: list[int],
    query: str,
    retrieval_mode: str = "hybrid",
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    top_k = top_k or settings.retrieval_top_k
    embedding = embed_texts([query])[0]
    dense_hits = get_vector_store().search(
        embedding,
        kb_ids,
        max(top_k, settings.dense_top_k),
    )

    candidate_limit = max(top_k, settings.reranker_top_n)
    if retrieval_mode == "hybrid":
        bm25_hits = _bm25_hits(db, kb_ids, query, max(candidate_limit, settings.bm25_top_k))
        fused: dict[int, float] = {}
        for rank, hit in enumerate(dense_hits):
            fused[hit.chunk_id] = fused.get(hit.chunk_id, 0.0) + 1 / (60 + rank + 1)
        for rank, (chunk_id, _) in enumerate(bm25_hits):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 1 / (60 + rank + 1)
        ordered_ids = sorted(fused, key=fused.get, reverse=True)[:candidate_limit]
        scores = fused
    else:
        ordered_ids = [hit.chunk_id for hit in dense_hits[:candidate_limit]]
        scores = {hit.chunk_id: hit.score for hit in dense_hits}

    loaded = _chunks_by_ids(db, ordered_ids)
    reranker = get_reranker()
    if reranker is not None and loaded:
        rerank_ids = [chunk_id for chunk_id in ordered_ids if chunk_id in loaded]
        passages = [loaded[chunk_id][0].content for chunk_id in rerank_ids]
        rerank_scores = reranker.score(query, passages)
        rerank_map = {
            chunk_id: float(score)
            for chunk_id, score in zip(rerank_ids, rerank_scores)
        }
        ordered_ids = sorted(
            rerank_ids,
            key=lambda chunk_id: rerank_map.get(chunk_id, float("-inf")),
            reverse=True,
        )[:top_k]
        scores = rerank_map
    else:
        ordered_ids = ordered_ids[:top_k]

    output: list[RetrievedChunk] = []
    for chunk_id in ordered_ids:
        pair = loaded.get(chunk_id)
        if not pair:
            continue
        chunk, document = pair
        output.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=document.id,
                document_name=document.filename,
                knowledge_base_id=chunk.knowledge_base_id,
                content=chunk.content,
                score=float(scores.get(chunk_id, 0.0)),
            )
        )
    return output
