from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import settings


class Base(DeclarativeBase):
    pass


engine_kwargs: dict = {"pool_pre_ping": True, "future": True}
if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    if ":memory:" in settings.database_url:
        engine_kwargs["poolclass"] = StaticPool

engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "role" not in user_columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE users "
                        "ADD COLUMN role VARCHAR(32) NOT NULL DEFAULT 'employee'"
                    )
                )
    if "knowledge_bases" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("knowledge_bases")}
        if "is_shared" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE knowledge_bases "
                        "ADD COLUMN is_shared BOOLEAN NOT NULL DEFAULT 0"
                    )
                )
