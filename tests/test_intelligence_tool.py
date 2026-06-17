"""Unit tests for tools/intelligence.py (mocked API).

Complements the existing test_intelligence_client.py with endpoint/param
coverage for the remaining intelligence tools and their error paths.
"""
import json

import httpx
import pytest

from tools.intelligence import (
    ask_portfolio,
    get_portfolio_gaps,
    get_ai_trends,
    get_portfolio_insights,
    get_cross_dimension_stats,
)
from tests.conftest import make_client, make_response


@pytest.mark.asyncio
async def test_ask_portfolio_posts_question():
    resp = make_response(json_data={"answer": "we are strong in RAG"})
    client = make_client(post_return=resp)

    result = await ask_portfolio(client, "what are our strengths?")

    client.post.assert_called_once_with(
        "/ask", json={"question": "what are our strengths?"}
    )
    assert "strong in RAG" in result


@pytest.mark.asyncio
async def test_get_portfolio_gaps_calls_gaps_endpoint():
    resp = make_response(json_data={"gaps": []})
    client = make_client(get_return=resp)

    await get_portfolio_gaps(client)

    client.get.assert_called_once_with("/gaps")


@pytest.mark.asyncio
async def test_get_ai_trends_calls_ai_trend_taxonomy_endpoint():
    resp = make_response(json_data=[{"trend": "agents", "count": 9}])
    client = make_client(get_return=resp)

    result = await get_ai_trends(client)

    client.get.assert_called_once_with("/taxonomy/ai_trend")
    assert "agents" in result


@pytest.mark.asyncio
async def test_get_portfolio_insights_calls_insights_endpoint():
    resp = make_response(json_data={"insights": ["a"]})
    client = make_client(get_return=resp)

    await get_portfolio_insights(client)

    client.get.assert_called_once_with("/insights")


@pytest.mark.asyncio
async def test_get_cross_dimension_stats_passes_all_params():
    resp = make_response(json_data={"pairs": []})
    client = make_client(get_return=resp)

    await get_cross_dimension_stats(client, "industry", "skill_area", limit=4)

    client.get.assert_called_once_with(
        "/analytics/cross-dimension",
        params={"dim1": "industry", "dim2": "skill_area", "limit": 4},
    )


@pytest.mark.asyncio
async def test_ask_portfolio_non_200_returns_error():
    resp = make_response(status_code=503, text="unavailable")
    client = make_client(post_return=resp)

    result = await ask_portfolio(client, "q")

    assert "503" in json.loads(result)["error"]


@pytest.mark.asyncio
async def test_ask_portfolio_timeout_returns_error():
    client = make_client(post_side_effect=httpx.TimeoutException("slow"))

    result = await ask_portfolio(client, "q")

    assert "Request failed" in json.loads(result)["error"]


@pytest.mark.asyncio
async def test_get_ai_trends_timeout_returns_error():
    client = make_client(get_side_effect=httpx.TimeoutException("slow"))

    result = await get_ai_trends(client)

    assert "Request failed" in json.loads(result)["error"]
