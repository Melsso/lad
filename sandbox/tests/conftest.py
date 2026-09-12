import pytest
from fastapi.testclient import TestClient

import sandbox.app as app_module
from sandbox import schemas


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(schemas, "CHAT_SANDBOXES_ROOT", tmp_path)
    return TestClient(app_module.app)
