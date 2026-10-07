import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from lad.helpers import agent as agent_module
from lad.schemas.llm import LLMTurn, ToolCall, ToolDefinition


@pytest.fixture
def mock_session():
    session = AsyncMock()
    counter = {"value": 0}

    def _add(message):
        counter["value"] += 1
        message.id = counter["value"]
        message.created_at = datetime.now(UTC)

    session.add = MagicMock(side_effect=_add)
    return session


def _parse_sse(raw: str) -> tuple[str, dict]:
    lines = raw.split("\n")
    return lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))


async def _events(generator) -> list[tuple[str, dict]]:
    return [_parse_sse(raw) async for raw in generator]


def _list_tools(monkeypatch, tools):
    monkeypatch.setattr(
        agent_module.mcp_client, "list_tools", AsyncMock(return_value=tools)
    )


def test_message_to_turn_converts_plain_user_and_assistant_messages(message_factory):
    user_message = message_factory(1, role="user", content="hi there")
    assistant_message = message_factory(2, role="assistant", content="hello")

    assert agent_module._message_to_turn(user_message) == {
        "role": "user",
        "content": "hi there",
    }
    assert agent_module._message_to_turn(assistant_message) == {
        "role": "assistant",
        "content": "hello",
    }


def test_message_to_turn_appends_attached_filenames_to_content(message_factory):
    user_message = message_factory(
        1,
        role="user",
        content="analyze this",
        attached_files=json.dumps(["data.csv", "notes.txt"]),
    )

    result = agent_module._message_to_turn(user_message)

    assert result["role"] == "user"
    assert result["content"] == (
        "analyze this\n\n[Attached files available in the sandbox: data.csv, notes.txt]"
    )


def test_message_to_turn_ignores_null_attached_files(message_factory):
    user_message = message_factory(
        1, role="user", content="hi there", attached_files=None
    )

    assert agent_module._message_to_turn(user_message) == {
        "role": "user",
        "content": "hi there",
    }


def test_message_to_turn_reconstructs_tool_call_message(message_factory):
    tool_call_message = message_factory(
        3,
        role="tool_call",
        content="",
        tool_call_id="call_0",
        tool_name="run_command",
        tool_arguments='{"command": "ls"}',
    )

    result = agent_module._message_to_turn(tool_call_message)

    assert result == {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"function": {"name": "run_command", "arguments": {"command": "ls"}}}
        ],
    }


def test_message_to_turn_handles_missing_tool_arguments(message_factory):
    tool_call_message = message_factory(
        3,
        role="tool_call",
        content="",
        tool_call_id="call_0",
        tool_name="run_command",
        tool_arguments=None,
    )

    result = agent_module._message_to_turn(tool_call_message)

    assert result["tool_calls"][0]["function"]["arguments"] == {}


def test_message_to_turn_reconstructs_tool_result_message(message_factory):
    tool_result_message = message_factory(
        4,
        role="tool_result",
        content="file.txt",
        tool_call_id="call_0",
        tool_name="run_command",
    )

    result = agent_module._message_to_turn(tool_result_message)

    assert result == {
        "role": "tool",
        "tool_name": "run_command",
        "content": "file.txt",
    }


async def test_run_agent_turn_builds_history_as_separate_turns_not_flattened_text(
    monkeypatch, mock_session, message_factory
):
    _list_tools(monkeypatch, [])

    captured_messages = []

    async def fake_generate_turn(*, messages, tools, model=None):
        captured_messages.append(messages)
        return LLMTurn(content="second answer", tool_calls=[])

    monkeypatch.setattr(agent_module, "generate_turn", fake_generate_turn)

    history = [
        message_factory(1, role="user", content="first question"),
        message_factory(
            2,
            role="tool_call",
            content="",
            tool_call_id="call_0",
            tool_name="web_search",
            tool_arguments='{"query": "first question"}',
        ),
        message_factory(
            3,
            role="tool_result",
            content="some retrieved content",
            tool_call_id="call_0",
            tool_name="web_search",
        ),
        message_factory(4, role="assistant", content="first answer"),
        message_factory(5, role="user", content="second question"),
    ]

    await _events(
        agent_module.run_agent_turn(
            mock_session, chat_id=1, summary=None, history=history
        )
    )

    conversation = captured_messages[0]

    assert conversation[0] == {
        "role": "system",
        "content": agent_module.AGENT_SYSTEM_PROMPT,
    }
    assert conversation[1] == {"role": "user", "content": "first question"}
    assert conversation[2]["role"] == "assistant"
    assert conversation[2]["tool_calls"][0]["function"]["name"] == "web_search"
    assert conversation[3] == {
        "role": "tool",
        "tool_name": "web_search",
        "content": "some retrieved content",
    }
    assert conversation[4] == {"role": "assistant", "content": "first answer"}
    assert conversation[5] == {"role": "user", "content": "second question"}

    assert not any(
        isinstance(turn.get("content"), str) and "TOOL_CALL" in turn["content"]
        for turn in conversation
    )


