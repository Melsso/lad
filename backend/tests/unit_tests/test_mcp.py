import pytest

from lad.core import mcp as mcp_module


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
