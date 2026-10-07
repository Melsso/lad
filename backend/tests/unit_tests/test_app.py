from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from lad.core import app as app_module
from lad.core.db import get_db
from lad.routes import app as app_routes


def _client(monkeypatch, *, hosts, resolved):
    monkeypatch.setattr(app_module.conf, "ALLOWED_CLIENT_HOSTS", hosts)

    async def fake_resolve(host):
        return resolved

    monkeypatch.setattr(app_module, "_resolve", fake_resolve)
    monkeypatch.setattr(app_routes, "get_chats", AsyncMock(return_value=[]))

    app = app_module.create_app()
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    return TestClient(app)


def test_rejects_clients_that_are_not_allowed(monkeypatch):
    client = _client(monkeypatch, hosts="lad-nginx", resolved={"10.0.0.2"})

    assert client.get("/app/").status_code == 403


def test_accepts_allowed_clients(monkeypatch):
    client = _client(monkeypatch, hosts="lad-nginx", resolved={"testclient"})

    assert client.get("/app/").status_code == 200


def test_no_restriction_when_unset(monkeypatch):
    client = _client(monkeypatch, hosts="", resolved=set())

    assert client.get("/app/").status_code == 200
