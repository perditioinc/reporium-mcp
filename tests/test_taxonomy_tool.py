"""Unit tests for tools/taxonomy.py (mocked API)."""
import json

import httpx
import pytest

from tools.taxonomy import (
    list_taxonomy_dimensions,
    list_taxonomy_values,
    get_repos_by_taxonomy,
    VALID_DIMENSIONS,
)
from tests.conftest import make_client, make_response


@pytest.mark.asyncio
async def test_list_taxonomy_dimensions_calls_endpoint():
    resp = make_response(json_data=[{"dimension": "skill_area", "count": 12}])
    client = make_client(get_return=resp)

    result = await list_taxonomy_dimensions(client)

    client.get.assert_called_once_with("/taxonomy/dimensions")
    assert "skill_area" in result


@pytest.mark.asyncio
async def test_list_taxonomy_values_valid_dimension():
    resp = make_response(json_data=[{"value": "nlp", "count": 4}])
    client = make_client(get_return=resp)

    result = await list_taxonomy_values(client, "skill_area")

    client.get.assert_called_once_with("/taxonomy/skill_area")
    assert "nlp" in result


@pytest.mark.asyncio
async def test_list_taxonomy_values_rejects_invalid_dimension_without_calling_api():
    client = make_client()

    result = await list_taxonomy_values(client, "not_a_dimension")

    client.get.assert_not_called()
    parsed = json.loads(result)
    assert "Invalid dimension" in parsed["error"]


@pytest.mark.asyncio
async def test_all_valid_dimensions_are_accepted():
    """Mutation guard: every dimension in VALID_DIMENSIONS must pass the
    guard and reach the API call."""
    for dim in VALID_DIMENSIONS:
        resp = make_response(json_data=[])
        client = make_client(get_return=resp)
        await list_taxonomy_values(client, dim)
        client.get.assert_called_once_with(f"/taxonomy/{dim}")


@pytest.mark.asyncio
async def test_get_repos_by_taxonomy_uses_dedicated_endpoint_on_200():
    resp = make_response(json_data=[{"name": "health/repo"}], status_code=200)
    client = make_client(get_return=resp)

    result = await get_repos_by_taxonomy(client, "industry", "healthcare", limit=5)

    client.get.assert_called_once_with(
        "/taxonomy/industry/healthcare/repos", params={"limit": 5}
    )
    assert "health/repo" in result


@pytest.mark.asyncio
async def test_get_repos_by_taxonomy_falls_back_to_full_library_on_404():
    """When the dedicated endpoint 404s, it must fetch /library/full and
    filter locally by the taxonomy value."""
    dedicated = make_response(json_data=None, status_code=404)
    full = make_response(status_code=200, json_data=[
        {"name": "a", "taxonomy": {"industry": ["healthcare", "finance"]}},
        {"name": "b", "taxonomy": {"industry": ["retail"]}},
    ])
    client = make_client()
    client.get.side_effect = [dedicated, full]

    result = await get_repos_by_taxonomy(client, "industry", "healthcare")

    # second call must be the full-library fallback
    assert client.get.call_args_list[1].args[0] == "/library/full"
    parsed = json.loads(result)
    names = [r["name"] for r in parsed]
    assert names == ["a"]  # only the healthcare repo matched


@pytest.mark.asyncio
async def test_get_repos_by_taxonomy_rejects_invalid_dimension():
    client = make_client()

    result = await get_repos_by_taxonomy(client, "bogus", "x")

    client.get.assert_not_called()
    assert "Invalid dimension" in json.loads(result)["error"]


@pytest.mark.asyncio
async def test_list_taxonomy_values_timeout_returns_error():
    client = make_client(get_side_effect=httpx.TimeoutException("slow"))

    result = await list_taxonomy_values(client, "industry")

    assert "Request failed" in json.loads(result)["error"]
