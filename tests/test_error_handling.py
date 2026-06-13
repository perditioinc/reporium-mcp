"""API error-handling tests: timeouts, non-200 responses, and 404 special cases.

All errors are simulated against a mocked client; no live calls. Every tool
function is expected to swallow transport/HTTP errors and return a JSON string
with an "error" key rather than raising, so the MCP server always emits a valid
TextContent payload to the model.
"""
import json

import httpx
import pytest

from conftest import make_response

from tools.search import search_repos, search_repos_semantic
from tools.taxonomy import (
    list_taxonomy_dimensions,
    list_taxonomy_values,
    get_repos_by_taxonomy,
)
from tools.repos import get_repo, find_similar_repos, get_repo_quality
from tools.graph import get_repos_by_category, get_knowledge_graph
from tools.quality import get_quality_signals, list_taxonomy_gaps
from tools.intelligence import (
    ask_portfolio,
    get_portfolio_gaps,
    get_ai_trends,
    get_portfolio_insights,
    get_cross_dimension_stats,
)


def _err(result: str) -> dict:
    parsed = json.loads(result)
    assert "error" in parsed, f"expected an error key, got: {result}"
    return parsed


# --------------------------------------------------------------------------- #
# Timeout handling — a TimeoutException must become a JSON error, not a raise.
# --------------------------------------------------------------------------- #
GET_TIMEOUT_CASES = [
    ("search_repos", lambda c: search_repos(c, "q")),
    ("search_repos_semantic", lambda c: search_repos_semantic(c, "q")),
    ("get_repo", lambda c: get_repo(c, "r")),
    ("find_similar_repos", lambda c: find_similar_repos(c, "r")),
    ("get_repo_quality", lambda c: get_repo_quality(c, "r")),
    ("list_taxonomy_dimensions", lambda c: list_taxonomy_dimensions(c)),
    ("list_taxonomy_values", lambda c: list_taxonomy_values(c, "skill_area")),
    ("get_repos_by_taxonomy", lambda c: get_repos_by_taxonomy(c, "skill_area", "nlp")),
    ("get_repos_by_category", lambda c: get_repos_by_category(c, "ai-agents")),
    ("get_knowledge_graph", lambda c: get_knowledge_graph(c)),
    ("get_quality_signals", lambda c: get_quality_signals(c, "r")),
    ("list_taxonomy_gaps", lambda c: list_taxonomy_gaps(c)),
    ("get_portfolio_gaps", lambda c: get_portfolio_gaps(c)),
    ("get_ai_trends", lambda c: get_ai_trends(c)),
    ("get_portfolio_insights", lambda c: get_portfolio_insights(c)),
    ("get_cross_dimension_stats", lambda c: get_cross_dimension_stats(c, "a", "b")),
]


@pytest.mark.parametrize("name,call", GET_TIMEOUT_CASES, ids=[c[0] for c in GET_TIMEOUT_CASES])
@pytest.mark.asyncio
async def test_get_tools_handle_timeout(mock_client, name, call):
    mock_client.get.side_effect = httpx.TimeoutException("read timed out")
    parsed = _err(await call(mock_client))
    assert "Request failed" in parsed["error"]


@pytest.mark.asyncio
async def test_ask_portfolio_handles_timeout(mock_client):
    mock_client.post.side_effect = httpx.TimeoutException("connect timed out")
    parsed = _err(await ask_portfolio(mock_client, "q?"))
    assert "Request failed" in parsed["error"]


# --------------------------------------------------------------------------- #
# Connection errors (also caught by the broad except) become JSON errors.
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_connect_error_is_handled(mock_client):
    mock_client.get.side_effect = httpx.ConnectError("connection refused")
    parsed = _err(await search_repos(mock_client, "q"))
    assert "Request failed" in parsed["error"]


# --------------------------------------------------------------------------- #
# Non-200 handling — 500 surfaces an "API error 500" message.
# --------------------------------------------------------------------------- #
NON200_GET_CASES = [
    ("search_repos", lambda c: search_repos(c, "q")),
    ("search_repos_semantic", lambda c: search_repos_semantic(c, "q")),
    ("list_taxonomy_dimensions", lambda c: list_taxonomy_dimensions(c)),
    ("list_taxonomy_values", lambda c: list_taxonomy_values(c, "skill_area")),
    ("get_repos_by_category", lambda c: get_repos_by_category(c, "ai-agents")),
    ("get_knowledge_graph", lambda c: get_knowledge_graph(c)),
    ("get_portfolio_gaps", lambda c: get_portfolio_gaps(c)),
    ("get_ai_trends", lambda c: get_ai_trends(c)),
    ("get_portfolio_insights", lambda c: get_portfolio_insights(c)),
    ("get_cross_dimension_stats", lambda c: get_cross_dimension_stats(c, "a", "b")),
    ("list_taxonomy_gaps", lambda c: list_taxonomy_gaps(c)),
]


@pytest.mark.parametrize("name,call", NON200_GET_CASES, ids=[c[0] for c in NON200_GET_CASES])
@pytest.mark.asyncio
async def test_get_tools_handle_500(mock_client, name, call):
    mock_client.get.return_value = make_response(status_code=500, text="boom")
    parsed = _err(await call(mock_client))
    assert "API error 500" in parsed["error"]


@pytest.mark.asyncio
async def test_ask_portfolio_handles_500(mock_client):
    mock_client.post.return_value = make_response(status_code=500, text="boom")
    parsed = _err(await ask_portfolio(mock_client, "q?"))
    assert "API error 500" in parsed["error"]


# --------------------------------------------------------------------------- #
# 404 special-casing — repos/quality return a friendly "not found" message.
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_get_repo_404_is_not_found(mock_client):
    mock_client.get.return_value = make_response(status_code=404)
    parsed = _err(await get_repo(mock_client, "ghost/repo"))
    assert "not found" in parsed["error"].lower()
    assert "ghost/repo" in parsed["error"]


@pytest.mark.asyncio
async def test_get_repo_quality_404_is_not_found(mock_client):
    mock_client.get.return_value = make_response(status_code=404)
    parsed = _err(await get_repo_quality(mock_client, "ghost/repo"))
    assert "not found" in parsed["error"].lower()


@pytest.mark.asyncio
async def test_get_quality_signals_404_is_not_found(mock_client):
    mock_client.get.return_value = make_response(status_code=404)
    parsed = _err(await get_quality_signals(mock_client, "ghost/repo"))
    assert "not found" in parsed["error"].lower()


@pytest.mark.asyncio
async def test_find_similar_repos_404_on_source_repo(mock_client):
    # The very first GET (fetching the source repo) 404s.
    mock_client.get.return_value = make_response(status_code=404)
    parsed = _err(await find_similar_repos(mock_client, "ghost/repo"))
    assert "not found" in parsed["error"].lower()


@pytest.mark.asyncio
async def test_get_quality_signals_non_404_status_is_api_error(mock_client):
    # A 503 must NOT be reported as "not found"; it is a generic API error.
    mock_client.get.return_value = make_response(status_code=503, text="unavailable")
    parsed = _err(await get_quality_signals(mock_client, "r"))
    assert "API error 503" in parsed["error"]
    assert "not found" not in parsed["error"].lower()


# --------------------------------------------------------------------------- #
# Malformed-response handling — bad JSON shape is caught, not raised.
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_list_taxonomy_gaps_rejects_non_list_payload(mock_client):
    mock_client.get.return_value = make_response({"unexpected": "object"})
    parsed = _err(await list_taxonomy_gaps(mock_client))
    assert "Unexpected response format" in parsed["error"]
