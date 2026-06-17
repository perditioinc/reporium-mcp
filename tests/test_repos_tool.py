"""Unit tests for tools/repos.py (mocked API)."""
import json

import httpx
import pytest

from tools.repos import get_repo, find_similar_repos, get_repo_quality
from tests.conftest import make_client, make_response


@pytest.mark.asyncio
async def test_get_repo_calls_repo_endpoint():
    resp = make_response(json_data={"name": "acme/repo", "stars": 5})
    client = make_client(get_return=resp)

    result = await get_repo(client, "acme/repo")

    client.get.assert_called_once_with("/repos/acme/repo")
    assert json.loads(result)["stars"] == 5


@pytest.mark.asyncio
async def test_get_repo_404_returns_not_found_message():
    resp = make_response(status_code=404, text="nope")
    client = make_client(get_return=resp)

    result = await get_repo(client, "ghost/repo")

    parsed = json.loads(result)
    assert parsed["error"] == "Repo 'ghost/repo' not found."


@pytest.mark.asyncio
async def test_get_repo_500_returns_api_error_not_not_found():
    resp = make_response(status_code=500, text="server error")
    client = make_client(get_return=resp)

    result = await get_repo(client, "acme/repo")

    parsed = json.loads(result)
    assert "500" in parsed["error"]
    assert "not found" not in parsed["error"]


@pytest.mark.asyncio
async def test_find_similar_repos_uses_readme_summary_as_query_and_filters_source():
    """find_similar should: fetch the repo, take readme_summary as the
    semantic query, request limit+1, then drop the source repo from results."""
    repo_resp = make_response(json_data={
        "name": "acme/repo",
        "readme_summary": "a vector database",
    })
    search_resp = make_response(json_data=[
        {"name": "acme/repo", "score": 1.0},   # source, must be filtered
        {"name": "other/db", "score": 0.8},
    ])
    client = make_client()
    client.get.side_effect = [repo_resp, search_resp]

    result = await find_similar_repos(client, "acme/repo", limit=2)

    # second call is the semantic search using the readme summary
    second_call = client.get.call_args_list[1]
    assert second_call.args[0] == "/search/semantic"
    assert second_call.kwargs["params"]["q"] == "a vector database"
    assert second_call.kwargs["params"]["limit"] == 3  # limit + 1

    parsed = json.loads(result)
    names = [r["name"] for r in parsed]
    assert "acme/repo" not in names  # source filtered out
    assert "other/db" in names


@pytest.mark.asyncio
async def test_find_similar_repos_falls_back_to_description_when_no_summary():
    repo_resp = make_response(json_data={
        "name": "acme/repo",
        "description": "fallback text",
    })
    search_resp = make_response(json_data=[])
    client = make_client()
    client.get.side_effect = [repo_resp, search_resp]

    await find_similar_repos(client, "acme/repo")

    second_call = client.get.call_args_list[1]
    assert second_call.kwargs["params"]["q"] == "fallback text"


@pytest.mark.asyncio
async def test_find_similar_repos_404_returns_not_found():
    resp = make_response(status_code=404, text="nope")
    client = make_client(get_return=resp)

    result = await find_similar_repos(client, "ghost/repo")

    assert json.loads(result)["error"] == "Repo 'ghost/repo' not found."


@pytest.mark.asyncio
async def test_get_repo_quality_extracts_only_quality_fields():
    resp = make_response(json_data={
        "name": "acme/repo",
        "full_name": "acme/repo",
        "quality_signals": {"overall_score": 88},
        "huge_field": "should not be returned",
    })
    client = make_client(get_return=resp)

    result = await get_repo_quality(client, "acme/repo")

    parsed = json.loads(result)
    assert parsed["quality_signals"]["overall_score"] == 88
    assert parsed["full_name"] == "acme/repo"
    assert "huge_field" not in parsed


@pytest.mark.asyncio
async def test_get_repo_quality_404_returns_not_found():
    resp = make_response(status_code=404, text="nope")
    client = make_client(get_return=resp)

    result = await get_repo_quality(client, "ghost/repo")

    assert json.loads(result)["error"] == "Repo 'ghost/repo' not found."
