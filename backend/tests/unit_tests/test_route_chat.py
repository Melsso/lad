from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.exc import SQLAlchemyError

from lad.routes import chat as chat_routes

CREATED_AT = "2026-01-01T00:00:00+00:00"


def _db_error():
    return AsyncMock(side_effect=SQLAlchemyError("boom"))


def test_create_chat_rejects_invalid_mode(client):
    response = client.post("/chat/create", json={"title": "hi", "mode": "bogus"})

    assert response.status_code == 422


def test_create_chat_success(monkeypatch, client):
    created = MagicMock(id=1, title="hello world", mode="chat", created_at=CREATED_AT)
    monkeypatch.setattr(chat_routes, "create_chat", AsyncMock(return_value=created))

    response = client.post("/chat/create", json={"title": "hello world"})

    assert response.status_code == 200
    assert response.json()["title"] == "hello world"


def test_create_chat_defaults_when_no_title(monkeypatch, client):
    captured = {}

    async def fake_create_chat(db, title, mode):
        captured["title"] = title
        return MagicMock(id=1, title=title, mode=mode, created_at=CREATED_AT)

    monkeypatch.setattr(chat_routes, "create_chat", fake_create_chat)

    response = client.post("/chat/create", json={})

    assert response.status_code == 200
    assert captured["title"] == "New Chat"


def test_create_chat_truncates_long_title(monkeypatch, client):
    captured = {}

    async def fake_create_chat(db, title, mode):
        captured["title"] = title
        return MagicMock(id=1, title=title, mode=mode, created_at=CREATED_AT)

    monkeypatch.setattr(chat_routes, "create_chat", fake_create_chat)

    response = client.post("/chat/create", json={"title": "x" * 80})

    assert response.status_code == 200
    assert len(captured["title"]) == 50
    assert captured["title"].endswith("...")


def test_create_chat_db_error(monkeypatch, client):
    monkeypatch.setattr(chat_routes, "create_chat", _db_error())

    response = client.post("/chat/create", json={"title": "hi"})

    assert response.status_code == 500


def test_update_chat_title_success(monkeypatch, client):
    updated = MagicMock(id=1, title="New Title", mode="chat", created_at=CREATED_AT)
    monkeypatch.setattr(
        chat_routes, "update_chat_title", AsyncMock(return_value=updated)
    )

    response = client.patch("/chat/title", json={"chat_id": 1, "title": "New Title"})

    assert response.status_code == 200
    assert response.json()["title"] == "New Title"


def test_update_chat_title_rejects_empty_title(client):
    response = client.patch("/chat/title", json={"chat_id": 1, "title": "   "})

    assert response.status_code == 400


def test_update_chat_title_not_found(monkeypatch, client):
    monkeypatch.setattr(chat_routes, "update_chat_title", AsyncMock(return_value=None))

    response = client.patch("/chat/title", json={"chat_id": 999, "title": "New Title"})

    assert response.status_code == 404


def test_update_chat_title_db_error(monkeypatch, client):
    monkeypatch.setattr(chat_routes, "update_chat_title", _db_error())

    response = client.patch("/chat/title", json={"chat_id": 1, "title": "New Title"})

    assert response.status_code == 500


def test_get_chat_messages_success(monkeypatch, client):
    fake_messages = [
        {
            "id": 1,
            "chat_id": 1,
            "content": "hi",
            "role": "user",
            "created_at": CREATED_AT,
        }
    ]
    monkeypatch.setattr(
        chat_routes, "get_chat_messages", AsyncMock(return_value=fake_messages)
    )

    response = client.get("/chat/messages", params={"chat_id": 1})

    assert response.status_code == 200
    assert response.json()[0]["content"] == "hi"


def test_get_chat_messages_db_error(monkeypatch, client):
    monkeypatch.setattr(chat_routes, "get_chat_messages", _db_error())

    response = client.get("/chat/messages", params={"chat_id": 1})

    assert response.status_code == 500


