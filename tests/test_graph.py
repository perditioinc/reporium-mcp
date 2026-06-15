"""Unit tests for tools/graph.py. All Reporium API calls are mocked."""
import pytest

from tools.graph import (
    list_categories,
    get_repos_by_category,
    get_knowledge_graph,
    CATEGORY_LABELS,
)
from tests.conftest import make_client, make_response, http_status_error, loads


@pytest.mark.asyncio
async def test_list_categories_is_local_and_returns_id_label_pairs():
    # list_categories is computed in-process; it must not touch the API.
    client = make_client(get=ConnectionError("should not be called"))

    result = await list_categories(client)

    client.get.assert_not_called()
    parsed = loads(result)
    assert {"id", "label"} <= set(parsed[0].keys())
    ids = {item["id"] for item in parsed}
    assert ids == set(CATEGORY_LABELS.keys())
    # Spot-check a known mapping.
    by_id = {item["id"]: item["label"] for item in parsed}
    assert by_id["rag-retrieval"] == "RAG & Retrieval"


@pytest.mark.asyncio
async def test_get_repos_by_category_passes_category_and_limit():
    client = make_client(get=make_response(json_body=[{"name": "owner/agent-repo"}]))

    result = await get_repos_by_category(client, "ai-agents", limit=12)

    client.get.assert_called_once_with(
        "/repos", params={"category": "ai-agents", "limit": 12}
    )
    assert loads(result)[0]["name"] == "owner/agent-repo"


@pytest.mark.asyncio
async def test_get_repos_by_category_status_error():
    err = http_status_error(502, text="bad gateway")
    client = make_client(get=make_response(raise_for_status_error=err))

    result = await get_repos_by_category(client, "ai-agents")

    parsed = loads(result)
    assert "502" in parsed["error"]
    assert "bad gateway" in parsed["error"]


@pytest.mark.asyncio
async def test_get_knowledge_graph_summarises_payload_no_edge_filter():
    client = make_client(
        get=make_response(
            json_body={
                "total": 3,
                "edgeTypes": ["SIMILAR_TO", "DEPENDS_ON"],
                "edges": [{"from": "a", "to": "b", "type": "SIMILAR_TO"}],
            }
        )
    )

    result = await get_knowledge_graph(client)

    # Default limit is 50 and no edge_type filter is sent.
    client.get.assert_called_once_with("/graph/edges", params={"limit": 50})
    parsed = loads(result)
    assert parsed["total_edges"] == 3
    assert parsed["edge_types_available"] == ["SIMILAR_TO", "DEPENDS_ON"]
    assert len(parsed["edges"]) == 1


@pytest.mark.asyncio
async def test_get_knowledge_graph_includes_edge_type_filter_when_given():
    client = make_client(
        get=make_response(json_body={"total": 0, "edgeTypes": [], "edges": []})
    )

    await get_knowledge_graph(client, edge_type="ALTERNATIVE_TO", limit=10)

    client.get.assert_called_once_with(
        "/graph/edges", params={"limit": 10, "edge_type": "ALTERNATIVE_TO"}
    )


@pytest.mark.asyncio
async def test_get_knowledge_graph_defaults_missing_fields():
    # An empty/partial payload must not crash; defaults fill in.
    client = make_client(get=make_response(json_body={}))

    result = await get_knowledge_graph(client)

    parsed = loads(result)
    assert parsed["total_edges"] == 0
    assert parsed["edge_types_available"] == []
    assert parsed["edges"] == []


@pytest.mark.asyncio
async def test_get_knowledge_graph_status_error():
    err = http_status_error(500, text="graph down")
    client = make_client(get=make_response(raise_for_status_error=err))

    result = await get_knowledge_graph(client)

    parsed = loads(result)
    assert "500" in parsed["error"]
    assert "graph down" in parsed["error"]
