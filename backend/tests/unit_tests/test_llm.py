import json
from unittest.mock import MagicMock

import pytest

from lad.core import llm as core_llm
from lad.helpers import llm as helpers_llm
from lad.schemas.llm import ToolDefinition


def _mock_post_response(monkeypatch, *, json_body):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = json_body

    mock_post = MagicMock(return_value=mock_response)
    monkeypatch.setattr(core_llm.httpx, "post", mock_post)

    return mock_post


def _mock_stream_response(monkeypatch, *, lines):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.iter_lines.return_value = iter(lines)

    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_response
    mock_context.__exit__.return_value = False

    mock_stream = MagicMock(return_value=mock_context)
    monkeypatch.setattr(core_llm.httpx, "stream", mock_stream)

    return mock_stream


def test_generate_content_returns_stripped_text(monkeypatch):
    _mock_post_response(
        monkeypatch, json_body={"message": {"content": "  hello world  "}}
    )

    result = core_llm.generate_content(contents="hi")

    assert result == "hello world"


def test_generate_content_raises_on_empty_response(monkeypatch):
    _mock_post_response(monkeypatch, json_body={"message": {"content": ""}})

    with pytest.raises(RuntimeError):
        core_llm.generate_content(contents="hi")


def test_generate_content_passes_system_instruction_and_temperature(monkeypatch):
    mock_post = _mock_post_response(
        monkeypatch, json_body={"message": {"content": "ok"}}
    )

    core_llm.generate_content(
        contents="hi", system_instruction="be nice", temperature=0.5
    )

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["messages"] == [
        {"role": "system", "content": "be nice"},
        {"role": "user", "content": "hi"},
    ]
    assert kwargs["json"]["options"]["temperature"] == 0.5


def test_stream_content_yields_chunk_text(monkeypatch):
    lines = [
        json.dumps({"message": {"content": "Hel"}, "done": False}),
        json.dumps({"message": {"content": "lo"}, "done": True}),
    ]
    _mock_stream_response(monkeypatch, lines=lines)

    result = list(core_llm.stream_content(contents="hi"))

    assert result == ["Hel", "lo"]


def test_stream_content_skips_empty_chunks(monkeypatch):
    lines = [
        json.dumps({"message": {"content": ""}, "done": False}),
        json.dumps({"message": {}, "done": False}),
        json.dumps({"message": {"content": "ok"}, "done": True}),
    ]
    _mock_stream_response(monkeypatch, lines=lines)

    result = list(core_llm.stream_content(contents="hi"))

    assert result == ["ok"]


def test_generate_turn_returns_plain_text_with_no_tool_calls(monkeypatch):
    _mock_post_response(monkeypatch, json_body={"message": {"content": "  hi there  "}})

    turn = core_llm.generate_turn(messages=[{"role": "user", "content": "hi"}])

    assert turn.content == "hi there"
    assert turn.tool_calls == []


def test_generate_turn_does_not_send_tools_key_when_no_tools_given(monkeypatch):
    mock_post = _mock_post_response(
        monkeypatch, json_body={"message": {"content": "ok"}}
    )

    core_llm.generate_turn(messages=[{"role": "user", "content": "hi"}])

    _, kwargs = mock_post.call_args
    assert "tools" not in kwargs["json"]


def test_generate_turn_sends_tools_in_openai_function_shape(monkeypatch):
    mock_post = _mock_post_response(
        monkeypatch, json_body={"message": {"content": "ok"}}
    )

    tool = ToolDefinition(
        name="get_temperature",
        description="Get the current temperature for a city",
        parameters={
            "type": "object",
            "required": ["city"],
            "properties": {"city": {"type": "string"}},
        },
    )

    core_llm.generate_turn(
        messages=[{"role": "user", "content": "weather in NY?"}], tools=[tool]
    )

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "get_temperature",
                "description": "Get the current temperature for a city",
                "parameters": {
                    "type": "object",
                    "required": ["city"],
                    "properties": {"city": {"type": "string"}},
                },
            },
        }
    ]


def test_generate_turn_parses_tool_calls_with_dict_arguments(monkeypatch):
    _mock_post_response(
        monkeypatch,
        json_body={
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_temperature",
                            "arguments": {"city": "New York"},
                        }
                    }
                ],
            }
        },
    )

    turn = core_llm.generate_turn(
        messages=[{"role": "user", "content": "weather in NY?"}],
        tools=[ToolDefinition(name="get_temperature", description="", parameters={})],
    )

    assert turn.content == ""
    assert len(turn.tool_calls) == 1
    assert turn.tool_calls[0].call_id == "call_0"
    assert turn.tool_calls[0].name == "get_temperature"
    assert turn.tool_calls[0].arguments == {"city": "New York"}


def test_generate_turn_parses_tool_calls_with_stringified_arguments(monkeypatch):
    _mock_post_response(
        monkeypatch,
        json_body={
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_temperature",
                            "arguments": json.dumps({"city": "New York"}),
                        }
                    }
                ],
            }
        },
    )

    turn = core_llm.generate_turn(
        messages=[{"role": "user", "content": "weather in NY?"}],
        tools=[ToolDefinition(name="get_temperature", description="", parameters={})],
    )

    assert turn.tool_calls[0].arguments == {"city": "New York"}


def test_generate_turn_assigns_unique_call_ids_for_parallel_tool_calls(monkeypatch):
    _mock_post_response(
        monkeypatch,
        json_body={
            "message": {
                "content": "",
                "tool_calls": [
                    {"function": {"name": "get_temperature", "arguments": {}}},
                    {"function": {"name": "get_temperature", "arguments": {}}},
                ],
            }
        },
    )

    turn = core_llm.generate_turn(
        messages=[{"role": "user", "content": "weather?"}],
        tools=[ToolDefinition(name="get_temperature", description="", parameters={})],
    )

    assert [call.call_id for call in turn.tool_calls] == ["call_0", "call_1"]

    def broken_lines():
        yield json.dumps({"message": {"content": "partial"}, "done": False})
        raise RuntimeError("503 UNAVAILABLE")

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.iter_lines.return_value = broken_lines()

    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_response
    mock_context.__exit__.return_value = False

    monkeypatch.setattr(core_llm.httpx, "stream", MagicMock(return_value=mock_context))

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
