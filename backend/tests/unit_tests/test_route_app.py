from sqlalchemy.exc import SQLAlchemyError

from lad.routes import app as app_routes


def test_list_chats_success(monkeypatch, client):
    fake_chats = [
        {"id": 1, "title": "First", "created_at": "2026-01-01T00:00:00+00:00"},
        {"id": 2, "title": "Second", "created_at": "2026-01-02T00:00:00+00:00"},
    ]
    monkeypatch.setattr(app_routes, "get_chats", lambda db: fake_chats)

    response = client.get("/app/")

    assert response.status_code == 200
    assert [c["title"] for c in response.json()] == ["First", "Second"]


def test_list_chats_db_error(monkeypatch, client):
    def raise_error(db):
        raise SQLAlchemyError("connection lost")

    monkeypatch.setattr(app_routes, "get_chats", raise_error)

    response = client.get("/app/")

    assert response.status_code == 500
