from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from lad.core import llm as core_llm
from lad.helpers import llm as helpers_llm


def test_generate_content_returns_stripped_text(monkeypatch):
    mock_response = SimpleNamespace(text="  hello world  ")
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    monkeypatch.setattr(core_llm, "client", mock_client)

    result = core_llm.generate_content(contents="hi")

    assert result == "hello world"


def test_generate_content_raises_on_empty_response(monkeypatch):
    mock_response = SimpleNamespace(text="")
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    monkeypatch.setattr(core_llm, "client", mock_client)

    with pytest.raises(RuntimeError):
        core_llm.generate_content(contents="hi")


def test_generate_content_passes_system_instruction_and_temperature(monkeypatch):
    mock_response = SimpleNamespace(text="ok")
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    monkeypatch.setattr(core_llm, "client", mock_client)

    core_llm.generate_content(
        contents="hi", system_instruction="be nice", temperature=0.5
    )

    _, kwargs = mock_client.models.generate_content.call_args
    assert kwargs["config"].system_instruction == "be nice"
    assert kwargs["config"].temperature == 0.5


def test_stream_content_yields_chunk_text(monkeypatch):
    chunks = [SimpleNamespace(text="Hel"), SimpleNamespace(text="lo")]
    mock_client = MagicMock()
    mock_client.models.generate_content_stream.return_value = iter(chunks)
    monkeypatch.setattr(core_llm, "client", mock_client)

    result = list(core_llm.stream_content(contents="hi"))

    assert result == ["Hel", "lo"]


def test_stream_content_skips_empty_chunks(monkeypatch):
    chunks = [
        SimpleNamespace(text=""),
        SimpleNamespace(text=None),
        SimpleNamespace(text="ok"),
    ]
    mock_client = MagicMock()
    mock_client.models.generate_content_stream.return_value = iter(chunks)
    monkeypatch.setattr(core_llm, "client", mock_client)

    result = list(core_llm.stream_content(contents="hi"))

    assert result == ["ok"]


def test_stream_content_propagates_upstream_errors(monkeypatch):
    def broken_stream():
        yield SimpleNamespace(text="partial")
        raise RuntimeError("503 UNAVAILABLE")

    mock_client = MagicMock()
    mock_client.models.generate_content_stream.return_value = broken_stream()
    monkeypatch.setattr(core_llm, "client", mock_client)

    generator = core_llm.stream_content(contents="hi")

    assert next(generator) == "partial"
    with pytest.raises(RuntimeError, match="503 UNAVAILABLE"):
        next(generator)


def test_build_llm_context_with_summary_and_messages(message_factory):
    messages = [
        message_factory(1, role="user", content="hi"),
        message_factory(2, role="assistant", content="hello"),
    ]

    context = helpers_llm.build_llm_context(summary="prior summary", messages=messages)

    assert "CONVERSATION SUMMARY:" in context
    assert "prior summary" in context
    assert "RECENT CONVERSATION:" in context
    assert "USER: hi" in context
    assert "ASSISTANT: hello" in context


def test_build_llm_context_without_summary(message_factory):
    messages = [message_factory(1, role="user", content="hi")]

    context = helpers_llm.build_llm_context(summary=None, messages=messages)

    assert "CONVERSATION SUMMARY:" not in context
    assert "USER: hi" in context


def test_build_llm_context_without_messages():
    context = helpers_llm.build_llm_context(summary="only a summary", messages=[])

    assert "CONVERSATION SUMMARY:" in context
    assert "RECENT CONVERSATION:" not in context


def test_generate_summary_returns_existing_when_no_messages():
    result = helpers_llm.generate_summary(existing_summary="unchanged", messages=[])

    assert result == "unchanged"


def test_generate_summary_returns_empty_string_when_nothing_exists():
    result = helpers_llm.generate_summary(existing_summary=None, messages=[])

    assert result == ""


def test_generate_summary_calls_generate_content(monkeypatch, message_factory):
    captured = {}

    def fake_generate_content(*, contents, system_instruction=None, temperature=None):
        captured["contents"] = contents
        captured["system_instruction"] = system_instruction
        captured["temperature"] = temperature
        return "new summary"

    monkeypatch.setattr(helpers_llm, "generate_content", fake_generate_content)

    messages = [message_factory(1, role="user", content="remember this")]
    result = helpers_llm.generate_summary(
        existing_summary="old summary", messages=messages
    )

    assert result == "new summary"
    assert "old summary" in captured["contents"]
    assert "remember this" in captured["contents"]
    assert captured["system_instruction"] == helpers_llm.SUMMARY_SYSTEM_PROMPT
    assert captured["temperature"] == 0.2


def test_generate_response_stream_yields_from_stream_content(
    monkeypatch, message_factory
):
    captured = {}

    def fake_stream_content(*, contents, system_instruction=None, temperature=None):
        captured["contents"] = contents
        captured["system_instruction"] = system_instruction
        yield "chunk-1"
        yield "chunk-2"

    monkeypatch.setattr(helpers_llm, "stream_content", fake_stream_content)

    messages = [message_factory(1, role="user", content="hi")]
    result = list(
        helpers_llm.generate_response_stream(summary="ctx", messages=messages)
    )

    assert result == ["chunk-1", "chunk-2"]
    assert "ctx" in captured["contents"]
    assert captured["system_instruction"] == helpers_llm.SYSTEM_PROMPT
