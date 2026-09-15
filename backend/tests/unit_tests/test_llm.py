import json
from unittest.mock import MagicMock

import pytest

from lad.core import llm as core_llm
from lad.helpers import llm as helpers_llm
from lad.schemas.llm import LLMTurn, ToolCall, ToolDefinition


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


def test_generate_content_uses_default_model_when_not_overridden(monkeypatch):
    mock_post = _mock_post_response(
        monkeypatch, json_body={"message": {"content": "ok"}}
    )

    core_llm.generate_content(contents="hi")

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["model"] == core_llm.conf.OLLAMA_MODEL
    assert kwargs["json"]["options"]["num_ctx"] == core_llm.conf.OLLAMA_NUM_CTX


def test_generate_content_uses_the_provided_model_override(monkeypatch):
    mock_post = _mock_post_response(
        monkeypatch, json_body={"message": {"content": "ok"}}
    )

    core_llm.generate_content(contents="hi", model="gemma4:12b")

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["model"] == "gemma4:12b"


def test_generate_turn_uses_the_provided_model_override(monkeypatch):
    mock_post = _mock_post_response(
        monkeypatch, json_body={"message": {"content": "ok"}}
    )

    core_llm.generate_turn(
        messages=[{"role": "user", "content": "hi"}], model="gemma4:12b"
    )

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["model"] == "gemma4:12b"
    assert kwargs["json"]["options"]["num_ctx"] == core_llm.conf.OLLAMA_NUM_CTX


def test_generate_turn_error_message_names_the_overridden_model(monkeypatch):
    mock_response = MagicMock()
    mock_response.status_code = 404
    _mock_post_response(monkeypatch, json_body={})
    monkeypatch.setattr(core_llm.httpx, "post", MagicMock(return_value=mock_response))

    with pytest.raises(RuntimeError, match="gemma4:12b"):
        core_llm.generate_turn(
            messages=[{"role": "user", "content": "hi"}], model="gemma4:12b"
        )


def test_stream_content_uses_the_provided_model_override(monkeypatch):
    mock_stream = _mock_stream_response(
        monkeypatch, lines=[json.dumps({"message": {"content": "ok"}, "done": True})]
    )

    list(core_llm.stream_content(contents="hi", model="gemma4:12b"))

    _, kwargs = mock_stream.call_args
    assert kwargs["json"]["model"] == "gemma4:12b"


def test_build_options_includes_num_ctx_when_given():
    options = core_llm._build_options(temperature=None, num_ctx=8192)

    assert options == {"num_ctx": 8192}


def test_build_options_omits_num_ctx_when_not_given():
    options = core_llm._build_options(temperature=0.5)

    assert options == {"temperature": 0.5}


def test_build_assistant_tool_call_message_wraps_calls_in_ollama_shape():
    turn = LLMTurn(
        content="",
        tool_calls=[
            ToolCall(
                call_id="call_0", name="get_temperature", arguments={"city": "NY"}
            ),
            ToolCall(call_id="call_1", name="get_time", arguments={}),
        ],
    )

    result = core_llm.build_assistant_tool_call_message(turn)

    assert result == {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"function": {"name": "get_temperature", "arguments": {"city": "NY"}}},
            {"function": {"name": "get_time", "arguments": {}}},
        ],
    }


def test_build_tool_result_message_matches_ollama_tool_role_shape():
    result = core_llm.build_tool_result_message("get_temperature", "22°C")

    assert result == {
        "role": "tool",
        "tool_name": "get_temperature",
        "content": "22°C",
    }


def test_raise_for_ollama_status_gives_a_clear_message_on_404(monkeypatch):
    mock_response = MagicMock()
    mock_response.status_code = 404

    with pytest.raises(RuntimeError, match="ollama pull embeddinggemma"):
        core_llm.raise_for_ollama_status(mock_response, "embeddinggemma")

    mock_response.raise_for_status.assert_not_called()


def test_raise_for_ollama_status_delegates_other_errors_to_raise_for_status():
    mock_response = MagicMock()
    mock_response.status_code = 500

    core_llm.raise_for_ollama_status(mock_response, "qwen3:8b")

    mock_response.raise_for_status.assert_called_once()


def test_raise_for_ollama_status_does_nothing_on_success():
    mock_response = MagicMock()
    mock_response.status_code = 200

    core_llm.raise_for_ollama_status(mock_response, "qwen3:8b")

    mock_response.raise_for_status.assert_called_once()


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


def test_format_message_renders_tool_call_and_tool_result_rows(message_factory):
    tool_call = message_factory(
        1,
        role="tool_call",
        content="",
        tool_name="get_temperature",
        tool_arguments='{"city": "New York"}',
    )
    tool_result = message_factory(
        2, role="tool_result", content="22°C", tool_name="get_temperature"
    )

    assert (
        helpers_llm._format_message(tool_call)
        == 'TOOL_CALL get_temperature({"city": "New York"})'
    )
    assert (
        helpers_llm._format_message(tool_result) == "TOOL_RESULT get_temperature: 22°C"
    )


def test_generate_summary_returns_existing_when_no_messages():
    result = helpers_llm.generate_summary(existing_summary="unchanged", messages=[])

    assert result == "unchanged"


def test_generate_summary_returns_empty_string_when_nothing_exists():
    result = helpers_llm.generate_summary(existing_summary=None, messages=[])

    assert result == ""


def test_generate_summary_calls_generate_content(monkeypatch, message_factory):
    captured = {}

    def fake_generate_content(
        *, contents, system_instruction=None, temperature=None, model=None
    ):
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
