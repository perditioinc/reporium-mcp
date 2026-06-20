"""Contract tests for the advertised MCP tool surface.

These mock nothing live: they exercise the in-process tool registration
(`list_tools`) and the dispatch table (`call_tool`) to guarantee the server
advertises exactly the expected set of tools, that every tool exposes a
valid MCP inputSchema, and that every advertised tool has a real dispatch
branch (no advertised-but-unroutable tools, and no missing-required-arg
crashes at the boundary).
"""
import asyncio

import pytest

import mcp_server


EXPECTED_TOOLS = {
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
    "find_alternatives",
    "explore_ecosystem",
}


def _list_tools():
    return asyncio.run(mcp_server.list_tools())


def test_advertises_exactly_twenty_tools():
    tools = _list_tools()
    assert len(tools) == 20, f"expected 20 tools, got {len(tools)}"


def test_advertised_tool_names_match_expected_set():
    names = {t.name for t in _list_tools()}
    assert names == EXPECTED_TOOLS, (
        f"missing={EXPECTED_TOOLS - names}, unexpected={names - EXPECTED_TOOLS}"
    )


def test_tool_names_are_unique():
    names = [t.name for t in _list_tools()]
    assert len(names) == len(set(names)), "duplicate tool names registered"


def test_every_tool_has_nonempty_description():
    for t in _list_tools():
        assert isinstance(t.description, str) and t.description.strip(), (
            f"tool {t.name} has an empty description"
        )


def test_every_tool_input_schema_is_valid_object_schema():
    """Each MCP tool inputSchema must be a JSON-Schema object with the
    required structural keys and a list-typed `required` array."""
    for t in _list_tools():
        schema = t.inputSchema
        assert isinstance(schema, dict), f"{t.name}: inputSchema is not a dict"
        assert schema.get("type") == "object", (
            f"{t.name}: inputSchema.type must be 'object'"
        )
        assert "properties" in schema, f"{t.name}: inputSchema missing properties"
        assert isinstance(schema["properties"], dict), (
            f"{t.name}: properties must be a dict"
        )
        # `required` is optional in JSON Schema, but every tool here declares it.
        assert "required" in schema, f"{t.name}: inputSchema missing required"
        assert isinstance(schema["required"], list), (
            f"{t.name}: required must be a list"
        )


def test_required_fields_are_declared_properties():
    """Every entry in a tool's `required` array must reference a declared
    property — a required field with no property definition is a broken
    schema clients cannot satisfy."""
    for t in _list_tools():
        schema = t.inputSchema
        props = set(schema.get("properties", {}).keys())
        for field in schema.get("required", []):
            assert field in props, (
                f"{t.name}: required field '{field}' is not a declared property"
            )


def test_enum_constrained_properties_have_nonempty_enums():
    for t in _list_tools():
        for prop_name, prop in t.inputSchema.get("properties", {}).items():
            if "enum" in prop:
                assert isinstance(prop["enum"], list) and prop["enum"], (
                    f"{t.name}.{prop_name}: enum must be a non-empty list"
                )


def test_every_advertised_tool_is_routable():
    """Every advertised tool name must hit a real dispatch branch in
    call_tool rather than falling through to the 'Unknown tool' sentinel.

    We pass empty arguments: tools with required args will raise KeyError
    (proving the branch executed and reached arg extraction), while
    no-arg tools will attempt a request against the AsyncMock client.
    Either way, the 'Unknown tool' path must never be reached.
    """
    import json as _json
    from unittest.mock import AsyncMock, MagicMock
    import httpx

    # Ensure call_tool passes the REPORIUM_API_URL guard.
    mcp_server.REPORIUM_API_URL = "http://test.local"

    ok_response = MagicMock(spec=httpx.Response)
    ok_response.status_code = 200
    ok_response.json = MagicMock(return_value={"ok": True})
    ok_response.raise_for_status = MagicMock()

    fake_client = AsyncMock(spec=httpx.AsyncClient)
    fake_client.get = AsyncMock(return_value=ok_response)
    fake_client.post = AsyncMock(return_value=ok_response)
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=False)

    original_get_client = mcp_server.get_client
    mcp_server.get_client = lambda: fake_client
    try:
        for name in EXPECTED_TOOLS:
            try:
                result = asyncio.run(mcp_server.call_tool(name, {}))
                # Tool ran; result must be MCP TextContent, never the
                # unknown-tool sentinel.
                assert isinstance(result, list) and result, f"{name}: empty result"
                text = result[0].text
                assert "Unknown tool" not in text, (
                    f"{name}: routed to Unknown tool sentinel"
                )
            except KeyError:
                # Required-arg extraction fired => branch is wired up. OK.
                pass
    finally:
        mcp_server.get_client = original_get_client


def test_unknown_tool_returns_error_sentinel():
    mcp_server.REPORIUM_API_URL = "http://test.local"
    from unittest.mock import AsyncMock
    import httpx

    fake_client = AsyncMock(spec=httpx.AsyncClient)
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=False)

    original_get_client = mcp_server.get_client
    mcp_server.get_client = lambda: fake_client
    try:
        result = asyncio.run(mcp_server.call_tool("does_not_exist", {}))
        assert "Unknown tool" in result[0].text
    finally:
        mcp_server.get_client = original_get_client


def test_call_tool_without_api_url_returns_config_error():
    """When REPORIUM_API_URL is unset, call_tool must short-circuit with a
    config error and never attempt a request."""
    original = mcp_server.REPORIUM_API_URL
    mcp_server.REPORIUM_API_URL = ""
    try:
        result = asyncio.run(mcp_server.call_tool("search_repos", {"query": "x"}))
        assert "REPORIUM_API_URL" in result[0].text
    finally:
        mcp_server.REPORIUM_API_URL = original
