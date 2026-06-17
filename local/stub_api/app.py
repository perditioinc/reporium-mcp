"""
Local-OSS stub of the Reporium API for the reporium-mcp $0 dev substrate.

This is NOT the production reporium-api. It is a tiny, offline, $0 FastAPI
service that serves the exact endpoints the MCP server's tools/* call, backed
by a static seed file (local/seed/repos.json). It lets a developer bring up the
MCP server locally and exercise all 18 tools end-to-end with NO cloud, NO
credentials, NO paid embedding API, and NO dependency on the live API.

Endpoints mirror the contract that tools/*.py expect:
  GET  /health
  GET  /search?q=&limit=
  GET  /search/semantic?q=&limit=
  GET  /repos/{name}
  GET  /repos?category=&limit=
  GET  /library/full
  GET  /taxonomy/dimensions
  GET  /taxonomy/{dimension}
  GET  /taxonomy/{dimension}/{value}/repos?limit=
  POST /ask
  GET  /gaps
  GET  /gaps/taxonomy
  GET  /insights
  GET  /analytics/cross-dimension?dim1=&dim2=&limit=
  GET  /graph/edges?edge_type=&limit=

"Semantic" search here is a deterministic keyword-overlap score, not a real
embedding model. That keeps the substrate $0 and offline while preserving the
response shape the MCP tools consume.
"""
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

SEED_PATH = Path(os.environ.get("SEED_PATH", "/seed/repos.json"))

app = FastAPI(title="reporium-api (local stub)", version="0.1.0")


def _load() -> dict:
    with SEED_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


DATA = _load()
REPOS = DATA["repos"]
EDGES = DATA["graph_edges"]
TAX_GAPS = DATA["taxonomy_gaps"]

DIMENSIONS = [
    "skill_area", "industry", "use_case",
    "modality", "ai_trend", "deployment_context",
]


def _find_repo(name: str):
    for repo in REPOS:
        if repo["name"] == name or repo["full_name"] == name:
            return repo
    return None


def _score(repo: dict, query: str) -> int:
    """Deterministic keyword-overlap score. $0, offline, no embeddings."""
    haystack = " ".join([
        repo.get("name", ""),
        repo.get("full_name", ""),
        repo.get("description", ""),
        repo.get("readme_summary", ""),
    ]).lower()
    tokens = {t for t in query.lower().split() if t}
    return sum(1 for t in tokens if t in haystack)


@app.get("/health")
def health():
    return {"status": "ok", "repos": len(REPOS), "source": "local-stub"}


@app.get("/search")
def search(q: str = Query(...), limit: int = 10):
    scored = sorted(
        ((_score(r, q), r) for r in REPOS),
        key=lambda x: x[0],
        reverse=True,
    )
    results = [r for s, r in scored if s > 0][:limit]
    if not results:
        results = REPOS[:limit]
    return results


@app.get("/search/semantic")
def search_semantic(q: str = Query(...), limit: int = 10):
    scored = sorted(
        ((_score(r, q), r) for r in REPOS),
        key=lambda x: x[0],
        reverse=True,
    )
    out = []
    for s, r in scored[:limit]:
        item = dict(r)
        item["similarity"] = round(min(1.0, 0.5 + s * 0.1), 3)
        out.append(item)
    return out


@app.get("/repos")
def repos_by_category(category: str | None = None, limit: int = 20):
    if category:
        matched = [r for r in REPOS if r.get("primary_category") == category]
    else:
        matched = list(REPOS)
    return matched[:limit]


@app.get("/library/full")
def library_full():
    return {"repos": REPOS}


@app.get("/repos/{name:path}")
def get_repo(name: str):
    repo = _find_repo(name)
    if repo is None:
        raise HTTPException(status_code=404, detail=f"Repo '{name}' not found")
    return repo


@app.get("/taxonomy/dimensions")
def taxonomy_dimensions():
    out = []
    for dim in DIMENSIONS:
        values = set()
        for r in REPOS:
            for v in r.get("taxonomy", {}).get(dim, []):
                values.add(v)
        out.append({"dimension": dim, "value_count": len(values), "repo_count": len(REPOS)})
    return out


@app.get("/taxonomy/{dimension}")
def taxonomy_values(dimension: str):
    if dimension not in DIMENSIONS:
        raise HTTPException(status_code=404, detail=f"Unknown dimension '{dimension}'")
    counts: dict[str, int] = {}
    for r in REPOS:
        for v in r.get("taxonomy", {}).get(dimension, []):
            counts[v] = counts.get(v, 0) + 1
    return sorted(
        [{"value": v, "repo_count": c} for v, c in counts.items()],
        key=lambda x: x["repo_count"],
        reverse=True,
    )


@app.get("/taxonomy/{dimension}/{value}/repos")
def taxonomy_repos(dimension: str, value: str, limit: int = 20):
    if dimension not in DIMENSIONS:
        raise HTTPException(status_code=404, detail=f"Unknown dimension '{dimension}'")
    matched = [
        r for r in REPOS
        if value.lower() in [str(v).lower() for v in r.get("taxonomy", {}).get(dimension, [])]
    ]
    return matched[:limit]


class AskBody(BaseModel):
    question: str


@app.post("/ask")
def ask(body: AskBody):
    return {
        "question": body.question,
        "answer": (
            f"[local-stub] Based on {len(REPOS)} seeded repos, the strongest coverage is in "
            "RAG and inference-serving. This is a local $0 stub answer, not a live LLM call."
        ),
        "source": "local-stub",
    }


@app.get("/gaps")
def gaps():
    return {"gaps": TAX_GAPS, "source": "local-stub"}


@app.get("/gaps/taxonomy")
def gaps_taxonomy():
    return TAX_GAPS


@app.get("/insights")
def insights():
    leaders = sorted(REPOS, key=lambda r: r["quality_signals"]["commit_velocity"], reverse=True)
    return {
        "velocity_leaders": [r["full_name"] for r in leaders[:3]],
        "rising_gaps": [g["value"] for g in TAX_GAPS if g["severity"] == "high"],
        "stale_repos": [r["full_name"] for r in REPOS if not r["quality_signals"]["is_active"]],
        "source": "local-stub",
    }


@app.get("/analytics/cross-dimension")
def cross_dimension(dim1: str, dim2: str, limit: int = 10):
    pairs: dict[tuple[str, str], int] = {}
    for r in REPOS:
        tax = r.get("taxonomy", {})
        for v1 in tax.get(dim1, []):
            for v2 in tax.get(dim2, []):
                pairs[(v1, v2)] = pairs.get((v1, v2), 0) + 1
    out = [
        {"dim1": dim1, "value1": k[0], "dim2": dim2, "value2": k[1], "count": c}
        for k, c in sorted(pairs.items(), key=lambda x: x[1], reverse=True)
    ]
    return {"pairs": out[:limit]}


@app.get("/graph/edges")
def graph_edges(edge_type: str | None = None, limit: int = 50):
    edges = EDGES
    if edge_type:
        edges = [e for e in edges if e["edge_type"] == edge_type]
    types = sorted({e["edge_type"] for e in EDGES})
    return {"total": len(edges), "edgeTypes": types, "edges": edges[:limit]}
