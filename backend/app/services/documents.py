from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Document, DocumentChunk, KnowledgeBase, KnowledgePermission, User
from .chunking import split_text
from .embeddings import embed_texts
from .parser import extract_text
from .vector_store import get_vector_store

logger = logging.getLogger(__name__)


MANAGER_ROLES = {"super_admin", "admin"}


def is_manager(user: User) -> bool:
    return user.role in MANAGER_ROLES


def _permission(db: Session, user: User, kb_id: int) -> KnowledgePermission | None:
    return db.scalar(
        select(KnowledgePermission).where(
            KnowledgePermission.knowledge_base_id == kb_id,
            KnowledgePermission.user_id == user.id,
        )
    )


def _check_kb_access(
    db: Session,
    user: User,
    kb: KnowledgeBase,
    *,
    require_manage: bool = False,
    require_upload: bool = False,
) -> None:
    if is_manager(user):
        return
    if require_manage:
        raise PermissionError("只有管理员可以管理知识库")
    permission = _permission(db, user, kb.id)
    if require_upload:
        if not permission or not permission.can_upload:
            raise PermissionError("当前账号没有该知识库的上传权限")
        return
    if not permission or not permission.can_view:
        raise PermissionError("当前账号没有该知识库的查看权限")


def get_accessible_knowledge_base(
    db: Session,
    user: User,
    kb_id: int,
    *,
    require_manage: bool = False,
    require_upload: bool = False,
) -> KnowledgeBase:
    kb = db.get(KnowledgeBase, kb_id)
    if not kb:
        raise LookupError("知识库不存在")
    _check_kb_access(
        db,
        user,
        kb,
        require_manage=require_manage,
        require_upload=require_upload,
    )
    return kb


def get_owned_knowledge_base(db: Session, user: User, kb_id: int) -> KnowledgeBase:
    return get_accessible_knowledge_base(db, user, kb_id, require_manage=True)


def get_accessible_document(
    db: Session,
    user: User,
    document_id: int,
    *,
    require_manage: bool = False,
) -> tuple[Document, KnowledgeBase]:
    row = db.execute(
        select(Document, KnowledgeBase)
        .join(KnowledgeBase, Document.knowledge_base_id == KnowledgeBase.id)
        .where(Document.id == document_id)
    ).first()
    if not row:
        raise LookupError("文档不存在")
    document, kb = row
    _check_kb_access(db, user, kb, require_manage=require_manage)
    return document, kb


def get_owned_document(db: Session, user: User, document_id: int) -> tuple[Document, KnowledgeBase]:
    return get_accessible_document(db, user, document_id, require_manage=True)

def _vector_record(chunk: DocumentChunk, vector: list[float]) -> dict:
    return {
        "id": int(chunk.id),
        "vector": vector,
        "kb_id": int(chunk.knowledge_base_id),
        "document_id": int(chunk.document_id),
        "content": chunk.content[:65000],
    }


def process_document(db: Session, document: Document) -> Document:
    try:
        text = extract_text(Path(document.storage_path))
        pieces = split_text(text, document.chunk_size, document.overlap)
        if not pieces:
            raise ValueError("文档中没有可解析的文本")
        chunks = [
            DocumentChunk(
                document_id=document.id,
                knowledge_base_id=document.knowledge_base_id,
                chunk_index=index,
                content=piece,
                metadata_json={
                    "source": document.filename,
                    "file_type": document.file_type,
                    "chunk_index": index,
                },
            )
            for index, piece in enumerate(pieces)
        ]
        db.add_all(chunks)
        db.flush()
        vectors = embed_texts([chunk.content for chunk in chunks])
        get_vector_store().upsert(
            [_vector_record(chunk, vector) for chunk, vector in zip(chunks, vectors)]
        )
        document.char_count = len(text)
        document.status = "ready"
        document.error_message = None
        db.commit()
        db.refresh(document)
        return document
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        document.status = "failed"
        document.error_message = str(exc)[:2000]
        db.commit()
        logger.exception("document processing failed: %s", document.filename)
        raise


def delete_document(db: Session, document: Document) -> None:
    chunk_ids = [chunk.id for chunk in document.chunks]
    if chunk_ids:
        get_vector_store().delete(chunk_ids)
    db.delete(document)
    db.commit()


def update_chunk(db: Session, chunk: DocumentChunk, content: str) -> DocumentChunk:
    vector = embed_texts([content])[0]
    chunk.content = content
    chunk.metadata_json = {**chunk.metadata_json, "edited": True}
    get_vector_store().upsert([_vector_record(chunk, vector)])
    db.commit()
    db.refresh(chunk)
    return chunk


def delete_chunk(db: Session, chunk: DocumentChunk) -> None:
    get_vector_store().delete([chunk.id])
    db.delete(chunk)
    db.commit()
