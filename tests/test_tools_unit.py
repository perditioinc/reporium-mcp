"""Per-tool-module unit tests (search/taxonomy/repos/graph/quality/intelligence).

Every reporium-api call is mocked via the `mock_client` fixture and the
`make_response` helper in conftest.py. No live network calls are made.

These tests pin the endpoint *contract* each tool function depends on: the URL
path, the query/body parameters, and that a successful response body is passed
through to the JSON string the MCP tool returns. If someone changes a path
(e.g. /search -> /v2/search) or a param name (q -> query), these fail.
"""
import json

import pytest

from conftest import make_response

from tools.search import search_repos, search_repos_semantic
from tools.taxonomy import (
    list_taxonomy_dimensions,
    list_taxonomy_values,
    get_repos_by_taxonomy,
)
from tools.repos import get_repo, find_similar_repos, get_repo_quality
from tools.graph import list_categories, get_repos_by_category, get_knowledge_graph
from tools.quality import get_quality_signals, list_taxonomy_gaps
from tools.intelligence import (
    ask_portfolio,
    get_portfolio_gaps,
    get_ai_trends,
    get_portfolio_insights,
    get_cross_dimension_stats,
)


# --------------------------------------------------------------------------- #
# search
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_search_repos_path_and_params(mock_client):
    mock_client.get.return_value = make_response([{"name": "langchain"}])

    result = await search_repos(mock_client, "rag frameworks", limit=7)

    mock_client.get.assert_called_once_with(
        "/search", params={"q": "rag frameworks", "limit": 7}
    )
    assert "langchain" in result


@pytest.mark.asyncio
async def test_search_repos_default_limit(mock_client):
    mock_client.get.return_value = make_response([])
    await search_repos(mock_client, "x")
    _, kwargs = mock_client.get.call_args
    assert kwargs["params"]["limit"] == 10


@pytest.mark.asyncio
async def test_search_repos_semantic_path(mock_client):
    mock_client.get.return_value = make_response({"results": [{"name": "llamaindex"}]})

    result = await search_repos_semantic(mock_client, "healthcare nlp", limit=3)

    mock_client.get.assert_called_once_with(
        "/search/semantic", params={"q": "healthcare nlp", "limit": 3}
    )
    assert "llamaindex" in result


# --------------------------------------------------------------------------- #
# taxonomy
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_list_taxonomy_dimensions_path(mock_client):
    mock_client.get.return_value = make_response([{"dimension": "skill_area", "count": 12}])

    result = await list_taxonomy_dimensions(mock_client)

    mock_client.get.assert_called_once_with("/taxonomy/dimensions")
    assert "skill_area" in result


@pytest.mark.asyncio
async def test_list_taxonomy_values_valid_dimension(mock_client):
    mock_client.get.return_value = make_response([{"value": "nlp", "count": 9}])

    result = await list_taxonomy_values(mock_client, "skill_area")

    mock_client.get.assert_called_once_with("/taxonomy/skill_area")
    assert "nlp" in result


@pytest.mark.asyncio
async def test_list_taxonomy_values_rejects_invalid_dimension(mock_client):
    result = await list_taxonomy_values(mock_client, "not_a_dimension")

    # Must validate locally and NOT hit the API.
    mock_client.get.assert_not_called()
    assert "Invalid dimension" in result


@pytest.mark.asyncio
async def test_get_repos_by_taxonomy_dedicated_endpoint(mock_client):
    mock_client.get.return_value = make_response([{"name": "monai"}], status_code=200)

    result = await get_repos_by_taxonomy(mock_client, "industry", "healthcare", limit=5)

    mock_client.get.assert_called_once_with(
        "/taxonomy/industry/healthcare/repos", params={"limit": 5}
    )
    assert "monai" in result


@pytest.mark.asyncio
async def test_get_repos_by_taxonomy_falls_back_to_library_full(mock_client):
    # First call (dedicated endpoint) returns 404 -> fall back to /library/full.
    not_found = make_response(status_code=404)
    library = make_response(
        {
            "repos": [
                {"name": "monai", "taxonomy": {"industry": ["healthcare", "ml"]}},
                {"name": "stripe-agent", "taxonomy": {"industry": ["fintech"]}},
            ]
        }
    )
    mock_client.get.side_effect = [not_found, library]

    result = await get_repos_by_taxonomy(mock_client, "industry", "healthcare", limit=20)

    # Two calls: dedicated endpoint then the library fallback.
    assert mock_client.get.call_count == 2
    second_call = mock_client.get.call_args_list[1]
    assert second_call.args[0] == "/library/full"
    parsed = json.loads(result)
    names = [r["name"] for r in parsed]
    assert "monai" in names
    assert "stripe-agent" not in names