async def test_run_agent_turn_includes_summary_as_its_own_system_turn(
    monkeypatch, mock_session
):
    _list_tools(monkeypatch, [])

    captured_messages = []

    async def fake_generate_turn(*, messages, tools, model=None):
        captured_messages.append(messages)
        return LLMTurn(content="ok", tool_calls=[])

    monkeypatch.setattr(agent_module, "generate_turn", fake_generate_turn)

    await _events(
        agent_module.run_agent_turn(
            mock_session, chat_id=1, summary="earlier context here", history=[]
        )
    )

    conversation = captured_messages[0]

    assert conversation[0]["role"] == "system"
    assert conversation[1]["role"] == "system"
    assert "earlier context here" in conversation[1]["content"]


async def test_run_agent_turn_streams_final_answer_when_no_tools_available(
    monkeypatch, mock_session
):
    _list_tools(monkeypatch, [])
    monkeypatch.setattr(
        agent_module,
        "generate_turn",
        AsyncMock(return_value=LLMTurn(content="Hello there", tool_calls=[])),
    )

    events = await _events(
        agent_module.run_agent_turn(mock_session, chat_id=1, summary=None, history=[])
    )

    chunk_events = [data["text"] for event, data in events if event == "chunk"]
    assert "".join(chunk_events) == "Hello there"

    assert events[-1][0] == "done"
    assert events[-1][1]["content"] == "Hello there"
    assert events[-1][1]["role"] == "assistant"


async def test_run_agent_turn_executes_a_tool_call_and_continues(
    monkeypatch, mock_session
):
    tool = ToolDefinition(name="run_command", description="", parameters={})
    _list_tools(monkeypatch, [tool])

    captured_conversations = []

    async def fake_generate_turn(*, messages, tools, model=None):
        captured_conversations.append([dict(m) for m in messages])
        if len(captured_conversations) == 1:
            return LLMTurn(
                content="",
                tool_calls=[
                    ToolCall(
                        call_id="call_0",
                        name="run_command",
                        arguments={"command": "ls"},
                    )
                ],
            )
        return LLMTurn(content="There is one file.", tool_calls=[])

    monkeypatch.setattr(agent_module, "generate_turn", fake_generate_turn)

    call_tool_calls = []

    async def fake_call_tool(name, arguments, extra_env=None):
        call_tool_calls.append((name, arguments, extra_env))
        return "file.txt"

    monkeypatch.setattr(agent_module.mcp_client, "call_tool", fake_call_tool)

    events = await _events(
        agent_module.run_agent_turn(mock_session, chat_id=42, summary=None, history=[])
    )

    assert [event for event, _ in events] == [
        "tool_call",
        "tool_result",
        "chunk",
        "done",
    ]

    assert len(call_tool_calls) == 1
    _, _, used_extra_env = call_tool_calls[0]
    assert used_extra_env == {"LAD_CHAT_ID": "42"}

    tool_call_payload = events[0][1]
    assert tool_call_payload["tool_name"] == "run_command"
    assert json.loads(tool_call_payload["tool_arguments"]) == {"command": "ls"}

    assert events[1][1]["content"] == "file.txt"

    second_call_messages = captured_conversations[1]
    assert second_call_messages[-2]["role"] == "assistant"
    assert second_call_messages[-1] == {
        "role": "tool",
        "tool_name": "run_command",
        "content": "file.txt",
    }


