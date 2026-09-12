from unittest.mock import MagicMock

import pytest

from lad.tools import sandbox_server


def test_run_command_raises_without_chat_context(monkeypatch):
    monkeypatch.delenv("LAD_CHAT_ID", raising=False)

    with pytest.raises(RuntimeError, match="No chat context"):
        sandbox_server.run_command("echo hi")


def test_run_command_posts_chat_id_command_and_timeout(monkeypatch):
    monkeypatch.setenv("LAD_CHAT_ID", "7")

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"exit_code": 0, "stdout": "hi\n", "stderr": ""}

    mock_post = MagicMock(return_value=mock_response)
    monkeypatch.setattr(sandbox_server.httpx, "post", mock_post)

    sandbox_server.run_command("echo hi", timeout=30)

    _, kwargs = mock_post.call_args
    assert kwargs["json"] == {"chat_id": "7", "command": "echo hi", "timeout": 30}


def test_run_command_uses_the_configured_sandbox_url(monkeypatch):
    monkeypatch.setenv("LAD_CHAT_ID", "1")
    monkeypatch.setattr(sandbox_server.conf, "SANDBOX_URL", "http://sandbox:9000")

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"exit_code": 0, "stdout": "", "stderr": ""}

    mock_post = MagicMock(return_value=mock_response)
    monkeypatch.setattr(sandbox_server.httpx, "post", mock_post)

    sandbox_server.run_command("echo hi")

    args, _ = mock_post.call_args
    assert args[0] == "http://sandbox:9000/execute"


def test_run_command_formats_the_result(monkeypatch):
    monkeypatch.setenv("LAD_CHAT_ID", "1")

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "exit_code": 1,
        "stdout": "partial output",
        "stderr": "it broke",
    }

    monkeypatch.setattr(
        sandbox_server.httpx, "post", MagicMock(return_value=mock_response)
    )

    result = sandbox_server.run_command("false")

    assert "exit_code: 1" in result
    assert "partial output" in result
    assert "it broke" in result
