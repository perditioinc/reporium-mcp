"""Error-handling tests for Reporium API timeouts and non-200 responses.

Every tool wraps its httpx call in try/except and must degrade to a JSON error
string rather than raising. These tests exercise that contract across GET and
POST tools, simulating real httpx failure modes (timeouts, connection errors,
and HTTP status errors) with mocks only -- no network calls.
"""
import httpx
import pytest

from tools.search import search_repos, search_repos_semantic
from tools.repos import get_repo, find_similar_repos, get_repo_quality
from tools.taxonomy import (
    list_taxonomy_dimensions,
    list_taxonomy_values,
    get_repos_by_taxonomy,
)
from tools.intelligence import (
    ask_portfolio,
    get_portfolio_gaps,
    get_ai_trends,
    get_portfolio_insights,
    get_cross_dimension_stats,
)
from tools.quality import get_quality_signals, list_taxonomy_gaps
from tools.graph import get_repos_by_category, get_knowledge_graph
from tests.conftest import make_client, make_response, http_status_error, loads


# (callable, kwargs) for every GET-backed tool. list_categories is excluded
# because it makes no API call; ask_portfolio is covered separately (POST).
GET_TOOLS = [
    (search_repos, {"query": "q"}),
    (search_repos_semantic, {"query": "q"}),
    (get_repo, {"name": "owner/repo"}),
    (find_similar_repos, {"repo_name": "owner/repo"}),
    (get_repo_quality, {"name": "owner/repo"}),
    (list_taxonomy_dimensions, {}),
    (list_taxonomy_values, {"dimension": "skill_area"}),
    (get_repos_by_taxonomy, {"dimension": "industry", "value": "healthcare"}),
    (get_portfolio_gaps, {}),
    (get_ai_trends, {}),
    (get_portfolio_insights, {}),
    (get_cross_dimension_stats, {"dim1": "skill_area", "dim2": "industry"}),
    (get_quality_signals, {"repo_name": "owner/repo"}),
    (list_taxonomy_gaps, {}),
    (get_repos_by_category, {"category": "ai-agents"}),
    (get_knowledge_graph, {}),
]


@pytest.mark.parametrize("func,kwargs", GET_TOOLS, ids=[f.__name__ for f, _ in GET_TOOLS])
@pytest.mark.asyncio
async def test_get_tools_handle_timeout_without_raising(func, kwargs):
    # httpx.TimeoutException is the real type raised when a request times out.
    client = make_client(get=httpx.TimeoutException("timed out"))

    result = await func(client, **kwargs)

    parsed = loads(result)
    assert "error" in parsed, f"{func.__name__} did not return an error dict on timeout"
    assert "Request failed" in parsed["error"]
    assert "timed out" in parsed["error"]


@pytest.mark.parametrize("func,kwargs", GET_TOOLS, ids=[f.__name__ for f, _ in GET_TOOLS])
@pytest.mark.asyncio
async def test_get_tools_handle_500_without_raising(func, kwargs):
    err = http_status_error(500, text="internal error")
    # status_code is set to 500 as well so tools that branch on status_code
    # before calling raise_for_status (e.g. get_repos_by_taxonomy) still reach
    # the error path realistically.
    client = make_client(
        get=make_response(status_code=500, raise_for_status_error=err)
    )

    result = await func(client, **kwargs)

    parsed = loads(result)
    assert "error" in parsed, f"{func.__name__} did not return an error dict on 500"
    # Non-404 status errors surface the status code and body.
    assert "500" in parsed["error"]


@pytest.mark.asyncio
async def test_ask_portfolio_handles_timeout():
    client = make_client(post=httpx.TimeoutException("timed out"))

    result = await ask_portfolio(client, "q")

    parsed = loads(result)
    assert "Request failed" in parsed["error"]
    assert "timed out" in parsed["error"]


@pytest.mark.asyncio
async def test_ask_portfolio_handles_503():
    err = http_status_error(503, text="unavailable")
    client = make_client(post=make_response(raise_for_status_error=err))

    result = await ask_portfolio(client, "q")

    parsed = loads(result)
    assert "503" in parsed["error"]
    assert "unavailable" in parsed["error"]


@pytest.mark.asyncio
async def test_connect_error_is_handled():
    # ConnectError is raised when the API host is unreachable.
    client = make_client(get=httpx.ConnectError("connection refused"))

    result = await get_repo(client, "owner/repo")

    parsed = loads(result)
    assert "Request failed" in parsed["error"]
    assert "connection refused" in parsed["error"]


@pytest.mark.asyncio
async def test_every_get_tool_error_is_valid_json_string():
    # The MCP contract is that tools always return a JSON-serialisable string;
    # an error must never be a bare exception or non-JSON text.
    err = http_status_error(418, text="teapot")
    for func, kwargs in GET_TOOLS:
        client = make_client(
            get=make_response(status_code=418, raise_for_status_error=err)
        )
        result = await func(client, **kwargs)
        assert isinstance(result, str)
        # Must round-trip through json.loads without error.
        parsed = loads(result)
        assert isinstance(parsed, (dict, list))
