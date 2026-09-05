import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from lad.helpers import agent as agent_module
from lad.schemas.llm import LLMTurn, ToolCall, ToolDefinition


@pytest.fixture
def mock_session():
    session = MagicMock()
    counter = {"value": 0}

    def _add(message):
        counter["value"] += 1
        message.id = counter["value"]
        message.created_at = datetime.now(UTC)

    session.add.side_effect = _add
    return session


def _parse_sse(raw: str) -> tuple[str, dict]:
    lines = raw.split("\n")
    return lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))


def test_run_agent_turn_streams_final_answer_when_no_tools_available(
    monkeypatch, mock_session
):
    monkeypatch.setattr(agent_module.mcp_client, "list_tools", list)
    monkeypatch.setattr(
        agent_module,
        "generate_turn",
        lambda *, messages, tools: LLMTurn(content="Hello there", tool_calls=[]),
    )

    events = [
        _parse_sse(raw)
        for raw in agent_module.run_agent_turn(
            mock_session, chat_id=1, summary=None, history=[]
        )
    ]

    chunk_events = [data["text"] for event, data in events if event == "chunk"]
    assert "".join(chunk_events) == "Hello there"

    assert events[-1][0] == "done"
    assert events[-1][1]["content"] == "Hello there"
    assert events[-1][1]["role"] == "assistant"


def test_run_agent_turn_executes_a_tool_call_and_continues(monkeypatch, mock_session):
    tool = ToolDefinition(name="get_temperature", description="", parameters={})
    monkeypatch.setattr(agent_module.mcp_client, "list_tools", lambda: [tool])

    captured_conversations = []

    def fake_generate_turn(*, messages, tools):
        captured_conversations.append([dict(m) for m in messages])
        if len(captured_conversations) == 1:
            return LLMTurn(
                content="",
                tool_calls=[
                    ToolCall(
                        call_id="call_0",
                        name="get_temperature",
                        arguments={"city": "New York"},
                    )
                ],
            )
        return LLMTurn(content="It's 22°C in New York.", tool_calls=[])

    monkeypatch.setattr(agent_module, "generate_turn", fake_generate_turn)
    monkeypatch.setattr(
        agent_module.mcp_client,
        "call_tool",
        lambda name, arguments: "22°C",
    )

    events = [
        _parse_sse(raw)
        for raw in agent_module.run_agent_turn(
            mock_session, chat_id=1, summary=None, history=[]
        )
    ]

    event_names = [event for event, _ in events]
    assert event_names == ["tool_call", "tool_result", "chunk", "done"]

    tool_call_payload = events[0][1]
    assert tool_call_payload["tool_name"] == "get_temperature"
    assert json.loads(tool_call_payload["tool_arguments"]) == {"city": "New York"}

    tool_result_payload = events[1][1]
    assert tool_result_payload["content"] == "22°C"

    second_call_messages = captured_conversations[1]
    assert second_call_messages[-2]["role"] == "assistant"
    assert second_call_messages[-1] == {
        "role": "tool",
        "tool_name": "get_temperature",
        "content": "22°C",
    }


def test_run_agent_turn_reports_tool_failures_back_to_the_model(
    monkeypatch, mock_session
):
    tool = ToolDefinition(name="get_temperature", description="", parameters={})
    monkeypatch.setattr(agent_module.mcp_client, "list_tools", lambda: [tool])

    call_count = {"value": 0}

    def fake_generate_turn(*, messages, tools):
        call_count["value"] += 1
        if call_count["value"] == 1:
            return LLMTurn(
                content="",
                tool_calls=[
                    ToolCall(call_id="call_0", name="get_temperature", arguments={})
                ],
            )
        return LLMTurn(content="Sorry, I couldn't check the weather.", tool_calls=[])

    def failing_call_tool(name, arguments):
        raise RuntimeError("boom")

    monkeypatch.setattr(agent_module, "generate_turn", fake_generate_turn)
    monkeypatch.setattr(agent_module.mcp_client, "call_tool", failing_call_tool)

    events = [
        _parse_sse(raw)
        for raw in agent_module.run_agent_turn(
            mock_session, chat_id=1, summary=None, history=[]
        )
    ]

    tool_result_payload = next(data for event, data in events if event == "tool_result")
    assert "Error calling get_temperature" in tool_result_payload["content"]
    assert "boom" in tool_result_payload["content"]

    assert events[-1][0] == "done"


def test_run_agent_turn_forces_a_final_answer_at_the_iteration_cap(
    monkeypatch, mock_session
):
    tool = ToolDefinition(name="get_temperature", description="", parameters={})
    monkeypatch.setattr(agent_module.mcp_client, "list_tools", lambda: [tool])
    monkeypatch.setattr(agent_module.conf, "MAX_TOOL_ITERATIONS", 2)

    call_tool_invocations = []

    def fake_generate_turn(*, messages, tools):
        if tools is None:
            return LLMTurn(content="Final answer.", tool_calls=[])
        return LLMTurn(
            content="",
            tool_calls=[
                ToolCall(call_id="call_0", name="get_temperature", arguments={})
            ],
        )

    def fake_call_tool(name, arguments):
        call_tool_invocations.append((name, arguments))
        return "22°C"

    monkeypatch.setattr(agent_module, "generate_turn", fake_generate_turn)
    monkeypatch.setattr(agent_module.mcp_client, "call_tool", fake_call_tool)

    events = [
        _parse_sse(raw)
        for raw in agent_module.run_agent_turn(
            mock_session, chat_id=1, summary=None, history=[]
        )
    ]

    assert len(call_tool_invocations) == 1
    assert events[-1][0] == "done"
    assert events[-1][1]["content"] == "Final answer."
