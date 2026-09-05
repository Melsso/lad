import json

from lad.helpers import messages as messages_module


def test_create_message_defaults_tool_fields_to_none(mock_session):
    result = messages_module.create_message(
        mock_session, chat_id=1, role="user", content="hi"
    )

    assert result.tool_call_id is None
    assert result.tool_name is None
    assert result.tool_arguments is None
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()


def test_create_tool_call_message_persists_call_metadata(mock_session):
    result = messages_module.create_tool_call_message(
        mock_session,
        chat_id=1,
        call_id="call_0",
        tool_name="get_temperature",
        arguments={"city": "New York"},
    )

    assert result.role == "tool_call"
    assert result.content == ""
    assert result.tool_call_id == "call_0"
    assert result.tool_name == "get_temperature"
    assert result.tool_arguments is not None
    assert json.loads(result.tool_arguments) == {"city": "New York"}
    mock_session.add.assert_called_once()


def test_create_tool_result_message_persists_result_content(mock_session):
    result = messages_module.create_tool_result_message(
        mock_session,
        chat_id=1,
        call_id="call_0",
        tool_name="get_temperature",
        content="22°C",
    )

    assert result.role == "tool_result"
    assert result.content == "22°C"
    assert result.tool_call_id == "call_0"
    assert result.tool_name == "get_temperature"
    assert result.tool_arguments is None


def test_sse_event_for_message_serializes_persisted_row(message_factory):
    message = message_factory(1, role="assistant", content="hello")

    result = messages_module.sse_event_for_message("done", message)

    assert result.startswith("event: done\n")
    data_line = result.split("\n")[1]
    payload = json.loads(data_line[len("data: ") :])
    assert payload["id"] == 1
    assert payload["role"] == "assistant"
    assert payload["content"] == "hello"
