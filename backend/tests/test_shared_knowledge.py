from __future__ import annotations

from tests.conftest import register_user
from tests.test_knowledge import SAMPLE_TEXT


def _chat(client, headers, session_id: int, kb_id: int):
    return client.post(
        "/api/chat/stream",
        headers=headers,
        json={
            "session_id": session_id,
            "question": "WebSocket 空闲多久会断开？",
            "knowledge_base_ids": [kb_id],
            "history_turns": 5,
        },
    )


def test_employee_access_is_granted_explicitly(client):
    admin_headers, _ = register_user(client, "kb_admin", role="admin")
    employee_headers, employee_id = register_user(client, "kb_employee")

    kb_response = client.post(
        "/api/knowledge-bases",
        headers=admin_headers,
        json={"name": "共享 API 文档", "description": "员工按权限访问"},
    )
    assert kb_response.status_code == 201, kb_response.text
    kb = kb_response.json()
    assert kb["can_manage"] is True

    upload = client.post(
        f"/api/knowledge-bases/{kb['id']}/documents",
        headers=admin_headers,
        files={"file": ("websocket.md", SAMPLE_TEXT.encode("utf-8"), "text/markdown")},
        data={"chunk_size": "300", "overlap": "40", "retrieval_mode": "hybrid"},
    )
    assert upload.status_code == 201, upload.text
    document = upload.json()

    listed = client.get("/api/knowledge-bases", headers=employee_headers)
    assert listed.status_code == 200
    assert listed.json() == []

    session = client.post("/api/sessions", headers=employee_headers, json={"title": "越权测试"})
    forbidden_chat = _chat(client, employee_headers, session.json()["id"], kb["id"])
    assert forbidden_chat.status_code == 403

    permissions = client.get(
        f"/api/knowledge-bases/{kb['id']}/permissions",
        headers=admin_headers,
    )
    assert permissions.status_code == 200
    employee_permission = next(item for item in permissions.json() if item["user_id"] == employee_id)
    assert employee_permission["can_view"] is False

    granted = client.put(
        f"/api/knowledge-bases/{kb['id']}/permissions/{employee_id}",
        headers=admin_headers,
        json={"can_view": True, "can_upload": False},
    )
    assert granted.status_code == 200
    assert granted.json()["can_view"] is True

    listed = client.get("/api/knowledge-bases", headers=employee_headers)
    shared = next(item for item in listed.json() if item["id"] == kb["id"])
    assert shared["can_view"] is True
    assert shared["can_upload"] is False
    assert shared["can_manage"] is False

    detail = client.get(f"/api/documents/{document['id']}", headers=employee_headers)
    assert detail.status_code == 200
    assert detail.json()["can_manage"] is False
    assert detail.json()["chunks"]

    forbidden_upload = client.post(
        f"/api/knowledge-bases/{kb['id']}/documents",
        headers=employee_headers,
        files={"file": ("blocked.md", b"# blocked", "text/markdown")},
    )
    assert forbidden_upload.status_code == 403

    forbidden_delete = client.delete(f"/api/documents/{document['id']}", headers=employee_headers)
    assert forbidden_delete.status_code == 403
    forbidden_chunk = client.patch(
        f"/api/chunks/{detail.json()['chunks'][0]['id']}",
        headers=employee_headers,
        json={"content": "越权修改"},
    )
    assert forbidden_chunk.status_code == 403

    chat = _chat(client, employee_headers, session.json()["id"], kb["id"])
    assert chat.status_code == 200
    assert "event: meta" in chat.text
    assert "citations" in chat.text

    upload_permission = client.put(
        f"/api/knowledge-bases/{kb['id']}/permissions/{employee_id}",
        headers=admin_headers,
        json={"can_view": True, "can_upload": True},
    )
    assert upload_permission.status_code == 200
    allowed_upload = client.post(
        f"/api/knowledge-bases/{kb['id']}/documents",
        headers=employee_headers,
        files={"file": ("employee.md", b"# Employee upload\n\nAllowed.", "text/markdown")},
        data={"chunk_size": "300", "overlap": "40", "retrieval_mode": "hybrid"},
    )
    assert allowed_upload.status_code == 201, allowed_upload.text
    employee_document = allowed_upload.json()
    assert employee_document["can_manage"] is False

    employee_delete = client.delete(
        f"/api/documents/{employee_document['id']}",
        headers=employee_headers,
    )
    assert employee_delete.status_code == 403
