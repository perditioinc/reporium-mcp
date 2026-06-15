"""Unit tests for tools/search.py. All Reporium API calls are mocked."""
import pytest

from tools.search import search_repos, search_repos_semantic
from tests.conftest import make_client, make_response, http_status_error, loads


@pytest.mark.asyncio
async def test_search_repos_hits_keyword_endpoint_with_query_and_limit():
    client = make_client(get=make_response(json_body=[{"name": "owner/repo-a"}]))

    result = await search_repos(client, "rag frameworks", limit=7)

    client.get.assert_called_once_with(
        "/search", params={"q": "rag frameworks", "limit": 7}
    )
    assert loads(result) == [{"name": "owner/repo-a"}]


@pytest.mark.asyncio
async def test_search_repos_default_limit_is_ten():
    client = make_client(get=make_response(json_body=[]))

    await search_repos(client, "anything")

    client.get.assert_called_once_with("/search", params={"q": "anything", "limit": 10})


@pytest.mark.asyncio
async def test_search_repos_semantic_hits_semantic_endpoint():
    client = make_client(
        get=make_response(json_body=[{"name": "owner/repo-b", "score": 0.91}])
    )

    result = await search_repos_semantic(client, "production RAG", limit=3)

    client.get.assert_called_once_with(
        "/search/semantic", params={"q": "production RAG", "limit": 3}
    )
    parsed = loads(result)
    assert parsed[0]["score"] == 0.91


@pytest.mark.asyncio
async def test_search_repos_surfaces_api_status_error():
    err = http_status_error(500, text="boom")
    client = make_client(get=make_response(raise_for_status_error=err))

    result = await search_repos(client, "q")

    parsed = loads(result)
    assert "error" in parsed
    assert "500" in parsed["error"]
    assert "boom" in parsed["error"]


@pytest.mark.asyncio
async def test_search_repos_semantic_surfaces_transport_error():
    # A non-HTTPStatusError (e.g. timeout / connection) hits the generic branch.
    client = make_client(get=TimeoutError("read timed out"))

    result = await search_repos_semantic(client, "q")

    parsed = loads(result)
    assert "error" in parsed
    assert "Request failed" in parsed["error"]
    assert "read timed out" in parsed["error"]
