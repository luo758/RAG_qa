from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET"] = "docflow-test-secret-at-least-32-characters"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="docflow-upload-")

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.services.vector_store import get_vector_store  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    store = get_vector_store()
    if hasattr(store, "clear"):
        store.clear()
    yield


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def register_user(
    client: TestClient,
    username: str,
    *,
    role: str = "employee",
    password: str = "StrongPass123",
) -> tuple[dict[str, str], int]:
    captcha = client.get("/api/auth/captcha").json()
    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": password,
            "confirm_password": password,
            "captcha_id": captcha["captcha_id"],
            "captcha_code": captcha["debug_code"],
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    user_id = int(payload["user"]["id"])
    if role != "employee":
        with SessionLocal() as db:
            user = db.get(User, user_id)
            assert user is not None
            user.role = role
            db.commit()
    return {"Authorization": f"Bearer {payload['access_token']}"}, user_id


@pytest.fixture()
def auth_headers(client: TestClient) -> dict[str, str]:
    headers, _ = register_user(client, "demo_admin", role="admin")
    return headers


@pytest.fixture()
def employee_headers(client: TestClient) -> dict[str, str]:
    headers, _ = register_user(client, "demo_employee")
    return headers
