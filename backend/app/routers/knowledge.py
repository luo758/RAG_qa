from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Document, DocumentChunk, KnowledgeBase, KnowledgePermission, User
from ..schemas import (
    ChunkRead,
    ChunkUpdate,
    DocumentDetail,
    DocumentRead,
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
    KnowledgeBaseUpdate,
    KnowledgePermissionRead,
    KnowledgePermissionUpdate,
)
from ..services.cache import get_cache
from ..services.documents import (
    delete_chunk,
    delete_document,
    get_accessible_document,
    get_accessible_knowledge_base,
    get_owned_knowledge_base,
    is_manager,
    process_document,
    update_chunk,
)
from ..services.parser import SUPPORTED_EXTENSIONS

router = APIRouter(tags=["知识库"])
logger = logging.getLogger(__name__)


def _permission(db: Session, user: User, kb_id: int) -> KnowledgePermission | None:
    return db.scalar(
        select(KnowledgePermission).where(
            KnowledgePermission.knowledge_base_id == kb_id,
            KnowledgePermission.user_id == user.id,
        )
    )


def _kb_read(db: Session, kb: KnowledgeBase, user: User) -> KnowledgeBaseRead:
    manager = is_manager(user)
    permission = None if manager else _permission(db, user, kb.id)
    can_view = manager or bool(permission and permission.can_view)
    can_upload = manager or bool(permission and permission.can_upload)
    return KnowledgeBaseRead.model_validate(kb).model_copy(
        update={
            "is_owner": kb.user_id == user.id,
            "is_shared": bool(permission),
            "can_manage": manager,
            "can_view": can_view,
            "can_upload": can_upload,
        }
    )