@pytest.mark.asyncio
async def test_get_repos_by_taxonomy_rejects_invalid_dimension(mock_client):
    result = await get_repos_by_taxonomy(mock_client, "bogus", "x")
    mock_client.get.assert_not_called()
    assert "Invalid dimension" in result


# --------------------------------------------------------------------------- #
# repos
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_get_repo_path(mock_client):
    mock_client.get.return_value = make_response({"name": "vllm", "stars": 1})

    result = await get_repo(mock_client, "vllm")

    mock_client.get.assert_called_once_with("/repos/vllm")
    assert "vllm" in result


@pytest.mark.asyncio
async def test_find_similar_repos_uses_summary_as_semantic_query(mock_client):
    repo = make_response({"name": "vllm", "readme_summary": "fast llm serving"})
    similar = make_response(
        [
            {"name": "vllm"},          # source repo, must be filtered out
            {"name": "tgi"},
            {"name": "sglang"},
        ]
    )
    mock_client.get.side_effect = [repo, similar]

    result = await find_similar_repos(mock_client, "vllm", limit=2)

    # 1st call fetches the repo; 2nd runs semantic search with the summary.
    first, second = mock_client.get.call_args_list
    assert first.args[0] == "/repos/vllm"
    assert second.args[0] == "/search/semantic"
    assert second.kwargs["params"]["q"] == "fast llm serving"
    # limit+1 is requested so the source repo can be filtered out.
    assert second.kwargs["params"]["limit"] == 3

    parsed = json.loads(result)
    names = [r["name"] for r in parsed]
    assert "vllm" not in names
    assert names == ["tgi", "sglang"]


@pytest.mark.asyncio
async def test_get_repo_quality_extracts_quality_signals(mock_client):
    mock_client.get.return_value = make_response(
        {
            "name": "vllm",
            "full_name": "vllm-project/vllm",
            "quality_signals": {"overall_score": 91, "has_ci": True},
            "other": "ignored",
        }
    )

    result = await get_repo_quality(mock_client, "vllm")

    mock_client.get.assert_called_once_with("/repos/vllm")
    parsed = json.loads(result)
    assert parsed["quality_signals"]["overall_score"] == 91
    assert parsed["full_name"] == "vllm-project/vllm"
    # The tool returns ONLY name/full_name/quality_signals, not the whole repo.
    assert "other" not in parsed


# --------------------------------------------------------------------------- #
# graph
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_list_categories_is_static_no_api_call(mock_client):
    result = await list_categories(mock_client)

    # list_categories is purely local data, it must never hit the API.
    mock_client.get.assert_not_called()
    parsed = json.loads(result)
    ids = [c["id"] for c in parsed]
    assert "ai-agents" in ids
    assert "rag-retrieval" in ids
    # Every entry has both id and label.
    assert all("id" in c and "label" in c for c in parsed)


@pytest.mark.asyncio
async def test_get_repos_by_category_path_and_params(mock_client):
    mock_client.get.return_value = make_response([{"name": "autogen"}])

    result = await get_repos_by_category(mock_client, "ai-agents", limit=4)

    mock_client.get.assert_called_once_with(
        "/repos", params={"category": "ai-agents", "limit": 4}
    )
    assert "autogen" in result


@pytest.mark.asyncio
async def test_get_knowledge_graph_summarises_payload(mock_client):
    mock_client.get.return_value = make_response(
        {
            "total": 2,
            "edgeTypes": ["ALTERNATIVE_TO", "DEPENDS_ON"],
            "edges": [{"a": "x", "b": "y", "type": "ALTERNATIVE_TO"}],
            "noise_field": "dropped",
        }
    )

    result = await get_knowledge_graph(mock_client, edge_type="ALTERNATIVE_TO", limit=25)

    mock_client.get.assert_called_once_with(
        "/graph/edges", params={"limit": 25, "edge_type": "ALTERNATIVE_TO"}
    )
    parsed = json.loads(result)
    assert parsed["total_edges"] == 2
    assert parsed["edge_types_available"] == ["ALTERNATIVE_TO", "DEPENDS_ON"]
    assert len(parsed["edges"]) == 1
    assert "noise_field" not in parsed


