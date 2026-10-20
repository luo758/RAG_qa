from __future__ import annotations

from tests.conftest import register_user


def test_employee_cannot_create_knowledge_base(client):
    employee_headers, _ = register_user(client, "plain_employee")
    response = client.post(
        "/api/knowledge-bases",
        headers=employee_headers,
        json={"name": "员工自建库"},
    )
    assert response.status_code == 403


def test_admin_can_crud_knowledge_base(client):
    admin_headers, _ = register_user(client, "crud_admin", role="admin")
    created = client.post(
        "/api/knowledge-bases",
        headers=admin_headers,
        json={"name": "API 参考", "description": "管理员创建"},
    )
    assert created.status_code == 201
    kb_id = created.json()["id"]

    updated = client.patch(
        f"/api/knowledge-bases/{kb_id}",
        headers=admin_headers,
        json={"name": "API 参考（新版）"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "API 参考（新版）"

    listed = client.get("/api/knowledge-bases", headers=admin_headers)
    assert any(item["id"] == kb_id for item in listed.json())

    deleted = client.delete(f"/api/knowledge-bases/{kb_id}", headers=admin_headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/knowledge-bases/{kb_id}", headers=admin_headers).status_code == 404


def test_only_super_admin_can_promote_employee(client):
    super_headers, _ = register_user(client, "root_admin", role="super_admin")
    admin_headers, _ = register_user(client, "normal_admin", role="admin")
    employee_headers, employee_id = register_user(client, "promote_me")

    users = client.get("/api/admin/users", headers=admin_headers)
    assert users.status_code == 200
    assert any(item["id"] == employee_id for item in users.json())

    forbidden = client.patch(
        f"/api/admin/users/{employee_id}/role",
        headers=admin_headers,
        json={"role": "admin"},
    )
    assert forbidden.status_code == 403

    promoted = client.patch(
        f"/api/admin/users/{employee_id}/role",
        headers=super_headers,
        json={"role": "admin"},
    )
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "admin"

    created = client.post(
        "/api/knowledge-bases",
        headers=employee_headers,
        json={"name": "新管理员创建的知识库"},
    )
    assert created.status_code == 201
