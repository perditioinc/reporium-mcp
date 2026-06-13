"""Unit tests for tools/search.py (mocked API)."""
import json

import httpx
import pytest

from tools.search import search_repos, search_repos_semantic
from tests.conftest import make_client, make_response


@pytest.mark.asyncio
async def test_search_repos_calls_keyword_endpoint_with_params():
    resp = make_response(json_data=[{"name": "acme/rag"}])
    client = make_client(get_return=resp)

    result = await search_repos(client, "rag frameworks", limit=7)

    client.get.assert_called_once_with(
        "/search", params={"q": "rag frameworks", "limit": 7}
    )
    parsed = json.loads(result)
    assert parsed == [{"name": "acme/rag"}]


@pytest.mark.asyncio
async def test_search_repos_default_limit_is_ten():
    resp = make_response(json_data=[])
    client = make_client(get_return=resp)

    await search_repos(client, "anything")

    _, kwargs = client.get.call_args
    assert kwargs["params"]["limit"] == 10


@pytest.mark.asyncio
async def test_search_repos_semantic_calls_semantic_endpoint():
    resp = make_response(json_data={"results": [{"name": "x", "score": 0.9}]})
    client = make_client(get_return=resp)

    result = await search_repos_semantic(client, "production rag", limit=3)

    client.get.assert_called_once_with(
        "/search/semantic", params={"q": "production rag", "limit": 3}
    )
    assert "0.9" in result


@pytest.mark.asyncio
async def test_search_repos_non_200_returns_structured_error():
    resp = make_response(status_code=500, text="boom")
    client = make_client(get_return=resp)

    result = await search_repos(client, "q")

    parsed = json.loads(result)
    assert "error" in parsed
    assert "500" in parsed["error"]


@pytest.mark.asyncio
async def test_search_repos_semantic_timeout_returns_structured_error():
    client = make_client(get_side_effect=httpx.TimeoutException("timed out"))

    result = await search_repos_semantic(client, "q")

    parsed = json.loads(result)
    assert "error" in parsed
    assert "Request failed" in parsed["error"]
