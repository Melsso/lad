import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from lad.core import llm as core_llm
from lad.helpers import llm as helpers_llm
from lad.schemas.llm import LLMTurn, ToolCall, ToolDefinition


def _mock_post_response(monkeypatch, *, json_body):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = json_body

    mock_post = AsyncMock(return_value=mock_response)
    monkeypatch.setattr(core_llm.httpx.AsyncClient, "post", mock_post)

    return mock_post


async def test_generate_content_uses_default_model_when_not_overridden(monkeypatch):
    mock_post = _mock_post_response(
        monkeypatch, json_body={"message": {"content": "ok"}}
    )

    await core_llm.generate_content(contents="hi")

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["model"] == core_llm.conf.OLLAMA_MODEL
    assert kwargs["json"]["options"]["num_ctx"] == core_llm.conf.OLLAMA_NUM_CTX


async def test_generate_content_uses_the_provided_model_override(monkeypatch):
    mock_post = _mock_post_response(
        monkeypatch, json_body={"message": {"content": "ok"}}
    )

    await core_llm.generate_content(contents="hi", model="gemma4:12b")

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["model"] == "gemma4:12b"


async def test_generate_turn_uses_the_provided_model_override(monkeypatch):
    mock_post = _mock_post_response(
        monkeypatch, json_body={"message": {"content": "ok"}}
    )

    await core_llm.generate_turn(
        messages=[{"role": "user", "content": "hi"}], model="gemma4:12b"
    )

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["model"] == "gemma4:12b"
    assert kwargs["json"]["options"]["num_ctx"] == core_llm.conf.OLLAMA_NUM_CTX


async def test_generate_turn_error_message_names_the_overridden_model(monkeypatch):
    mock_response = MagicMock()
    mock_response.status_code = 404
    monkeypatch.setattr(
        core_llm.httpx.AsyncClient, "post", AsyncMock(return_value=mock_response)
    )

    with pytest.raises(RuntimeError, match="gemma4:12b"):
        await core_llm.generate_turn(
            messages=[{"role": "user", "content": "hi"}], model="gemma4:12b"
        )


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
            ToolCall(call_id="call_0", name="run_command", arguments={"command": "ls"}),
            ToolCall(call_id="call_1", name="web_search", arguments={}),
        ],
    )

    result = core_llm.build_assistant_tool_call_message(turn)

    assert result == {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"function": {"name": "run_command", "arguments": {"command": "ls"}}},
            {"function": {"name": "web_search", "arguments": {}}},
        ],
    }


def test_build_tool_result_message_matches_ollama_tool_role_shape():
    result = core_llm.build_tool_result_message("run_command", "file.txt")

    assert result == {
        "role": "tool",
        "tool_name": "run_command",
        "content": "file.txt",
    }


def test_raise_for_ollama_status_gives_a_clear_message_on_404():
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


def test_raise_for_ollama_status_calls_raise_for_status_on_success():
    mock_response = MagicMock()
    mock_response.status_code = 200

    core_llm.raise_for_ollama_status(mock_response, "qwen3:8b")

    mock_response.raise_for_status.assert_called_once()


async def test_generate_content_returns_stripped_text(monkeypatch):
    _mock_post_response(
        monkeypatch, json_body={"message": {"content": "  hello world  "}}
    )

    assert await core_llm.generate_content(contents="hi") == "hello world"


async def test_generate_content_raises_on_empty_response(monkeypatch):
    _mock_post_response(monkeypatch, json_body={"message": {"content": ""}})

    with pytest.raises(RuntimeError):
        await core_llm.generate_content(contents="hi")


async def test_generate_content_passes_system_instruction_and_temperature(
    monkeypatch,
):
    mock_post = _mock_post_response(
        monkeypatch, json_body={"message": {"content": "ok"}}
    )

    await core_llm.generate_content(
        contents="hi", system_instruction="be nice", temperature=0.5
    )

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["messages"] == [
        {"role": "system", "content": "be nice"},
        {"role": "user", "content": "hi"},
    ]
    assert kwargs["json"]["options"]["temperature"] == 0.5


async def test_generate_turn_returns_plain_text_with_no_tool_calls(monkeypatch):
    _mock_post_response(monkeypatch, json_body={"message": {"content": "  hi there  "}})

    turn = await core_llm.generate_turn(messages=[{"role": "user", "content": "hi"}])

    assert turn.content == "hi there"
    assert turn.tool_calls == []


