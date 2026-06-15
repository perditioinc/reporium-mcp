"""Tool-contract tests.

These tests guard against advertised-vs-registered drift: the MCP server
advertises a set of tools via list_tools(), and dispatches them via call_tool().
If a tool is added to list_tools() but not wired into call_tool() (or vice
versa), or if a tool's input schema becomes malformed, these tests fail.

No network calls: the underlying tool implementations are patched to return a
sentinel so dispatch can be exercised without a live Reporium API.
"""
import inspect

import pytest

import mcp_server


# The canonical set of tools this server is documented to expose. Keeping the
# expected set explicit (rather than deriving it from the code under test)
# means an accidental add/remove is caught instead of silently accepted.
EXPECTED_TOOL_NAMES = {
    "search_repos",
    "search_repos_semantic",
    "get_repo",
    "find_similar_repos",
    "list_taxonomy_dimensions",
    "list_taxonomy_values",
    "get_repos_by_taxonomy",
    "ask_portfolio",
    "get_portfolio_gaps",
    "get_ai_trends",
    "get_portfolio_insights",
    "get_cross_dimension_stats",
    "get_repo_quality",
    "get_quality_signals",
    "list_taxonomy_gaps",
    "list_categories",
    "get_repos_by_category",
    "get_knowledge_graph",
}


async def _advertised_tools():
    return await mcp_server.list_tools()


@pytest.mark.asyncio
async def test_exactly_eighteen_tools_advertised():
    tools = await _advertised_tools()
    assert len(tools) == 18


@pytest.mark.asyncio
async def test_advertised_names_match_canonical_set():
    tools = await _advertised_tools()
    names = {t.name for t in tools}
    assert names == EXPECTED_TOOL_NAMES


@pytest.mark.asyncio
async def test_tool_names_are_unique():
    tools = await _advertised_tools()
    names = [t.name for t in tools]
    assert len(names) == len(set(names)), "duplicate tool name advertised"


@pytest.mark.asyncio
async def test_every_tool_has_nonempty_description():
    tools = await _advertised_tools()
    for t in tools:
        assert isinstance(t.description, str) and t.description.strip(), (
            f"tool {t.name!r} has an empty description"
        )


@pytest.mark.asyncio
async def test_every_tool_exposes_a_valid_object_input_schema():
    tools = await _advertised_tools()
    for t in tools:
        schema = t.inputSchema
        assert isinstance(schema, dict), f"{t.name}: inputSchema must be a dict"
        # MCP tool input schemas are JSON Schema objects.
        assert schema.get("type") == "object", (
            f"{t.name}: inputSchema.type must be 'object'"
        )
        props = schema.get("properties", {})
        assert isinstance(props, dict), f"{t.name}: properties must be a dict"
        required = schema.get("required", [])
        assert isinstance(required, list), f"{t.name}: required must be a list"
        # Every required field must be declared in properties.
        for field in required:
            assert field in props, (
                f"{t.name}: required field {field!r} is not in properties"
            )


@pytest.mark.asyncio
async def test_enum_constrained_fields_have_nonempty_enums():
    # Several tools constrain inputs with an enum (e.g. dimension, category,
    # min_severity, edge_type). A drifted/empty enum would silently break input
    # validation, so assert any declared enum is a non-empty list.
    tools = await _advertised_tools()
    for t in tools:
        for field, spec in t.inputSchema.get("properties", {}).items():
            if "enum" in spec:
                assert isinstance(spec["enum"], list) and spec["enum"], (
                    f"{t.name}.{field}: enum must be a non-empty list"
                )


def test_dispatcher_handles_every_advertised_tool():
    # Guard advertised-vs-dispatched drift by parsing the call_tool dispatch
    # source: every advertised tool name must have a branch, and there must be
    # no leftover dispatch branch for a tool that is no longer advertised.
    src = inspect.getsource(mcp_server.call_tool)
    import re

    dispatched = set(re.findall(r'name == "([a-z_]+)"', src))
    assert dispatched == EXPECTED_TOOL_NAMES, (
        "call_tool dispatch branches drifted from advertised tools: "
        f"missing={EXPECTED_TOOL_NAMES - dispatched}, "
        f"extra={dispatched - EXPECTED_TOOL_NAMES}"
    )


@pytest.mark.asyncio
async def test_unknown_tool_returns_error(monkeypatch):
    # A name that is not advertised must hit the explicit 'Unknown tool' branch
    # rather than dispatching anything.
    monkeypatch.setattr(mcp_server, "REPORIUM_API_URL", "http://localhost")
    result = await mcp_server.call_tool("not_a_real_tool", {})
    assert len(result) == 1
    assert "Unknown tool: not_a_real_tool" in result[0].text


@pytest.mark.asyncio
async def test_call_tool_guards_missing_api_url(monkeypatch):
    # When REPORIUM_API_URL is unset, the server must refuse to call out and
    # return a configuration error instead of attempting a request.
    monkeypatch.setattr(mcp_server, "REPORIUM_API_URL", "")
    result = await mcp_server.call_tool("search_repos", {"query": "x"})
    assert len(result) == 1
    assert "REPORIUM_API_URL" in result[0].text