def test_get_chat_endpoint_success(monkeypatch, client):
    chat = MagicMock(id=1, title="hello", mode="chat", created_at=CREATED_AT)
    monkeypatch.setattr(chat_routes, "get_chat", AsyncMock(return_value=chat))

    response = client.get("/chat/1")

    assert response.status_code == 200
    assert response.json()["mode"] == "chat"


def test_get_chat_endpoint_not_found(monkeypatch, client):
    monkeypatch.setattr(chat_routes, "get_chat", AsyncMock(return_value=None))

    response = client.get("/chat/999")

    assert response.status_code == 404


def test_get_chat_endpoint_db_error(monkeypatch, client):
    monkeypatch.setattr(chat_routes, "get_chat", _db_error())

    response = client.get("/chat/1")

    assert response.status_code == 500


def test_get_chat_endpoint_does_not_shadow_messages_route(monkeypatch, client):
    monkeypatch.setattr(chat_routes, "get_chat_messages", AsyncMock(return_value=[]))

    response = client.get("/chat/messages", params={"chat_id": 1})

    assert response.status_code == 200
    assert response.json() == []


def test_stream_msg_chat_not_found(monkeypatch, client):
    monkeypatch.setattr(chat_routes, "get_chat", AsyncMock(return_value=None))

    response = client.post(
        "/chat/msg/stream", data={"chat_id": 999, "msg": "hi"}, files=[]
    )

    assert response.status_code == 404


def test_stream_msg_db_error_on_lookup(monkeypatch, client):
    monkeypatch.setattr(chat_routes, "get_chat", _db_error())

    response = client.post(
        "/chat/msg/stream", data={"chat_id": 1, "msg": "hi"}, files=[]
    )

    assert response.status_code == 500


