from __future__ import annotations


def test_register_login_and_me(client):
    captcha = client.get("/api/auth/captcha").json()
    response = client.post(
        "/api/auth/register",
        json={
            "username": "alice",
            "password": "StrongPass123",
            "confirm_password": "StrongPass123",
            "captcha_id": captcha["captcha_id"],
            "captcha_code": captcha["debug_code"],
        },
    )
    assert response.status_code == 201
    token = response.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "alice"

    captcha2 = client.get("/api/auth/captcha").json()
    login = client.post(
        "/api/auth/login",
        json={
            "username": "alice",
            "password": "StrongPass123",
            "captcha_id": captcha2["captcha_id"],
            "captcha_code": captcha2["debug_code"],
        },
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"


def test_register_rejects_mismatched_password(client):
    captcha = client.get("/api/auth/captcha").json()
    response = client.post(
        "/api/auth/register",
        json={
            "username": "bob",
            "password": "StrongPass123",
            "confirm_password": "DifferentPass123",
            "captcha_id": captcha["captcha_id"],
            "captcha_code": captcha["debug_code"],
        },
    )
    assert response.status_code == 400
    assert "不一致" in response.json()["detail"]


def test_captcha_is_single_use(client):
    captcha = client.get("/api/auth/captcha").json()
    payload = {
        "username": "captcha_user",
        "password": "StrongPass123",
        "confirm_password": "StrongPass123",
        "captcha_id": captcha["captcha_id"],
        "captcha_code": captcha["debug_code"],
    }
    first = client.post("/api/auth/register", json=payload)
    second = client.post("/api/auth/register", json={**payload, "username": "another_user"})
    assert first.status_code == 201
    assert second.status_code == 400


def test_protected_endpoint_requires_token(client):
    response = client.get("/api/knowledge-bases")
    assert response.status_code == 401


def test_register_short_password_returns_chinese_validation(client):
    captcha = client.get("/api/auth/captcha").json()
    response = client.post(
        "/api/auth/register",
        json={
            "username": "shortpass",
            "password": "123456",
            "confirm_password": "123456",
            "captcha_id": captcha["captcha_id"],
            "captcha_code": captcha["debug_code"],
        },
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "密码至少需要 8 个字符" in detail
    assert "确认密码至少需要 8 个字符" in detail
