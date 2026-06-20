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


def seed_neighbors_by_type(subgraph: dict, seed: str) -> dict:
    """Group a repo's DIRECT graph neighbors by edge type, sorted by weight desc.

    Pure helper over a /graph/subgraph response. Returns {edgeType: [{name, description,
    weight}]}; excludes the seed itself and edges that do not touch the seed; dedupes by name.
    """
    out: dict = {}
    for e in subgraph.get("edges", []):
        s = e.get("source", {}) or {}
        t = e.get("target", {}) or {}
        sn, tn = s.get("name"), t.get("name")
        if seed == sn:
            nbr = t
        elif seed == tn:
            nbr = s
        else:
            continue
        et = e.get("edgeType", "UNKNOWN")
        out.setdefault(et, []).append(
            {"name": nbr.get("name"), "description": nbr.get("description"),
             "weight": e.get("weight") or 0.0}
        )
    for et in out:
        seen: set = set()
        uniq: list = []
        for n in sorted(out[et], key=lambda x: -(x["weight"] or 0.0)):
            if n["name"] and n["name"] not in seen:
                seen.add(n["name"])
                uniq.append(n)
        out[et] = uniq
    return out


async def find_alternatives(client: httpx.AsyncClient, repo_name: str, limit: int = 8) -> str:
    """Find ALTERNATIVE/SIMILAR repos to a given repo by traversing the knowledge graph.

    Validated capability (offline pre-check): typed-graph traversal recalls the correct
    alternatives significantly better than dense search or random (+0.25 recall vs random,
    95% CI[+0.115,+0.398]). Use after locating a seed repo (e.g. via search_repos_semantic).
    """
    try:
        response = await client.get(f"/graph/subgraph/{repo_name}")
        response.raise_for_status()
        grouped = seed_neighbors_by_type(response.json(), repo_name)
        alts: list = []
        seen: set = set()
        for et in ("ALTERNATIVE_TO", "SIMILAR_TO"):
            for n in grouped.get(et, []):
                if n["name"] not in seen:
                    seen.add(n["name"])
                    alts.append({**n, "relation": et})
        return json.dumps({"repo": repo_name, "alternatives": alts[:limit]}, indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"API error {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        return json.dumps({"error": f"Request failed: {str(e)}"})


async def explore_ecosystem(client: httpx.AsyncClient, repo_name: str) -> str:
    """Explore a repo's ecosystem via typed knowledge-graph edges: alternatives, what it
    depends on, what extends it, and compatible tools. Lets an agent reason over
    relationships instead of flat keyword search."""
    try:
        response = await client.get(f"/graph/subgraph/{repo_name}")
        response.raise_for_status()
        g = seed_neighbors_by_type(response.json(), repo_name)
        return json.dumps({
            "repo": repo_name,
            "alternatives": (g.get("ALTERNATIVE_TO", []) + g.get("SIMILAR_TO", []))[:8],
            "depends_on": g.get("DEPENDS_ON", [])[:8],
            "extended_by": g.get("EXTENDS", [])[:8],
            "compatible_with": g.get("COMPATIBLE_WITH", [])[:8],
        }, indent=2)
    except httpx.HTTPStatusError as e:
        return json.dumps({"error": f"API error {e.response.status_code}: {e.response.text}"})
    except Exception as e:
        return json.dumps({"error": f"Request failed: {str(e)}"})