def test_stream_msg_success_returns_sse_stream(monkeypatch, client):
    monkeypatch.setattr(
        chat_routes, "get_chat", AsyncMock(return_value=MagicMock(id=1, mode="agent"))
    )

    async def fake_stream(chat_id, msg, attached_filenames=None):
        yield 'event: chunk\ndata: {"text": "hi"}\n\n'
        yield 'event: done\ndata: {"id": 1}\n\n'

    monkeypatch.setattr(chat_routes, "stream_chat_msg", fake_stream)

    response = client.post(
        "/chat/msg/stream", data={"chat_id": 1, "msg": "hi"}, files=[]
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: chunk" in response.text
    assert "event: done" in response.text


def test_stream_msg_rejects_too_many_files(monkeypatch, client):
    monkeypatch.setattr(
        chat_routes, "get_chat", AsyncMock(return_value=MagicMock(id=1, mode="agent"))
    )

    def raise_too_many(files):
        raise ValueError("Too many files attached")

    monkeypatch.setattr(chat_routes, "validate_uploads", raise_too_many)

    response = client.post(
        "/chat/msg/stream",
        data={"chat_id": 1, "msg": "hi"},
        files=[("files", ("a.txt", b"x", "text/plain"))],
    )

    assert response.status_code == 400
    assert "Too many files" in response.json()["detail"]


def test_stream_msg_rejects_invalid_extension(monkeypatch, client):
    monkeypatch.setattr(
        chat_routes, "get_chat", AsyncMock(return_value=MagicMock(id=1, mode="agent"))
    )

    def raise_bad_extension(files):
        raise ValueError("File type '.exe' is not allowed: virus.exe")

    monkeypatch.setattr(chat_routes, "validate_uploads", raise_bad_extension)

    response = client.post(
        "/chat/msg/stream",
        data={"chat_id": 1, "msg": "hi"},
        files=[("files", ("virus.exe", b"x", "application/octet-stream"))],
    )

    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"]


def test_stream_msg_saves_uploaded_files_and_passes_filenames(monkeypatch, client):
    monkeypatch.setattr(
        chat_routes, "get_chat", AsyncMock(return_value=MagicMock(id=1, mode="agent"))
    )
    monkeypatch.setattr(chat_routes, "validate_uploads", lambda files: None)
    monkeypatch.setattr(chat_routes, "save_uploads", lambda chat_id, files: ["main.py"])

    captured = {}

    async def fake_stream(chat_id, msg, attached_filenames=None):
        captured["attached_filenames"] = attached_filenames
        yield 'event: done\ndata: {"id": 1}\n\n'

    monkeypatch.setattr(chat_routes, "stream_chat_msg", fake_stream)

    response = client.post(
        "/chat/msg/stream",
        data={"chat_id": 1, "msg": "hi"},
        files=[("files", ("main.py", b"print(1)", "text/plain"))],
    )

    assert response.status_code == 200
    assert captured["attached_filenames"] == ["main.py"]


def test_stream_msg_ignores_empty_file_part(monkeypatch, client):
    monkeypatch.setattr(
        chat_routes, "get_chat", AsyncMock(return_value=MagicMock(id=1, mode="agent"))
    )

    validate_calls = []
    monkeypatch.setattr(
        chat_routes, "validate_uploads", lambda files: validate_calls.append(files)
    )

    async def fake_stream(chat_id, msg, attached_filenames=None):
        yield 'event: done\ndata: {"id": 1}\n\n'

    monkeypatch.setattr(chat_routes, "stream_chat_msg", fake_stream)

    response = client.post(
        "/chat/msg/stream",
        data={"chat_id": 1, "msg": "hi"},
        files=[("files", ("", b"", "application/octet-stream"))],
    )

    assert response.status_code == 200
    assert validate_calls == [[]]


def test_retry_msg_chat_not_found(monkeypatch, client):
    monkeypatch.setattr(chat_routes, "get_chat", AsyncMock(return_value=None))

    response = client.post("/chat/msg/retry", json={"chat_id": 999})

    assert response.status_code == 404


def test_retry_msg_db_error_on_lookup(monkeypatch, client):
    monkeypatch.setattr(chat_routes, "get_chat", _db_error())

    response = client.post("/chat/msg/retry", json={"chat_id": 1})

    assert response.status_code == 500


def test_retry_msg_success_returns_sse_stream(monkeypatch, client):
    monkeypatch.setattr(
        chat_routes, "get_chat", AsyncMock(return_value=MagicMock(id=1, mode="agent"))
    )

    async def fake_retry(chat_id):
        yield 'event: done\ndata: {"id": 2}\n\n'

    monkeypatch.setattr(chat_routes, "stream_chat_retry", fake_retry)

    response = client.post("/chat/msg/retry", json={"chat_id": 1})

    assert response.status_code == 200
    assert "event: done" in response.text


def test_delete_chat_success(monkeypatch, client):
    monkeypatch.setattr(chat_routes, "delete_chat", AsyncMock(return_value=True))
    cleaned: list[int] = []
    monkeypatch.setattr(chat_routes, "delete_chat_sandbox", cleaned.append)

    response = client.delete("/chat/1")

    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
    assert cleaned == [1]


def test_delete_chat_not_found(monkeypatch, client):
    monkeypatch.setattr(chat_routes, "delete_chat", AsyncMock(return_value=False))
    cleaned: list[int] = []
    monkeypatch.setattr(chat_routes, "delete_chat_sandbox", cleaned.append)

    response = client.delete("/chat/999")

    assert response.status_code == 404
    assert cleaned == []


def test_delete_chat_db_error(monkeypatch, client):
    monkeypatch.setattr(chat_routes, "delete_chat", _db_error())

    response = client.delete("/chat/1")

    assert response.status_code == 500


def test_stream_msg_rejects_files_for_chat_mode(monkeypatch, client):
    monkeypatch.setattr(
        chat_routes, "get_chat", AsyncMock(return_value=MagicMock(id=1, mode="chat"))
    )

    response = client.post(
        "/chat/msg/stream",
        data={"chat_id": 1, "msg": "hi"},
        files=[("files", ("main.py", b"print(1)", "text/plain"))],
    )

    assert response.status_code == 400
    assert "agent mode" in response.json()["detail"]
