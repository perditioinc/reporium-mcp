"""18-tool contract test for the stdio MCP server.

Asserts the advertised tool surface is exactly the 18 documented tools, that
every tool exposes a well-formed MCP inputSchema, and that the call_tool
dispatcher routes every advertised tool name (no tool is registered but
un-dispatchable). The README badge and the "Tool Reference (18 tools)" section
both promise 18; this test makes that promise enforceable.

No live API calls: list_tools() builds static metadata, and the dispatch check
mocks get_client + each tool function so nothing leaves the process.
"""
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import mcp_server


# The 18 tools the server advertises and documents. Sorted for stable diffs.
EXPECTED_TOOLS = sorted(
    [
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
    ]
)

# Minimal valid arguments for each tool so the dispatcher reaches the right
# branch without a KeyError on a required argument.
SAMPLE_ARGS = {
    "search_repos": {"query": "x"},
    "search_repos_semantic": {"query": "x"},
    "get_repo": {"name": "owner/repo"},
    "find_similar_repos": {"repo_name": "owner/repo"},
    "list_taxonomy_dimensions": {},
    "list_taxonomy_values": {"dimension": "skill_area"},
    "get_repos_by_taxonomy": {"dimension": "skill_area", "value": "nlp"},
    "ask_portfolio": {"question": "x?"},
    "get_portfolio_gaps": {},
    "get_ai_trends": {},
    "get_portfolio_insights": {},
    "get_cross_dimension_stats": {"dim1": "skill_area", "dim2": "industry"},
    "get_repo_quality": {"name": "owner/repo"},
    "get_quality_signals": {"repo_name": "owner/repo"},
    "list_taxonomy_gaps": {},
    "list_categories": {},
    "get_repos_by_category": {"category": "ai-agents"},
    "get_knowledge_graph": {},
}


@pytest.fixture
async def tools():
    return await mcp_server.list_tools()


@pytest.mark.asyncio
async def test_exactly_18_tools_registered(tools):
    assert len(tools) == 18


@pytest.mark.asyncio
async def test_advertised_tool_names_match_expected(tools):
    names = sorted(t.name for t in tools)
    assert names == EXPECTED_TOOLS


@pytest.mark.asyncio
async def test_tool_names_are_unique(tools):
    names = [t.name for t in tools]
    assert len(names) == len(set(names)), "duplicate tool name advertised"


@pytest.mark.asyncio
async def test_every_tool_has_description(tools):
    for t in tools:
        assert t.description, f"tool {t.name} missing description"
        assert len(t.description) > 10, f"tool {t.name} has a stub description"


@pytest.mark.asyncio
async def test_every_tool_has_valid_mcp_input_schema(tools):
    for t in tools:
        schema = t.inputSchema
        assert isinstance(schema, dict), f"{t.name}: inputSchema is not a dict"
        # MCP requires an object schema at the top level.
        assert schema.get("type") == "object", f"{t.name}: schema type must be 'object'"
        assert "properties" in schema, f"{t.name}: schema missing 'properties'"
        assert isinstance(schema["properties"], dict), f"{t.name}: 'properties' not a dict"
        assert "required" in schema, f"{t.name}: schema missing 'required'"
        assert isinstance(schema["required"], list), f"{t.name}: 'required' not a list"


@pytest.mark.asyncio
async def test_required_fields_are_subset_of_properties(tools):
    # A required field that isn't a declared property is an invalid schema and
    # a real bug: the client cannot satisfy it.
    for t in tools:
        props = set(t.inputSchema.get("properties", {}).keys())
        required = set(t.inputSchema.get("required", []))
        missing = required - props
        assert not missing, f"{t.name}: required fields not in properties: {missing}"


@pytest.mark.asyncio
async def test_enum_constraints_are_lists_of_strings(tools):
    # Several schemas use enum constraints (dimension, category, edge_type,
    # severity). Each enum must be a non-empty list of strings.
    for t in tools:
        for prop_name, prop in t.inputSchema.get("properties", {}).items():
            if "enum" in prop:
                enum = prop["enum"]
                assert isinstance(enum, list) and enum, (
                    f"{t.name}.{prop_name}: enum must be a non-empty list"
                )
                assert all(isinstance(v, str) for v in enum), (
                    f"{t.name}.{prop_name}: enum values must be strings"
                )


@pytest.mark.asyncio
async def test_sample_args_cover_all_required_fields(tools):
    # Guards the test fixture itself: every required arg has a sample value so
    # the dispatch test below actually exercises each branch.
    for t in tools:
        required = set(t.inputSchema.get("required", []))
        provided = set(SAMPLE_ARGS[t.name].keys())
        assert required <= provided, (
            f"{t.name}: SAMPLE_ARGS missing required {required - provided}"
        )


@pytest.mark.asyncio
async def test_dispatcher_routes_every_advertised_tool(monkeypatch):
    """Each advertised tool name must reach a real handler, never the
    'Unknown tool' fallback. We mock get_client and every tools.* function the
    dispatcher imports so no HTTP happens, then call call_tool for each name.
    """
    # Ensure the URL guard does not short-circuit.
    monkeypatch.setattr(mcp_server, "REPORIUM_API_URL", "http://mock.local")

    # get_client() is used as `async with get_client() as client`. Provide an
    # async-context-manager mock so the dispatcher body runs.
    fake_client = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=fake_client)
    cm.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(mcp_server, "get_client", lambda: cm)

    # Patch each tool coroutine referenced in mcp_server's namespace to a
    # sentinel so we can detect that the right one was invoked and avoid any
    # real logic/IO.
    handler_names = [
        "search_repos", "search_repos_semantic", "get_repo", "find_similar_repos",
        "list_taxonomy_dimensions", "list_taxonomy_values", "get_repos_by_taxonomy",
        "ask_portfolio", "get_portfolio_gaps", "get_ai_trends", "get_portfolio_insights",
        "get_cross_dimension_stats", "get_repo_quality", "get_quality_signals",
        "list_taxonomy_gaps", "list_categories", "get_repos_by_category",
        "get_knowledge_graph",
    ]
    for hn in handler_names:
        monkeypatch.setattr(mcp_server, hn, AsyncMock(return_value=f'{{"ok":"{hn}"}}'))

    for tool_name in EXPECTED_TOOLS:
        out = await mcp_server.call_tool(tool_name, SAMPLE_ARGS[tool_name])
        assert len(out) == 1
        text = out[0].text
        assert "Unknown tool" not in text, f"{tool_name} hit the unknown-tool fallback"


@pytest.mark.asyncio
async def test_unknown_tool_returns_error():
    with patch.object(mcp_server, "REPORIUM_API_URL", "http://mock.local"):
        out = await mcp_server.call_tool("not_a_real_tool", {})
    assert "Unknown tool" in out[0].text


@pytest.mark.asyncio
async def test_missing_api_url_short_circuits_before_any_call():
    # With no API URL, call_tool must return the config error and never build a
    # client. This protects the offline/guarded path.
    with patch.object(mcp_server, "REPORIUM_API_URL", ""):
        with patch.object(mcp_server, "get_client") as gc:
            out = await mcp_server.call_tool("search_repos", {"query": "x"})
            gc.assert_not_called()
    assert "REPORIUM_API_URL" in out[0].text