def _read_kb_or_404(db: Session, user: User, kb_id: int) -> KnowledgeBase:
    try:
        return get_accessible_knowledge_base(db, user, kb_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _manage_kb_or_error(db: Session, user: User, kb_id: int) -> KnowledgeBase:
    try:
        return get_owned_knowledge_base(db, user, kb_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _upload_kb_or_error(db: Session, user: User, kb_id: int) -> KnowledgeBase:
    try:
        return get_accessible_knowledge_base(db, user, kb_id, require_upload=True)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _read_document_or_404(
    db: Session, user: User, document_id: int
) -> tuple[Document, KnowledgeBase]:
    try:
        return get_accessible_document(db, user, document_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _manage_document_or_error(
    db: Session, user: User, document_id: int
) -> tuple[Document, KnowledgeBase]:
    try:
        return get_accessible_document(db, user, document_id, require_manage=True)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/knowledge-bases", response_model=list[KnowledgeBaseRead])
def list_knowledge_bases(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[KnowledgeBaseRead]:
    if is_manager(user):
        items = db.scalars(
            select(KnowledgeBase).order_by(KnowledgeBase.updated_at.desc())
        ).all()
    else:
        items = db.scalars(
            select(KnowledgeBase)
            .join(
                KnowledgePermission,
                KnowledgePermission.knowledge_base_id == KnowledgeBase.id,
            )
            .where(
                KnowledgePermission.user_id == user.id,
                KnowledgePermission.can_view.is_(True),
            )
            .order_by(KnowledgeBase.updated_at.desc())
        ).all()
    return [_kb_read(db, item, user) for item in items]


@router.post("/knowledge-bases", response_model=KnowledgeBaseRead, status_code=201)
def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeBaseRead:
    if not is_manager(user):
        raise HTTPException(status_code=403, detail="只有管理员可以创建知识库")
    kb = KnowledgeBase(
        user_id=user.id,
        name=payload.name.strip(),
        description=payload.description.strip(),
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    get_cache().bump_kb_versions([kb.id])
    return _kb_read(db, kb, user)


@router.get("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseRead)
def get_knowledge_base(
    kb_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeBaseRead:
    return _kb_read(db, _read_kb_or_404(db, user, kb_id), user)


@router.patch("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseRead)
def update_knowledge_base(
    kb_id: int,
    payload: KnowledgeBaseUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeBaseRead:
    kb = _manage_kb_or_error(db, user, kb_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "is_shared":
            continue
        setattr(kb, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(kb)
    get_cache().bump_kb_versions([kb.id])
    return _kb_read(db, kb, user)


@router.delete("/knowledge-bases/{kb_id}", status_code=204)
def remove_knowledge_base(
    kb_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    kb = _manage_kb_or_error(db, user, kb_id)
    chunk_ids = list(
        db.scalars(select(DocumentChunk.id).where(DocumentChunk.knowledge_base_id == kb.id))
    )
    if chunk_ids:
        from ..services.vector_store import get_vector_store

        get_vector_store().delete(chunk_ids)
    for document in kb.documents:
        Path(document.storage_path).unlink(missing_ok=True)
    db.delete(kb)
    db.commit()
    get_cache().bump_kb_versions([kb.id])


@router.get(
    "/knowledge-bases/{kb_id}/permissions",
    response_model=list[KnowledgePermissionRead],
)
def list_permissions(
    kb_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[KnowledgePermissionRead]:
    kb = _manage_kb_or_error(db, user, kb_id)
    employees = db.scalars(
        select(User).where(User.role == "employee").order_by(User.username)
    ).all()
    permissions = {
        item.user_id: item
        for item in db.scalars(
            select(KnowledgePermission).where(
                KnowledgePermission.knowledge_base_id == kb.id
            )
        ).all()
    }
    return [
        KnowledgePermissionRead(
            user_id=employee.id,
            username=employee.username,
            can_view=bool(permissions.get(employee.id) and permissions[employee.id].can_view),
            can_upload=bool(permissions.get(employee.id) and permissions[employee.id].can_upload),
        )
        for employee in employees
    ]


@router.put(
    "/knowledge-bases/{kb_id}/permissions/{target_user_id}",
    response_model=KnowledgePermissionRead,
)
def set_permission(
    kb_id: int,
    target_user_id: int,
    payload: KnowledgePermissionUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgePermissionRead:
    kb = _manage_kb_or_error(db, user, kb_id)
    target = db.get(User, target_user_id)
    if not target or target.role != "employee":
        raise HTTPException(status_code=404, detail="员工账号不存在")
    permission = db.scalar(
        select(KnowledgePermission).where(
            KnowledgePermission.knowledge_base_id == kb.id,
            KnowledgePermission.user_id == target.id,
        )
    )
    if payload.can_view or payload.can_upload:
        if permission is None:
            permission = KnowledgePermission(
                knowledge_base_id=kb.id,
                user_id=target.id,
                granted_by=user.id,
            )
            db.add(permission)
        permission.can_view = payload.can_view
        permission.can_upload = payload.can_upload
    elif permission is not None:
        db.delete(permission)
    db.commit()
    get_cache().bump_kb_versions([kb.id])
    return KnowledgePermissionRead(
        user_id=target.id,
        username=target.username,
        can_view=payload.can_view,
        can_upload=payload.can_upload,
    )


@router.delete("/knowledge-bases/{kb_id}/permissions/{target_user_id}", status_code=204)
def delete_permission(
    kb_id: int,
    target_user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    kb = _manage_kb_or_error(db, user, kb_id)
    permission = db.scalar(
        select(KnowledgePermission).where(
            KnowledgePermission.knowledge_base_id == kb.id,
            KnowledgePermission.user_id == target_user_id,
        )
    )
    if permission:
        db.delete(permission)
        db.commit()
        get_cache().bump_kb_versions([kb.id])


@router.get("/knowledge-bases/{kb_id}/documents", response_model=list[DocumentRead])
def list_documents(
    kb_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentRead]:
    kb = _read_kb_or_404(db, user, kb_id)
    manager = is_manager(user)
    documents = db.scalars(
        select(Document)
        .where(Document.knowledge_base_id == kb.id)
        .order_by(Document.created_at.desc())
    ).all()
    return [
        DocumentRead.model_validate(document).model_copy(
            update={"can_manage": manager}
        )
        for document in documents
    ]


@router.post(
    "/knowledge-bases/{kb_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    chunk_size: int = Form(800),
    overlap: int = Form(100),
    retrieval_mode: str = Form("hybrid"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentRead:
    kb = _upload_kb_or_error(db, user, kb_id)
    filename = Path(file.filename or "document").name
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型：{suffix}")
    if not 100 <= chunk_size <= 5000:
        raise HTTPException(status_code=400, detail="切块大小必须在 100 到 5000 之间")
    if overlap < 0 or overlap >= chunk_size:
        raise HTTPException(status_code=400, detail="重叠长度必须小于切块大小")
    if retrieval_mode not in {"dense", "hybrid"}:
        raise HTTPException(status_code=400, detail="检索模式只能是 dense 或 hybrid")

    content = await file.read()
    if len(content) > settings.upload_max_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"文件不能超过 {settings.upload_max_mb} MB")

    directory = settings.upload_dir / str(user.id) / str(kb.id)
    directory.mkdir(parents=True, exist_ok=True)
    storage_path = directory / f"{uuid4().hex}{suffix}"
    storage_path.write_bytes(content)

    document = Document(
        knowledge_base_id=kb.id,
        filename=filename,
        file_type=suffix.lstrip("."),
        storage_path=str(storage_path),
        chunk_size=chunk_size,
        overlap=overlap,
        retrieval_mode=retrieval_mode,
        status="processing",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        document = process_document(db, document)
        get_cache().bump_kb_versions([kb.id])
    except Exception as exc:  # noqa: BLE001
        logger.exception("upload processing failed")
        raise HTTPException(status_code=422, detail=f"文档解析失败：{exc}") from exc
    return DocumentRead.model_validate(document).model_copy(
        update={"can_manage": is_manager(user)}
    )


@router.get("/documents/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentDetail:
    document, _ = _read_document_or_404(db, user, document_id)
    manager = is_manager(user)
    return DocumentDetail(
        **DocumentRead.model_validate(document).model_dump(exclude={"can_manage"}),
        can_manage=manager,
        chunks=[ChunkRead.model_validate(chunk) for chunk in document.chunks],
    )


@router.get("/documents/{document_id}/chunks", response_model=list[ChunkRead])
def get_document_chunks(
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentChunk]:
    document, _ = _read_document_or_404(db, user, document_id)
    return list(document.chunks)


@router.delete("/documents/{document_id}", status_code=204)
def remove_document(
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    document, _ = _manage_document_or_error(db, user, document_id)
    path = Path(document.storage_path)
    kb_id = document.knowledge_base_id
    delete_document(db, document)
    get_cache().bump_kb_versions([kb_id])
    path.unlink(missing_ok=True)


def _managed_chunk(db: Session, user: User, chunk_id: int) -> DocumentChunk:
    if not is_manager(user):
        raise HTTPException(status_code=403, detail="只有管理员可以修改文档块")
    row = db.execute(
        select(DocumentChunk)
        .join(Document, DocumentChunk.document_id == Document.id)
        .join(KnowledgeBase, Document.knowledge_base_id == KnowledgeBase.id)
        .where(DocumentChunk.id == chunk_id)
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="文档块不存在")
    return row


@router.patch("/chunks/{chunk_id}", response_model=ChunkRead)
def edit_chunk(
    chunk_id: int,
    payload: ChunkUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentChunk:
    chunk = _managed_chunk(db, user, chunk_id)
    updated = update_chunk(db, chunk, payload.content)
    get_cache().bump_kb_versions([chunk.knowledge_base_id])
    return updated


@router.delete("/chunks/{chunk_id}", status_code=204)
def remove_chunk(
    chunk_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    chunk = _managed_chunk(db, user, chunk_id)
    kb_id = chunk.knowledge_base_id
    delete_chunk(db, chunk)
    get_cache().bump_kb_versions([kb_id])
