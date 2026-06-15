"""Unit tests for tools/intelligence.py. All Reporium API calls are mocked.

The existing test_intelligence_client.py covers ask_portfolio and
get_portfolio_insights path correctness; this module adds the remaining
intelligence tools plus error-handling coverage.
"""
import pytest

from tools.intelligence import (
    ask_portfolio,
    get_portfolio_gaps,
    get_ai_trends,
    get_portfolio_insights,
    get_cross_dimension_stats,
)
from tests.conftest import make_client, make_response, http_status_error, loads


@pytest.mark.asyncio
async def test_ask_portfolio_posts_question_body():
    client = make_client(post=make_response(json_body={"answer": "strongest: agents"}))

    result = await ask_portfolio(client, "What are our strongest areas?")

    client.post.assert_called_once_with(
        "/ask", json={"question": "What are our strongest areas?"}
    )
    assert "strongest: agents" in loads(result)["answer"]


@pytest.mark.asyncio
async def test_get_portfolio_gaps_calls_gaps_endpoint():
    client = make_client(get=make_response(json_body={"gaps": ["mlops"]}))

    result = await get_portfolio_gaps(client)

    client.get.assert_called_once_with("/gaps")
    assert loads(result)["gaps"] == ["mlops"]


@pytest.mark.asyncio
async def test_get_ai_trends_reads_ai_trend_taxonomy():
    client = make_client(get=make_response(json_body=[{"value": "agents"}]))

    result = await get_ai_trends(client)

    client.get.assert_called_once_with("/taxonomy/ai_trend")
    assert loads(result)[0]["value"] == "agents"


@pytest.mark.asyncio
async def test_get_portfolio_insights_calls_insights_endpoint():
    client = make_client(get=make_response(json_body={"insights": ["rising gap"]}))

    result = await get_portfolio_insights(client)

    client.get.assert_called_once_with("/insights")
    assert "rising gap" in loads(result)["insights"]


@pytest.mark.asyncio
async def test_get_cross_dimension_stats_passes_both_dims_and_limit():
    client = make_client(get=make_response(json_body={"pairs": []}))

    result = await get_cross_dimension_stats(client, "skill_area", "industry", limit=4)

    client.get.assert_called_once_with(
        "/analytics/cross-dimension",
        params={"dim1": "skill_area", "dim2": "industry", "limit": 4},
    )
    assert "pairs" in loads(result)


@pytest.mark.asyncio
async def test_ask_portfolio_status_error_includes_code():
    err = http_status_error(429, text="rate limited")
    client = make_client(post=make_response(raise_for_status_error=err))

    result = await ask_portfolio(client, "q")

    parsed = loads(result)
    assert "429" in parsed["error"]
    assert "rate limited" in parsed["error"]


@pytest.mark.asyncio
async def test_get_ai_trends_request_failed_branch():
    client = make_client(get=ConnectionError("dns failure"))

    result = await get_ai_trends(client)

    parsed = loads(result)
    assert "Request failed" in parsed["error"]
    assert "dns failure" in parsed["error"]
