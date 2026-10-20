from __future__ import annotations

from tests.test_knowledge import SAMPLE_TEXT, _create_kb


def test_streaming_chat_returns_citations_and_saves_history(client, auth_headers):
    kb_id = _create_kb(client, auth_headers)
    upload = client.post(
        f"/api/knowledge-bases/{kb_id}/documents",
        headers=auth_headers,
        files={"file": ("websocket.md", SAMPLE_TEXT.encode("utf-8"), "text/markdown")},
        data={"chunk_size": "240", "overlap": "30", "retrieval_mode": "hybrid"},
    )
    assert upload.status_code == 201, upload.text

    session = client.post(
        "/api/sessions",
        headers=auth_headers,
        json={
            "title": "新对话",
            "model": "qwen-max",
            "temperature": 0.2,
            "top_p": 0.8,
            "max_tokens": 1024,
            "history_turns": 5,
        },
    )
    assert session.status_code == 201
    session_id = session.json()["id"]

    with client.stream(
        "POST",
        "/api/chat/stream",
        headers=auth_headers,
        json={
            "session_id": session_id,
            "question": "WebSocket 空闲多久会断开？",
            "knowledge_base_ids": [kb_id],
            "model": "qwen-max",
            "temperature": 0.1,
            "top_p": 0.7,
            "max_tokens": 512,
            "history_turns": 5,
        },
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert "event: meta" in body
    assert "citations" in body
    assert "event: token" in body
    assert "event: done" in body

    messages = client.get(
        f"/api/sessions/{session_id}/messages",
        headers=auth_headers,
    )
    assert messages.status_code == 200
    history = messages.json()
    assert [item["role"] for item in history] == ["user", "assistant"]
    assert history[-1]["content"]
    assert history[-1]["citations"]


def test_session_crud(client, auth_headers):
    created = client.post("/api/sessions", headers=auth_headers, json={"title": "测试会话"})
    assert created.status_code == 201
    session_id = created.json()["id"]

    updated = client.patch(
        f"/api/sessions/{session_id}",
        headers=auth_headers,
        json={"title": "重命名会话"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "重命名会话"

    listed = client.get("/api/sessions", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    deleted = client.delete(f"/api/sessions/{session_id}", headers=auth_headers)
    assert deleted.status_code == 204
