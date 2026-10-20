from __future__ import annotations

import pytest


SAMPLE_TEXT = """# WebSocket 连接指南

WebSocket 连接默认空闲超时为 10 分钟。客户端应每 30 秒发送一次 ping。

## 断线重连

如果连接中断，客户端应使用指数退避重连，并携带 request_id。

```python
await websocket.send_json({"type": "ping"})
```

## 常见错误

错误码 4010 表示鉴权过期，需要重新获取 access_token。
"""


def _create_kb(client, headers, name="API 文档"):
    response = client.post(
        "/api/knowledge-bases",
        headers=headers,
        json={"name": name, "description": "测试知识库"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_upload_parse_preview_edit_and_delete(client, auth_headers):
    kb_id = _create_kb(client, auth_headers)
    upload = client.post(
        f"/api/knowledge-bases/{kb_id}/documents",
        headers=auth_headers,
        files={"file": ("websocket.md", SAMPLE_TEXT.encode("utf-8"), "text/markdown")},
        data={"chunk_size": "300", "overlap": "40", "retrieval_mode": "hybrid"},
    )
    assert upload.status_code == 201, upload.text
    document = upload.json()
    assert document["status"] == "ready"
    assert document["char_count"] > 0

    detail = client.get(f"/api/documents/{document['id']}", headers=auth_headers)
    assert detail.status_code == 200
    chunks = detail.json()["chunks"]
    assert chunks

    updated = client.patch(
        f"/api/chunks/{chunks[0]['id']}",
        headers=auth_headers,
        json={"content": chunks[0]["content"] + "\n\n人工补充说明。"},
    )
    assert updated.status_code == 200
    assert "人工补充说明" in updated.json()["content"]

    deleted_chunk = client.delete(f"/api/chunks/{chunks[0]['id']}", headers=auth_headers)
    assert deleted_chunk.status_code == 204

    deleted_document = client.delete(f"/api/documents/{document['id']}", headers=auth_headers)
    assert deleted_document.status_code == 204


def test_rejects_unsupported_file(client, auth_headers):
    kb_id = _create_kb(client, auth_headers, "临时库")
    response = client.post(
        f"/api/knowledge-bases/{kb_id}/documents",
        headers=auth_headers,
        files={"file": ("virus.exe", b"not-a-doc", "application/octet-stream")},
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("architecture.pdf", "application/pdf"),
        ("release-notes.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        ("troubleshooting.png", "image/png"),
    ],
)
def test_upload_supported_formats(client, auth_headers, filename, content_type):
    from pathlib import Path

    sample = Path(__file__).resolve().parents[1] / "data" / "sample_docs" / filename
    kb_id = _create_kb(client, auth_headers, f"格式测试-{filename}")
    response = client.post(
        f"/api/knowledge-bases/{kb_id}/documents",
        headers=auth_headers,
        files={"file": (filename, sample.read_bytes(), content_type)},
        data={"chunk_size": "500", "overlap": "50", "retrieval_mode": "dense"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "ready"