@pytest.mark.asyncio
async def test_get_knowledge_graph_omits_edge_type_when_none(mock_client):
    mock_client.get.return_value = make_response({"total": 0, "edgeTypes": [], "edges": []})

    await get_knowledge_graph(mock_client, edge_type=None, limit=50)

    _, kwargs = mock_client.get.call_args
    assert "edge_type" not in kwargs["params"]
    assert kwargs["params"]["limit"] == 50


# --------------------------------------------------------------------------- #
# quality
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_get_quality_signals_present(mock_client):
    mock_client.get.return_value = make_response(
        {"quality_signals": {"overall_score": 80, "is_active": True}}
    )

    result = await get_quality_signals(mock_client, "vllm")

    mock_client.get.assert_called_once_with("/repos/vllm")
    parsed = json.loads(result)
    assert parsed["quality_signals"]["overall_score"] == 80
    assert parsed["repo"] == "vllm"


@pytest.mark.asyncio
async def test_get_quality_signals_not_computed(mock_client):
    mock_client.get.return_value = make_response({"quality_signals": None})

    result = await get_quality_signals(mock_client, "vllm")

    parsed = json.loads(result)
    assert parsed["quality_signals"] is None
    assert "have not been computed" in parsed["message"]


@pytest.mark.asyncio
async def test_list_taxonomy_gaps_severity_filter(mock_client):
    mock_client.get.return_value = make_response(
        [
            {"dimension": "skill_area", "value": "rl", "severity": "low"},
            {"dimension": "skill_area", "value": "safety", "severity": "high"},
            {"dimension": "industry", "value": "legal", "severity": "medium"},
        ]
    )

    result = await list_taxonomy_gaps(mock_client, min_severity="high")

    mock_client.get.assert_called_once_with("/gaps/taxonomy")
    parsed = json.loads(result)
    # Only the 'high' item passes a min_severity=high filter.
    assert parsed["count"] == 1
    assert parsed["gaps"][0]["value"] == "safety"


@pytest.mark.asyncio
async def test_list_taxonomy_gaps_dimension_filter(mock_client):
    mock_client.get.return_value = make_response(
        [
            {"dimension": "skill_area", "value": "rl", "severity": "high"},
            {"dimension": "industry", "value": "legal", "severity": "high"},
        ]
    )

    result = await list_taxonomy_gaps(mock_client, dimension="industry", min_severity="low")

    parsed = json.loads(result)
    assert parsed["count"] == 1
    assert parsed["gaps"][0]["dimension"] == "industry"


# --------------------------------------------------------------------------- #
# intelligence
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_ask_portfolio_posts_to_ask(mock_client):
    mock_client.post.return_value = make_response({"answer": "strong in agents"})

    result = await ask_portfolio(mock_client, "what are our strongest areas?")

    mock_client.post.assert_called_once_with(
        "/ask", json={"question": "what are our strongest areas?"}
    )
    assert "strong in agents" in result


@pytest.mark.asyncio
async def test_get_portfolio_gaps_path(mock_client):
    mock_client.get.return_value = make_response({"gaps": []})
    await get_portfolio_gaps(mock_client)
    mock_client.get.assert_called_once_with("/gaps")


@pytest.mark.asyncio
async def test_get_ai_trends_path(mock_client):
    mock_client.get.return_value = make_response([{"trend": "agents"}])
    result = await get_ai_trends(mock_client)
    mock_client.get.assert_called_once_with("/taxonomy/ai_trend")
    assert "agents" in result


@pytest.mark.asyncio
async def test_get_portfolio_insights_path(mock_client):
    mock_client.get.return_value = make_response({"insights": ["x"]})
    await get_portfolio_insights(mock_client)
    mock_client.get.assert_called_once_with("/insights")


@pytest.mark.asyncio
async def test_get_cross_dimension_stats_path_and_params(mock_client):
    mock_client.get.return_value = make_response({"pairs": []})

    await get_cross_dimension_stats(mock_client, "skill_area", "industry", limit=6)

    mock_client.get.assert_called_once_with(
        "/analytics/cross-dimension",
        params={"dim1": "skill_area", "dim2": "industry", "limit": 6},
    )
