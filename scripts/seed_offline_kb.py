from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(SCRIPTS))

from offline_docs import write_offline_documents  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402
from app.models import (  # noqa: E402
    Document,
    DocumentChunk,
    KnowledgeBase,
    KnowledgePermission,
    User,
)
from app.security import hash_password  # noqa: E402
from app.services.cache import get_cache  # noqa: E402
from app.services.documents import process_document  # noqa: E402
from app.services.vector_store import get_vector_store  # noqa: E402
from sqlalchemy import select  # noqa: E402


KB_NAME = "企业离线知识库"
KB_DESCRIPTION = "预置来画智能创作平台的产品手册、技术文档与 API 参考资料，可直接用于检索问答演示。"


def ensure_user(db, username: str, password: str, role: str) -> User:
    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        user = User(username=username, password_hash=hash_password(password), role=role)
        db.add(user)
        db.flush()
    else:
        user.role = role
        user.password_hash = hash_password(password)
        user.is_active = True
    db.commit()
    db.refresh(user)
    return user


def ensure_knowledge_base(db, admin: User) -> KnowledgeBase:
    kb = db.scalar(
        select(KnowledgeBase).where(
            KnowledgeBase.name == KB_NAME,
            KnowledgeBase.user_id == admin.id,
        )
    )
    if kb is None:
        kb = KnowledgeBase(
            user_id=admin.id,
            name=KB_NAME,
            description=KB_DESCRIPTION,
            is_shared=True,
        )
        db.add(kb)
        db.commit()
        db.refresh(kb)
    return kb


def grant_employee_access(db, kb: KnowledgeBase, employee: User, granter: User) -> None:
    permission = db.scalar(
        select(KnowledgePermission).where(
            KnowledgePermission.knowledge_base_id == kb.id,
            KnowledgePermission.user_id == employee.id,
        )
    )
    if permission is None:
        permission = KnowledgePermission(
            knowledge_base_id=kb.id,
            user_id=employee.id,
            granted_by=granter.id,
        )
        db.add(permission)
    permission.can_view = True
    permission.can_upload = True
    db.commit()


def import_document(db, kb: KnowledgeBase, source: Path) -> tuple[Document, bool]:
    existing = db.scalar(
        select(Document).where(
            Document.knowledge_base_id == kb.id,
            Document.filename == source.name,
        )
    )
    if existing and existing.status == "ready" and existing.chunks:
        return existing, False

    if existing:
        chunk_ids = [chunk.id for chunk in existing.chunks]
        if chunk_ids:
            get_vector_store().delete(chunk_ids)
        Path(existing.storage_path).unlink(missing_ok=True)
        db.delete(existing)
        db.commit()

    target_dir = settings.upload_dir / "offline-seed" / str(kb.id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    document = Document(
        knowledge_base_id=kb.id,
        filename=source.name,
        file_type=source.suffix.lstrip("."),
        storage_path=str(target.resolve()),
        chunk_size=900,
        overlap=120,
        retrieval_mode="hybrid",
        status="processing",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    try:
        document = process_document(db, document)
        get_cache().bump_kb_versions([kb.id])
    except Exception:
        db.rollback()
        raise
    return document, True


def main() -> None:
    init_db()
    sample_dir = ROOT / "backend" / "data" / "sample_docs"
    write_offline_documents(sample_dir)

    super_password = os.getenv("SEED_SUPERADMIN_PASSWORD", "SuperAdmin@2026")
    admin_password = os.getenv("SEED_ADMIN_PASSWORD", "Admin@2026")
    employee_password = os.getenv("SEED_EMPLOYEE_PASSWORD", "Employee@2026")

    with SessionLocal() as db:
        super_admin = ensure_user(db, "superadmin", super_password, "super_admin")
        admin = ensure_user(db, "admin", admin_password, "admin")
        employee = ensure_user(db, "employee", employee_password, "employee")

        kb = ensure_knowledge_base(db, admin)
        grant_employee_access(db, kb, employee, super_admin)

        sources = [
            sample_dir / "product-manual.md",
            sample_dir / "technical-docs.md",
            sample_dir / "api-reference.md",
        ]
        created = 0
        skipped = 0
        for source in sources:
            document, was_created = import_document(db, kb, source)
            chunk_count = db.scalar(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document.id)
                .with_only_columns(DocumentChunk.id)
                .limit(1)
            )
            if was_created:
                created += 1
            else:
                skipped += 1
            print(
                f"[seed] {source.name}: status={document.status} "
                f"chars={document.char_count} first_chunk={bool(chunk_count)} "
                f"{'created' if was_created else 'skipped'}"
            )

    print(f"[seed] knowledge_base_id={kb.id} documents_created={created} skipped={skipped}")
    print(f"[seed] super_admin={super_admin.username} / {super_password}")
    print(f"[seed] admin={admin.username} / {admin_password}")
    print(f"[seed] employee={employee.username} / {employee_password} (view + upload)")


if __name__ == "__main__":
    main()