async def test_generate_turn_does_not_send_tools_key_when_no_tools_given(monkeypatch):
    mock_post = _mock_post_response(
        monkeypatch, json_body={"message": {"content": "ok"}}
    )

    await core_llm.generate_turn(messages=[{"role": "user", "content": "hi"}])

    _, kwargs = mock_post.call_args
    assert "tools" not in kwargs["json"]


async def test_generate_turn_sends_tools_in_openai_function_shape(monkeypatch):
    mock_post = _mock_post_response(
        monkeypatch, json_body={"message": {"content": "ok"}}
    )

    tool = ToolDefinition(
        name="web_search",
        description="Search the web",
        parameters={
            "type": "object",
            "required": ["query"],
            "properties": {"query": {"type": "string"}},
        },
    )

    await core_llm.generate_turn(
        messages=[{"role": "user", "content": "news?"}], tools=[tool]
    )

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web",
                "parameters": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {"query": {"type": "string"}},
                },
            },
        }
    ]


async def test_generate_turn_parses_tool_calls_with_dict_arguments(monkeypatch):
    _mock_post_response(
        monkeypatch,
        json_body={
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "web_search",
                            "arguments": {"query": "ollama"},
                        }
                    }
                ],
            }
        },
    )

    turn = await core_llm.generate_turn(
        messages=[{"role": "user", "content": "news?"}],
        tools=[ToolDefinition(name="web_search", description="", parameters={})],
    )

    assert turn.content == ""
    assert len(turn.tool_calls) == 1
    assert turn.tool_calls[0].call_id == "call_0"
    assert turn.tool_calls[0].name == "web_search"
    assert turn.tool_calls[0].arguments == {"query": "ollama"}


async def test_generate_turn_parses_tool_calls_with_stringified_arguments(
    monkeypatch,
):
    _mock_post_response(
        monkeypatch,
        json_body={
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "web_search",
                            "arguments": json.dumps({"query": "ollama"}),
                        }
                    }
                ],
            }
        },
    )

    turn = await core_llm.generate_turn(
        messages=[{"role": "user", "content": "news?"}],
        tools=[ToolDefinition(name="web_search", description="", parameters={})],
    )

    assert turn.tool_calls[0].arguments == {"query": "ollama"}


async def test_generate_turn_assigns_unique_call_ids_for_parallel_tool_calls(
    monkeypatch,
):
    _mock_post_response(
        monkeypatch,
        json_body={
            "message": {
                "content": "",
                "tool_calls": [
                    {"function": {"name": "web_search", "arguments": {}}},
                    {"function": {"name": "web_search", "arguments": {}}},
                ],
            }
        },
    )

    turn = await core_llm.generate_turn(
        messages=[{"role": "user", "content": "news?"}],
        tools=[ToolDefinition(name="web_search", description="", parameters={})],
    )

    assert [call.call_id for call in turn.tool_calls] == ["call_0", "call_1"]


def test_format_message_renders_tool_call_and_tool_result_rows(message_factory):
    tool_call = message_factory(
        1,
        role="tool_call",
        content="",
        tool_name="web_search",
        tool_arguments='{"query": "ollama"}',
    )
    tool_result = message_factory(
        2, role="tool_result", content="results", tool_name="web_search"
    )

    assert (
        helpers_llm._format_message(tool_call)
        == 'TOOL_CALL web_search({"query": "ollama"})'
    )
    assert helpers_llm._format_message(tool_result) == "TOOL_RESULT web_search: results"


async def test_generate_summary_returns_existing_when_no_messages():
    result = await helpers_llm.generate_summary(
        existing_summary="unchanged", messages=[]
    )

    assert result == "unchanged"


async def test_generate_summary_returns_empty_string_when_nothing_exists():
    result = await helpers_llm.generate_summary(existing_summary=None, messages=[])

    assert result == ""


async def test_generate_summary_calls_generate_content(monkeypatch, message_factory):
    captured = {}

    async def fake_generate_content(
        *, contents, system_instruction=None, temperature=None, model=None
    ):
        captured["contents"] = contents
        captured["system_instruction"] = system_instruction
        captured["temperature"] = temperature
        return "new summary"

    monkeypatch.setattr(helpers_llm, "generate_content", fake_generate_content)

    messages = [message_factory(1, role="user", content="remember this")]
    result = await helpers_llm.generate_summary(
        existing_summary="old summary", messages=messages
    )

    assert result == "new summary"
    assert "old summary" in captured["contents"]
    assert "remember this" in captured["contents"]
    assert captured["system_instruction"] == helpers_llm.SUMMARY_SYSTEM_PROMPT
    assert captured["temperature"] == 0.2
