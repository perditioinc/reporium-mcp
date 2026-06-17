"""Cross-module error-handling tests (mocked API).

Guarantees that every tool entrypoint converts API timeouts and non-200
responses into a structured JSON error string instead of raising. A leaked
exception would crash the MCP call_tool dispatch and surface as a protocol
error to the client, so this is a hard contract.
"""
import json

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
from tests.conftest import make_client, make_response


def _is_error_json(result: str) -> bool:
    parsed = json.loads(result)
    return isinstance(parsed, dict) and "error" in parsed


# (callable, kwargs, uses_post)
GET_TOOLS = [
    (search_repos, {"query": "q"}, False),
    (search_repos_semantic, {"query": "q"}, False),
    (get_repo, {"name": "a/b"}, False),
    (find_similar_repos, {"repo_name": "a/b"}, False),
    (get_repo_quality, {"name": "a/b"}, False),
    (list_taxonomy_dimensions, {}, False),
    (list_taxonomy_values, {"dimension": "industry"}, False),
    (get_repos_by_taxonomy, {"dimension": "industry", "value": "x"}, False),
    (get_portfolio_gaps, {}, False),
    (get_ai_trends, {}, False),
    (get_portfolio_insights, {}, False),
    (get_cross_dimension_stats, {"dim1": "a", "dim2": "b"}, False),
    (get_quality_signals, {"repo_name": "a/b"}, False),
    (list_taxonomy_gaps, {}, False),
    (get_repos_by_category, {"category": "ai-agents"}, False),
    (get_knowledge_graph, {}, False),
    (ask_portfolio, {"question": "q"}, True),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("func,kwargs,uses_post", GET_TOOLS, ids=lambda v: getattr(v, "__name__", str(v)))
async def test_timeout_is_caught_and_returns_error(func, kwargs, uses_post):
    exc = httpx.TimeoutException("timed out")
    if uses_post:
        client = make_client(post_side_effect=exc)
    else:
        client = make_client(get_side_effect=exc)

    result = await func(client, **kwargs)

    assert _is_error_json(result), f"{func.__name__} did not return error JSON on timeout"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [500, 502, 503, 403])
@pytest.mark.parametrize("func,kwargs,uses_post", GET_TOOLS, ids=lambda v: getattr(v, "__name__", str(v)))
async def test_non_200_is_caught_and_returns_error(func, kwargs, uses_post, status):
    resp = make_response(status_code=status, text="server said no")

    if uses_post:
        client = make_client(post_return=resp)
    else:
        client = make_client(get_return=resp)

    result = await func(client, **kwargs)

    assert _is_error_json(result), (
        f"{func.__name__} did not return error JSON on HTTP {status}"
    )
    # The status code should be reflected in the error message for these
    # 5xx/403 cases (404 has dedicated messaging tested elsewhere).
    assert str(status) in json.loads(result)["error"]


@pytest.mark.asyncio
async def test_connect_error_is_caught():
    """A network-level connection failure must also be swallowed."""
    client = make_client(get_side_effect=httpx.ConnectError("refused"))

    result = await search_repos(client, "q")

    assert _is_error_json(result)
    assert "Request failed" in json.loads(result)["error"]
