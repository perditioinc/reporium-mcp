"""Unit tests for tools/quality.py (mocked API)."""
import json

import httpx
import pytest

from tools.quality import get_quality_signals, list_taxonomy_gaps
from tests.conftest import make_client, make_response


@pytest.mark.asyncio
async def test_get_quality_signals_returns_signals_when_present():
    resp = make_response(json_data={
        "name": "acme/repo",
        "quality_signals": {"overall_score": 73, "is_active": True},
    })
    client = make_client(get_return=resp)

    result = await get_quality_signals(client, "acme/repo")

    client.get.assert_called_once_with("/repos/acme/repo")
    parsed = json.loads(result)
    assert parsed["quality_signals"]["overall_score"] == 73


@pytest.mark.asyncio
async def test_get_quality_signals_explains_when_not_computed():
    resp = make_response(json_data={"name": "acme/repo", "quality_signals": None})
    client = make_client(get_return=resp)

    result = await get_quality_signals(client, "acme/repo")

    parsed = json.loads(result)
    assert parsed["quality_signals"] is None
    assert "not been computed" in parsed["message"]


@pytest.mark.asyncio
async def test_get_quality_signals_404_returns_not_found():
    resp = make_response(status_code=404, text="nope")
    client = make_client(get_return=resp)

    result = await get_quality_signals(client, "ghost/repo")

    assert json.loads(result)["error"] == "Repo 'ghost/repo' not found."


@pytest.mark.asyncio
async def test_list_taxonomy_gaps_filters_by_min_severity():
    """Default min_severity is 'medium' => low items must be dropped."""
    resp = make_response(json_data=[
        {"dimension": "industry", "value": "legal", "severity": "low"},
        {"dimension": "industry", "value": "fintech", "severity": "medium"},
        {"dimension": "skill_area", "value": "rl", "severity": "high"},
    ])
    client = make_client(get_return=resp)

    result = await list_taxonomy_gaps(client)

    client.get.assert_called_once_with("/gaps/taxonomy")
    parsed = json.loads(result)
    severities = {g["severity"] for g in parsed["gaps"]}
    assert "low" not in severities
    assert parsed["count"] == 2


@pytest.mark.asyncio
async def test_list_taxonomy_gaps_low_severity_includes_everything():
    resp = make_response(json_data=[
        {"dimension": "industry", "value": "legal", "severity": "low"},
        {"dimension": "industry", "value": "fintech", "severity": "high"},
    ])
    client = make_client(get_return=resp)

    result = await list_taxonomy_gaps(client, min_severity="low")

    assert json.loads(result)["count"] == 2


@pytest.mark.asyncio
async def test_list_taxonomy_gaps_filters_by_dimension():
    resp = make_response(json_data=[
        {"dimension": "industry", "value": "legal", "severity": "high"},
        {"dimension": "skill_area", "value": "rl", "severity": "high"},
    ])
    client = make_client(get_return=resp)

    result = await list_taxonomy_gaps(client, dimension="industry", min_severity="high")

    parsed = json.loads(result)
    assert parsed["count"] == 1
    assert parsed["gaps"][0]["dimension"] == "industry"


@pytest.mark.asyncio
async def test_list_taxonomy_gaps_unexpected_format_errors():
    resp = make_response(json_data={"not": "a list"})
    client = make_client(get_return=resp)

    result = await list_taxonomy_gaps(client)

    assert "Unexpected response format" in json.loads(result)["error"]


@pytest.mark.asyncio
async def test_list_taxonomy_gaps_timeout_returns_error():
    client = make_client(get_side_effect=httpx.TimeoutException("slow"))

    result = await list_taxonomy_gaps(client)

    assert "Request failed" in json.loads(result)["error"]
