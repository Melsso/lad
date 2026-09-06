import pytest

from lad.core import mcp as mcp_module


def test_flatten_exceptions_returns_a_plain_exception_as_is():
    exc = ValueError("boom")

    assert mcp_module._flatten_exceptions(exc) == [exc]


def test_flatten_exceptions_recursively_unwraps_nested_groups():
    inner = ValueError("boom")
    group = BaseExceptionGroup(
        "outer", [BaseExceptionGroup("inner", [inner]), RuntimeError("also boom")]
    )

    leaves = mcp_module._flatten_exceptions(group)

    assert inner in leaves
    assert any(isinstance(leaf, RuntimeError) for leaf in leaves)
    assert len(leaves) == 2


def test_describe_exception_includes_the_real_underlying_message():
    group = BaseExceptionGroup(
        "unhandled errors in a TaskGroup", [ValueError("model not found")]
    )

    description = mcp_module._describe_exception(group)

    assert "model not found" in description
    assert "ValueError" in description


def test_call_tool_unwraps_exception_group_into_a_readable_runtime_error(
    monkeypatch,
):
    client = mcp_module.MCPClient(servers=[])
    client._tool_owners["search_docs"] = mcp_module.MCPServerConfig(
        name="rag", command="python", args=[]
    )

    def fake_run(coro):
        coro.close()
        raise BaseExceptionGroup(
            "unhandled errors in a TaskGroup", [ValueError("404 model not found")]
        )

    monkeypatch.setattr(mcp_module.asyncio, "run", fake_run)

    with pytest.raises(RuntimeError, match="404 model not found"):
        client.call_tool("search_docs", {})


def test_list_tools_unwraps_exception_group_into_a_readable_runtime_error(
    monkeypatch,
):
    client = mcp_module.MCPClient(
        servers=[mcp_module.MCPServerConfig(name="rag", command="python", args=[])]
    )

    def fake_run(coro):
        coro.close()
        raise BaseExceptionGroup(
            "unhandled errors in a TaskGroup", [ConnectionError("closed")]
        )

    monkeypatch.setattr(mcp_module.asyncio, "run", fake_run)

    with pytest.raises(RuntimeError, match="closed"):
        client.list_tools()


def test_load_server_configs_returns_empty_list_for_blank_string():
    assert mcp_module.load_server_configs("") == []
    assert mcp_module.load_server_configs("   ") == []


def test_load_server_configs_returns_empty_list_for_empty_json_array():
    assert mcp_module.load_server_configs("[]") == []


def test_load_server_configs_parses_server_entries():
    raw = (
        '[{"name": "rag", "command": "python", "args": ["-m", "lad.tools.rag"]}, '
        '{"name": "echo", "command": "node", "args": []}]'
    )

    configs = mcp_module.load_server_configs(raw)

    assert configs == [
        mcp_module.MCPServerConfig(
            name="rag", command="python", args=["-m", "lad.tools.rag"]
        ),
        mcp_module.MCPServerConfig(name="echo", command="node", args=[]),
    ]


def test_load_server_configs_defaults_missing_args_to_empty_list():
    configs = mcp_module.load_server_configs('[{"name": "rag", "command": "python"}]')

    assert configs[0].args == []


def test_list_tools_returns_empty_without_spawning_anything_when_unconfigured(
    monkeypatch,
):
    client = mcp_module.MCPClient(servers=[])

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("asyncio.run should not be called with no servers")

    monkeypatch.setattr(mcp_module.asyncio, "run", _fail_if_called)

    assert client.list_tools() == []


def test_call_tool_raises_for_a_name_with_no_owning_server():
    client = mcp_module.MCPClient(servers=[])

    with pytest.raises(ValueError, match="Unknown MCP tool"):
        client.call_tool("nonexistent", {})
