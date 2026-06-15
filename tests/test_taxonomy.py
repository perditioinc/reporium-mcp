"""Unit tests for tools/taxonomy.py. All Reporium API calls are mocked."""
import pytest

from tools.taxonomy import (
    list_taxonomy_dimensions,
    list_taxonomy_values,
    get_repos_by_taxonomy,
    VALID_DIMENSIONS,
)
from tests.conftest import make_client, make_response, http_status_error, loads


@pytest.mark.asyncio
async def test_list_taxonomy_dimensions_calls_endpoint():
    client = make_client(
        get=make_response(json_body=[{"dimension": "skill_area", "count": 10}])
    )

    result = await list_taxonomy_dimensions(client)

    client.get.assert_called_once_with("/taxonomy/dimensions")
    assert loads(result)[0]["dimension"] == "skill_area"


@pytest.mark.asyncio
async def test_list_taxonomy_values_valid_dimension():
    client = make_client(get=make_response(json_body=[{"value": "nlp", "count": 5}]))

    result = await list_taxonomy_values(client, "skill_area")

    client.get.assert_called_once_with("/taxonomy/skill_area")
    assert loads(result)[0]["value"] == "nlp"


@pytest.mark.asyncio
async def test_list_taxonomy_values_rejects_invalid_dimension_without_calling_api():
    client = make_client(get=make_response(json_body=[]))

    result = await list_taxonomy_values(client, "not_a_dimension")

    # Invalid input must be rejected client-side; no API call is made.
    client.get.assert_not_called()
    parsed = loads(result)
    assert "Invalid dimension" in parsed["error"]
    assert "not_a_dimension" in parsed["error"]


@pytest.mark.asyncio
async def test_get_repos_by_taxonomy_rejects_invalid_dimension():
    client = make_client(get=make_response(json_body=[]))

    result = await get_repos_by_taxonomy(client, "bogus", "value")

    client.get.assert_not_called()
    assert "Invalid dimension" in loads(result)["error"]


@pytest.mark.asyncio
async def test_get_repos_by_taxonomy_uses_dedicated_endpoint_on_200():
    client = make_client(
        get=make_response(
            status_code=200, json_body=[{"name": "owner/health-repo"}]
        )
    )

    result = await get_repos_by_taxonomy(client, "industry", "healthcare", limit=15)

    client.get.assert_called_once_with(
        "/taxonomy/industry/healthcare/repos", params={"limit": 15}
    )
    assert loads(result)[0]["name"] == "owner/health-repo"


@pytest.mark.asyncio
async def test_get_repos_by_taxonomy_falls_back_to_full_library_on_404():
    dedicated_404 = make_response(status_code=404, json_body=None)
    full_library = make_response(
        status_code=200,
        json_body={
            "repos": [
                {"name": "owner/match", "taxonomy": {"industry": ["Healthcare"]}},
                {"name": "owner/nomatch", "taxonomy": {"industry": ["finance"]}},
                {"name": "owner/scalar", "taxonomy": {"industry": "healthcare"}},
            ]
        },
    )
    client = make_client(get=[dedicated_404, full_library])

    result = await get_repos_by_taxonomy(client, "industry", "healthcare", limit=20)

    # Two calls: dedicated endpoint (404), then the full-library fallback.
    calls = [c.args[0] for c in client.get.call_args_list]
    assert calls == ["/taxonomy/industry/healthcare/repos", "/library/full"]

    parsed = loads(result)
    names = [r["name"] for r in parsed]
    # Case-insensitive list match AND scalar match are both included;
    # the non-matching finance repo is excluded.
    assert "owner/match" in names
    assert "owner/scalar" in names
    assert "owner/nomatch" not in names


@pytest.mark.asyncio
async def test_get_repos_by_taxonomy_fallback_respects_limit():
    dedicated_404 = make_response(status_code=404, json_body=None)
    repos = [
        {"name": f"owner/r{i}", "taxonomy": {"use_case": ["rag"]}} for i in range(5)
    ]
    full_library = make_response(status_code=200, json_body={"repos": repos})
    client = make_client(get=[dedicated_404, full_library])

    result = await get_repos_by_taxonomy(client, "use_case", "rag", limit=2)

    assert len(loads(result)) == 2


@pytest.mark.asyncio
async def test_valid_dimensions_constant_matches_advertised_enum():
    # Guards against drift between the module constant and the documented enum.
    assert set(VALID_DIMENSIONS) == {
        "skill_area",
        "industry",
        "use_case",
        "modality",
        "ai_trend",
        "deployment_context",
        "tags",
        "categories",
    }
