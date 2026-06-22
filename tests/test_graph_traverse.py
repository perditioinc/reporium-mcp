"""Tests for the knowledge-graph traversal helper behind the new agentic MCP tools
(find_alternatives / explore_ecosystem).

Validated capability: typed-graph traversal recalls correct alternatives/ecosystem
repos significantly better than dense-alone or random (pre-check: +0.25 recall vs
random, 95% CI[+0.115,+0.398]). These tools expose that as agent-callable tools.
"""
from tools.graph import seed_neighbors_by_type

SUBGRAPH = {
    "repo_name": "qdrant",
    "edges": [
        {"edgeType": "SIMILAR_TO", "weight": 0.83,
         "source": {"name": "qdrant", "description": "vector db"},
         "target": {"name": "weaviate", "description": "vector db"}},
        {"edgeType": "SIMILAR_TO", "weight": 0.91,
         "source": {"name": "milvus", "description": "vector db"},
         "target": {"name": "qdrant", "description": "vector db"}},
        {"edgeType": "ALTERNATIVE_TO", "weight": 0.7,
         "source": {"name": "qdrant", "description": "vector db"},
         "target": {"name": "chroma", "description": "vector db"}},
        {"edgeType": "SIMILAR_TO", "weight": 0.5,
         "source": {"name": "pinecone-docs", "description": "x"},
         "target": {"name": "other", "description": "y"}},  # unrelated to seed -> excluded
    ],
}


def test_groups_seed_neighbors_by_edge_type():
    g = seed_neighbors_by_type(SUBGRAPH, "qdrant")
    assert set(g.keys()) == {"SIMILAR_TO", "ALTERNATIVE_TO"}
    assert {n["name"] for n in g["SIMILAR_TO"]} == {"weaviate", "milvus"}
    assert {n["name"] for n in g["ALTERNATIVE_TO"]} == {"chroma"}


def test_neighbors_sorted_by_weight_desc():
    g = seed_neighbors_by_type(SUBGRAPH, "qdrant")
    assert [n["name"] for n in g["SIMILAR_TO"]] == ["milvus", "weaviate"]  # 0.91 before 0.83


def test_excludes_edges_not_touching_seed_and_seed_itself():
    g = seed_neighbors_by_type(SUBGRAPH, "qdrant")
    alln = {n["name"] for v in g.values() for n in v}
    assert "qdrant" not in alln and "other" not in alln and "pinecone-docs" not in alln


def test_empty_subgraph():
    assert seed_neighbors_by_type({"edges": []}, "x") == {}
