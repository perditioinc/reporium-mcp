"""
End-to-end smoke for the reporium-mcp $0 local substrate.

Runs INSIDE the mcp container (built from the repo Dockerfile, so it has the
real mcp_server.py + tools/*). It:
  1. Imports mcp_server and asserts all 18 tools register (catches broken
     imports / tool wiring, same as the CI smoke).
  2. Opens an httpx client against the local stub API (REPORIUM_API_URL) and
     calls every tools/* function end-to-end, asserting each returns data and
     not an {"error": ...} payload.

Exit 0 = PASS, non-zero = FAIL. No cloud, no credentials, $0.
"""
import asyncio
import json
import os
import sys

import httpx

import mcp_server
from tools.search import search_repos, search_repos_semantic
from tools.repos import get_repo, find_similar_repos, get_repo_quality
from tools.taxonomy import (
    list_taxonomy_dimensions,
    list_taxonomy_values,
    get_repos_by_taxonomy,
)
from tools.intelligence import (
    ask_portfolio,
    get_portfolio_gaps,
    get_ai_trends,
    get_portfolio_insights,
    get_cross_dimension_stats,
)
from tools.quality import get_quality_signals, list_taxonomy_gaps
from tools.graph import list_categories, get_repos_by_category, get_knowledge_graph

API_URL = os.environ["REPORIUM_API_URL"].rstrip("/")

failures: list[str] = []


def check(label: str, raw: str, must_contain: str | None = None) -> None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        failures.append(f"{label}: not valid JSON")
        print(f"FAIL {label}: not JSON")
        return
    if isinstance(data, dict) and "error" in data:
        failures.append(f"{label}: {data['error']}")
        print(f"FAIL {label}: {data['error']}")
        return
    if must_contain and must_contain not in raw:
        failures.append(f"{label}: missing expected '{must_contain}'")
        print(f"FAIL {label}: missing '{must_contain}'")
        return
    print(f"PASS {label}")


async def main() -> int:
    # 1. Tool-registration smoke (mirrors CI).
    tools = await mcp_server.list_tools()
    assert mcp_server.app.name == "reporium", "server name mismatch"
    assert len(tools) == 18, f"expected 18 tools, got {len(tools)}"
    print(f"PASS tool-registration: 18 tools, server='reporium'")

    # 2. End-to-end against the local stub.
    async with httpx.AsyncClient(base_url=API_URL, timeout=15.0) as client:
        check("search_repos", await search_repos(client, "rag", 5), "llama_index")
        check("search_repos_semantic", await search_repos_semantic(client, "vector search", 5), "similarity")
        check("get_repo", await get_repo(client, "langchain"), "langchain")
        check("find_similar_repos", await find_similar_repos(client, "langchain", 3))
        check("get_repo_quality", await get_repo_quality(client, "vllm"), "quality_signals")
        check("get_quality_signals", await get_quality_signals(client, "vllm"), "overall_score")
        check("list_taxonomy_dimensions", await list_taxonomy_dimensions(client), "skill_area")
        check("list_taxonomy_values", await list_taxonomy_values(client, "industry"), "healthcare")
        check("get_repos_by_taxonomy", await get_repos_by_taxonomy(client, "industry", "healthcare", 5), "monai")
        check("ask_portfolio", await ask_portfolio(client, "what are our strongest areas?"), "answer")
        check("get_portfolio_gaps", await get_portfolio_gaps(client), "gaps")
        check("get_ai_trends", await get_ai_trends(client))
        check("get_portfolio_insights", await get_portfolio_insights(client), "velocity_leaders")
        check("get_cross_dimension_stats", await get_cross_dimension_stats(client, "skill_area", "industry", 5))
        check("list_taxonomy_gaps", await list_taxonomy_gaps(client, None, "low"), "gaps")
        check("list_categories", await list_categories(client), "ai-agents")
        check("get_repos_by_category", await get_repos_by_category(client, "rag-retrieval", 5), "llama_index")
        check("get_knowledge_graph", await get_knowledge_graph(client, "ALTERNATIVE_TO", 10), "edges")

    if failures:
        print(f"\nSMOKE FAIL: {len(failures)} failure(s)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nSMOKE PASS: all tools returned data against the local stub")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