async def test_run_agent_turn_reports_tool_failures_back_to_the_model(
    monkeypatch, mock_session
):
    tool = ToolDefinition(name="run_command", description="", parameters={})
    _list_tools(monkeypatch, [tool])

    call_count = {"value": 0}

    async def fake_generate_turn(*, messages, tools, model=None):
        call_count["value"] += 1
        if call_count["value"] == 1:
            return LLMTurn(
                content="",
                tool_calls=[
                    ToolCall(call_id="call_0", name="run_command", arguments={})
                ],
            )
        return LLMTurn(content="Sorry, that failed.", tool_calls=[])

    async def failing_call_tool(name, arguments, extra_env=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(agent_module, "generate_turn", fake_generate_turn)
    monkeypatch.setattr(agent_module.mcp_client, "call_tool", failing_call_tool)

    events = await _events(
        agent_module.run_agent_turn(mock_session, chat_id=1, summary=None, history=[])
    )

    tool_result_payload = next(data for event, data in events if event == "tool_result")
    assert "Error calling run_command" in tool_result_payload["content"]
    assert "boom" in tool_result_payload["content"]

    assert events[-1][0] == "done"


async def test_run_agent_turn_forces_a_final_answer_at_the_iteration_cap(
    monkeypatch, mock_session
):
    tool = ToolDefinition(name="run_command", description="", parameters={})
    _list_tools(monkeypatch, [tool])
    monkeypatch.setattr(agent_module.conf, "AGENT_MAX_TOOL_ITERATIONS", 2)

    call_tool_invocations = []

    async def fake_generate_turn(*, messages, tools, model=None):
        if tools is None:
            return LLMTurn(content="Final answer.", tool_calls=[])
        return LLMTurn(
            content="",
            tool_calls=[ToolCall(call_id="call_0", name="run_command", arguments={})],
        )

    async def fake_call_tool(name, arguments, extra_env=None):
        call_tool_invocations.append((name, arguments))
        return "ok"

    monkeypatch.setattr(agent_module, "generate_turn", fake_generate_turn)
    monkeypatch.setattr(agent_module.mcp_client, "call_tool", fake_call_tool)

    events = await _events(
        agent_module.run_agent_turn(mock_session, chat_id=1, summary=None, history=[])
    )

    assert len(call_tool_invocations) == 1
    assert events[-1][0] == "done"
    assert events[-1][1]["content"] == "Final answer."


async def test_run_agent_turn_ignores_tool_calls_on_the_final_iteration(
    monkeypatch, mock_session
):
    tool = ToolDefinition(name="run_command", description="", parameters={})
    _list_tools(monkeypatch, [tool])
    monkeypatch.setattr(agent_module.conf, "AGENT_MAX_TOOL_ITERATIONS", 1)

    monkeypatch.setattr(
        agent_module,
        "generate_turn",
        AsyncMock(
            return_value=LLMTurn(
                content="Best effort answer.",
                tool_calls=[
                    ToolCall(call_id="call_0", name="run_command", arguments={})
                ],
            )
        ),
    )
    monkeypatch.setattr(
        agent_module.mcp_client,
        "call_tool",
        AsyncMock(side_effect=AssertionError("tool must not run on the last turn")),
    )

    events = await _events(
        agent_module.run_agent_turn(mock_session, chat_id=1, summary=None, history=[])
    )

    assert events[-1][0] == "done"
    assert events[-1][1]["content"] == "Best effort answer."


async def test_run_agent_turn_raises_on_empty_final_content(monkeypatch, mock_session):
    _list_tools(monkeypatch, [])
    monkeypatch.setattr(
        agent_module,
        "generate_turn",
        AsyncMock(return_value=LLMTurn(content="   ", tool_calls=[])),
    )

    with pytest.raises(RuntimeError, match="empty response"):
        await _events(
            agent_module.run_agent_turn(
                mock_session, chat_id=1, summary=None, history=[]
            )
        )


async def test_run_agent_turn_rejects_a_tool_call_outside_the_allowed_set(
    monkeypatch, mock_session
):
    tool = ToolDefinition(name="run_command", description="", parameters={})
    _list_tools(monkeypatch, [tool])

    call_count = {"value": 0}

    async def fake_generate_turn(*, messages, tools, model=None):
        call_count["value"] += 1
        if call_count["value"] == 1:
            return LLMTurn(
                content="",
                tool_calls=[
                    ToolCall(call_id="call_0", name="delete_everything", arguments={})
                ],
            )
        return LLMTurn(content="Can't do that.", tool_calls=[])

    call_tool = AsyncMock(return_value="should not be reached")

    monkeypatch.setattr(agent_module, "generate_turn", fake_generate_turn)
    monkeypatch.setattr(agent_module.mcp_client, "call_tool", call_tool)

    events = await _events(
        agent_module.run_agent_turn(mock_session, chat_id=1, summary=None, history=[])
    )

    call_tool.assert_not_awaited()
    tool_result_payload = next(data for event, data in events if event == "tool_result")
    assert "not available in this mode" in tool_result_payload["content"]
    assert events[-1][0] == "done"


async def test_run_chat_turn_uses_chat_system_prompt_and_model(
    monkeypatch, mock_session
):
    _list_tools(monkeypatch, [])
    monkeypatch.setattr(agent_module.conf, "OLLAMA_MODEL", "qwen3:8b")

    captured = {}

    async def fake_generate_turn(*, messages, tools, model=None):
        captured["messages"] = messages
        captured["model"] = model
        return LLMTurn(content="hi there", tool_calls=[])

    monkeypatch.setattr(agent_module, "generate_turn", fake_generate_turn)

    await _events(
        agent_module.run_chat_turn(mock_session, chat_id=1, summary=None, history=[])
    )

    assert captured["messages"][0] == {
        "role": "system",
        "content": agent_module.CHAT_SYSTEM_PROMPT,
    }
    assert captured["model"] == "qwen3:8b"


async def test_run_chat_turn_only_offers_chat_scoped_tools(monkeypatch, mock_session):
    list_tools = AsyncMock(return_value=[])
    monkeypatch.setattr(agent_module.mcp_client, "list_tools", list_tools)
    monkeypatch.setattr(
        agent_module,
        "generate_turn",
        AsyncMock(return_value=LLMTurn(content="ok", tool_calls=[])),
    )

    await _events(
        agent_module.run_chat_turn(mock_session, chat_id=1, summary=None, history=[])
    )

    list_tools.assert_awaited_once_with(allowed_tools={"web_search", "recall_memory"})


async def test_run_chat_turn_executes_an_allowed_tool_call(monkeypatch, mock_session):
    tool = ToolDefinition(name="web_search", description="", parameters={})
    _list_tools(monkeypatch, [tool])

    call_count = {"value": 0}

    async def fake_generate_turn(*, messages, tools, model=None):
        call_count["value"] += 1
        if call_count["value"] == 1:
            return LLMTurn(
                content="",
                tool_calls=[
                    ToolCall(
                        call_id="call_0", name="web_search", arguments={"query": "x"}
                    )
                ],
            )
        return LLMTurn(content="Here's what I found.", tool_calls=[])

    monkeypatch.setattr(agent_module, "generate_turn", fake_generate_turn)
    monkeypatch.setattr(
        agent_module.mcp_client, "call_tool", AsyncMock(return_value="search results")
    )

    events = await _events(
        agent_module.run_chat_turn(mock_session, chat_id=1, summary=None, history=[])
    )

    assert [event for event, _ in events] == [
        "tool_call",
        "tool_result",
        "chunk",
        "done",
    ]
    assert events[-1][1]["content"] == "Here's what I found."


async def test_chat_and_agent_turns_use_independent_iteration_caps(
    monkeypatch, mock_session
):
    tool = ToolDefinition(name="web_search", description="", parameters={})
    _list_tools(monkeypatch, [tool])
    monkeypatch.setattr(agent_module.conf, "MAX_TOOL_ITERATIONS", 1)
    monkeypatch.setattr(agent_module.conf, "AGENT_MAX_TOOL_ITERATIONS", 5)

    offered_tools = []

    async def fake_generate_turn(*, messages, tools, model=None):
        offered_tools.append(tools)
        return LLMTurn(content="final", tool_calls=[])

    monkeypatch.setattr(agent_module, "generate_turn", fake_generate_turn)

    await _events(
        agent_module.run_chat_turn(mock_session, chat_id=1, summary=None, history=[])
    )
    await _events(
        agent_module.run_agent_turn(mock_session, chat_id=1, summary=None, history=[])
    )

    assert offered_tools[0] is None
    assert offered_tools[1] == [tool]
