import json
import httpx

CATEGORY_LABELS: dict[str, str] = {
    "ai-agents":           "AI Agents & Orchestration",
    "rag-retrieval":       "RAG & Retrieval",
    "inference-serving":   "Inference & Serving",
    "model-training":      "Model Training & Fine-tuning",
    "evals-benchmarking":  "Evals & Benchmarking",
    "observability":       "Observability",
    "safety-alignment":    "Safety & Alignment",
    "coding-devtools":     "Coding & Dev Tools",
    "dev-tools":           "Dev Tools & Automation",
    "data-science":        "Data Science & Analytics",
    "computer-vision":     "Computer Vision",
    "nlp-text":            "NLP & Text",
    "generative-media":    "Generative Media",
    "mlops-infrastructure":"MLOps & Infrastructure",
    "ml-platform":         "ML Platform & Infrastructure",
    "foundation-models":   "Foundation Models",
    "multimodal":          "Multimodal AI",
    "edge-mobile":         "Edge & Mobile AI",
    "search-knowledge":    "Search & Knowledge",
    "learning-resources":  "Learning Resources",
    "other":               "Other AI / ML",
}


async def list_categories(client: httpx.AsyncClient) -> str:
    """Return the 16 canonical primary_category IDs and their human-readable labels."""
    return json.dumps(
        [{"id": k, "label": v} for k, v in CATEGORY_LABELS.items()],
        indent=2,
    )


async def get_repos_by_category(
    client: httpx.AsyncClient,
    category: str,
    limit: int = 20,
) -> str:
    """Get repos filtered by primary_category (one of the 16 canonical DB categories)."""
    try:
        response = await client.get(
            "/repos",
            params={"category": category, "limit": limit},
        )
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"API error {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        return json.dumps({"error": f"Request failed: {str(e)}"})


async def get_knowledge_graph(
    client: httpx.AsyncClient,
    edge_type: str | None = None,
    limit: int = 50,
) -> str:
    """Get edges from the repo knowledge graph showing relationships between repos.

    Edge types:
    - ALTERNATIVE_TO: repos that are alternatives to each other
    - COMPATIBLE_WITH: repos that work well together
    - DEPENDS_ON: repos that depend on another
    - SIMILAR_TO: repos with overlapping capabilities
    - EXTENDS: repos that build on top of another
    """
    try:
        params: dict = {"limit": limit}
        if edge_type:
            params["edge_type"] = edge_type
        response = await client.get("/graph/edges", params=params)
        response.raise_for_status()
        data = response.json()
        # Summarise for MCP consumption: total + edge_types + edges list
        return json.dumps(
            {
                "total_edges": data.get("total", 0),
                "edge_types_available": data.get("edgeTypes", []),
                "edges": data.get("edges", []),
            },
            indent=2,
        )
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"API error {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        return json.dumps({"error": f"Request failed: {str(e)}"})
