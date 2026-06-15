"""Unit tests for tools/repos.py. All Reporium API calls are mocked."""
import pytest

from tools.repos import get_repo, find_similar_repos, get_repo_quality
from tests.conftest import make_client, make_response, http_status_error, loads


@pytest.mark.asyncio
async def test_get_repo_fetches_by_name():
    client = make_client(
        get=make_response(json_body={"name": "owner/repo", "stars": 42})
    )

    result = await get_repo(client, "owner/repo")

    client.get.assert_called_once_with("/repos/owner/repo")
    assert loads(result)["stars"] == 42


@pytest.mark.asyncio
async def test_get_repo_404_returns_friendly_not_found():
    err = http_status_error(404)
    client = make_client(get=make_response(status_code=404, raise_for_status_error=err))

    result = await get_repo(client, "owner/missing")

    parsed = loads(result)
    assert parsed["error"] == "Repo 'owner/missing' not found."


@pytest.mark.asyncio
async def test_get_repo_non_404_status_error_includes_code_and_body():
    err = http_status_error(503, text="unavailable")
    client = make_client(get=make_response(raise_for_status_error=err))

    result = await get_repo(client, "owner/repo")

    parsed = loads(result)
    assert "503" in parsed["error"]
    assert "unavailable" in parsed["error"]


@pytest.mark.asyncio
async def test_find_similar_repos_uses_readme_summary_as_query_and_filters_source():
    repo_resp = make_response(
        json_body={"name": "owner/src", "readme_summary": "a vector db"}
    )
    # Semantic search returns the source repo plus two others; source must be dropped.
    search_resp = make_response(
        json_body=[
            {"name": "owner/src"},
            {"name": "owner/other-1"},
            {"name": "owner/other-2"},
        ]
    )
    client = make_client(get=[repo_resp, search_resp])

    result = await find_similar_repos(client, "owner/src", limit=2)

    # First call fetches the repo, second runs the semantic search.
    first_call, second_call = client.get.call_args_list
    assert first_call.args[0] == "/repos/owner/src"
    assert second_call.args[0] == "/search/semantic"
    # Query is the readme summary; limit is requested as limit+1 to allow for
    # dropping the source repo.
    assert second_call.kwargs["params"]["q"] == "a vector db"
    assert second_call.kwargs["params"]["limit"] == 3

    parsed = loads(result)
    names = [r["name"] for r in parsed]
    assert "owner/src" not in names
    assert names == ["owner/other-1", "owner/other-2"]


@pytest.mark.asyncio
async def test_find_similar_repos_falls_back_to_description_when_no_summary():
    repo_resp = make_response(
        json_body={"name": "owner/src", "description": "fallback text"}
    )
    search_resp = make_response(json_body=[])
    client = make_client(get=[repo_resp, search_resp])

    await find_similar_repos(client, "owner/src", limit=5)

    second_call = client.get.call_args_list[1]
    assert second_call.kwargs["params"]["q"] == "fallback text"


@pytest.mark.asyncio
async def test_find_similar_repos_404_on_source_repo():
    err = http_status_error(404)
    client = make_client(get=make_response(status_code=404, raise_for_status_error=err))

    result = await find_similar_repos(client, "owner/missing")

    parsed = loads(result)
    assert parsed["error"] == "Repo 'owner/missing' not found."


@pytest.mark.asyncio
async def test_get_repo_quality_projects_only_quality_fields():
    client = make_client(
        get=make_response(
            json_body={
                "name": "repo",
                "full_name": "owner/repo",
                "quality_signals": {"overall_score": 88, "has_tests": True},
                "readme_summary": "should not be leaked into projection",
            }
        )
    )

    result = await get_repo_quality(client, "owner/repo")

    parsed = loads(result)
    assert parsed["full_name"] == "owner/repo"
    assert parsed["quality_signals"]["overall_score"] == 88
    # The projection only exposes name/full_name/quality_signals.
    assert set(parsed.keys()) == {"name", "full_name", "quality_signals"}
    assert "readme_summary" not in parsed


@pytest.mark.asyncio
async def test_get_repo_quality_404():
    err = http_status_error(404)
    client = make_client(get=make_response(status_code=404, raise_for_status_error=err))

    result = await get_repo_quality(client, "owner/missing")

    assert loads(result)["error"] == "Repo 'owner/missing' not found."
