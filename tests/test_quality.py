"""Unit tests for tools/quality.py. All Reporium API calls are mocked."""
import pytest

from tools.quality import get_quality_signals, list_taxonomy_gaps
from tests.conftest import make_client, make_response, http_status_error, loads


@pytest.mark.asyncio
async def test_get_quality_signals_returns_signals_when_present():
    client = make_client(
        get=make_response(
            json_body={"quality_signals": {"overall_score": 73, "is_active": True}}
        )
    )

    result = await get_quality_signals(client, "owner/repo")

    client.get.assert_called_once_with("/repos/owner/repo")
    parsed = loads(result)
    assert parsed["repo"] == "owner/repo"
    assert parsed["quality_signals"]["overall_score"] == 73


@pytest.mark.asyncio
async def test_get_quality_signals_explains_when_not_computed():
    # quality_signals absent -> tool returns None plus an explanatory message,
    # rather than erroring.
    client = make_client(get=make_response(json_body={"name": "owner/repo"}))

    result = await get_quality_signals(client, "owner/repo")

    parsed = loads(result)
    assert parsed["quality_signals"] is None
    assert "have not been computed" in parsed["message"]


@pytest.mark.asyncio
async def test_get_quality_signals_404():
    err = http_status_error(404)
    client = make_client(get=make_response(status_code=404, raise_for_status_error=err))

    result = await get_quality_signals(client, "owner/missing")

    assert loads(result)["error"] == "Repo 'owner/missing' not found."


def _gap(dimension, value, severity):
    return {"dimension": dimension, "value": value, "severity": severity}


@pytest.mark.asyncio
async def test_list_taxonomy_gaps_filters_below_min_severity():
    gaps = [
        _gap("skill_area", "a", "low"),
        _gap("skill_area", "b", "medium"),
        _gap("industry", "c", "high"),
    ]
    client = make_client(get=make_response(json_body=gaps))

    result = await list_taxonomy_gaps(client, min_severity="medium")

    client.get.assert_called_once_with("/gaps/taxonomy")
    parsed = loads(result)
    # 'low' is dropped; medium and high remain.
    severities = {g["severity"] for g in parsed["gaps"]}
    assert severities == {"medium", "high"}
    assert parsed["count"] == 2


@pytest.mark.asyncio
async def test_list_taxonomy_gaps_high_only():
    gaps = [
        _gap("skill_area", "a", "low"),
        _gap("skill_area", "b", "medium"),
        _gap("industry", "c", "high"),
    ]
    client = make_client(get=make_response(json_body=gaps))

    result = await list_taxonomy_gaps(client, min_severity="high")

    parsed = loads(result)
    assert parsed["count"] == 1
    assert parsed["gaps"][0]["severity"] == "high"


@pytest.mark.asyncio
async def test_list_taxonomy_gaps_dimension_filter():
    gaps = [
        _gap("skill_area", "a", "high"),
        _gap("industry", "c", "high"),
    ]
    client = make_client(get=make_response(json_body=gaps))

    result = await list_taxonomy_gaps(client, dimension="industry", min_severity="low")

    parsed = loads(result)
    assert parsed["count"] == 1
    assert parsed["gaps"][0]["dimension"] == "industry"
    assert parsed["dimension_filter"] == "industry"


@pytest.mark.asyncio
async def test_list_taxonomy_gaps_unexpected_format_errors():
    # Non-list payload is rejected with a clear error.
    client = make_client(get=make_response(json_body={"not": "a list"}))

    result = await list_taxonomy_gaps(client)

    assert "Unexpected response format" in loads(result)["error"]


@pytest.mark.asyncio
async def test_list_taxonomy_gaps_status_error():
    err = http_status_error(500, text="server down")
    client = make_client(get=make_response(raise_for_status_error=err))

    result = await list_taxonomy_gaps(client)

    parsed = loads(result)
    assert "500" in parsed["error"]
    assert "server down" in parsed["error"]
