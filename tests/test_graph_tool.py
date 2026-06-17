"""Unit tests for tools/graph.py (mocked API)."""
import json

import httpx
import pytest

from tools.graph import list_categories, get_repos_by_category, get_knowledge_graph
from tests.conftest import make_client, make_response


@pytest.mark.asyncio
async def test_list_categories_returns_id_label_pairs_without_network():
    client = make_client()

    result = await list_categories(client)

    # list_categories is local-only; it must not touch the client.
    client.get.assert_not_called()
    parsed = json.loads(result)
    assert isinstance(parsed, list)
    ids = {row["id"] for row in parsed}
    assert "ai-agents" in ids
    assert "rag-retrieval" in ids
    # every entry must carry both id and label
    for row in parsed:
        assert row["id"] and row["label"]


@pytest.mark.asyncio
async def test_get_repos_by_category_calls_repos_endpoint_with_category():
    resp = make_response(json_data=[{"name": "agent/repo"}])
    client = make_client(get_return=resp)

    result = await get_repos_by_category(client, "ai-agents", limit=15)

    client.get.assert_called_once_with(
        "/repos", params={"category": "ai-agents", "limit": 15}
    )
    assert "agent/repo" in result


@pytest.mark.asyncio
async def test_get_repos_by_category_500_returns_error():
    resp = make_response(status_code=500, text="boom")
    client = make_client(get_return=resp)

    result = await get_repos_by_category(client, "ai-agents")

    assert "500" in json.loads(result)["error"]


@pytest.mark.asyncio
async def test_get_knowledge_graph_summarises_payload():
    resp = make_response(json_data={
        "total": 3,
        "edgeTypes": ["ALTERNATIVE_TO", "SIMILAR_TO"],
        "edges": [{"src": "a", "dst": "b", "type": "SIMILAR_TO"}],
    })
    client = make_client(get_return=resp)

    result = await get_knowledge_graph(client, limit=50)

    client.get.assert_called_once_with("/graph/edges", params={"limit": 50})
    parsed = json.loads(result)
    assert parsed["total_edges"] == 3
    assert parsed["edge_types_available"] == ["ALTERNATIVE_TO", "SIMILAR_TO"]
    assert len(parsed["edges"]) == 1


@pytest.mark.asyncio
async def test_get_knowledge_graph_includes_edge_type_param_when_given():
    resp = make_response(json_data={"total": 0, "edgeTypes": [], "edges": []})
    client = make_client(get_return=resp)

    await get_knowledge_graph(client, edge_type="DEPENDS_ON", limit=10)

    _, kwargs = client.get.call_args
    assert kwargs["params"] == {"limit": 10, "edge_type": "DEPENDS_ON"}


@pytest.mark.asyncio
async def test_get_knowledge_graph_omits_edge_type_when_none():
    resp = make_response(json_data={"total": 0, "edgeTypes": [], "edges": []})
    client = make_client(get_return=resp)

    await get_knowledge_graph(client, edge_type=None, limit=10)

    _, kwargs = client.get.call_args
    assert "edge_type" not in kwargs["params"]


@pytest.mark.asyncio
async def test_get_knowledge_graph_defaults_missing_keys():
    """A backend that omits total/edgeTypes/edges must not crash the tool."""
    resp = make_response(json_data={})
    client = make_client(get_return=resp)

    result = await get_knowledge_graph(client)

    parsed = json.loads(result)
    assert parsed["total_edges"] == 0
    assert parsed["edge_types_available"] == []
    assert parsed["edges"] == []


@pytest.mark.asyncio
async def test_get_knowledge_graph_timeout_returns_error():
    client = make_client(get_side_effect=httpx.TimeoutException("slow"))

    result = await get_knowledge_graph(client)

    assert "Request failed" in json.loads(result)["error"]
