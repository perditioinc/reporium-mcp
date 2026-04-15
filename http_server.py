"""
http_server.py — FastAPI HTTP bridge for the Reporium MCP tool suite.

Exposes all 18 MCP tools as REST endpoints so Workato and other HTTP
clients can call them without the stdio MCP transport.

Auth: X-MCP-Token header (required on all non-health endpoints).
Rate: 60 requests/minute per IP (slowapi).

Env vars:
    REPORIUM_API_URL   — upstream reporium-api base URL
    REPORIUM_APP_TOKEN — X-App-Token forwarded to reporium-api
    MCP_API_TOKEN      — required bearer token for this server
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from tools.search import search_repos, search_repos_semantic
from tools.repos import get_repo, find_similar_repos, get_repo_quality
from tools.taxonomy import list_taxonomy_dimensions, list_taxonomy_values, get_repos_by_taxonomy
from tools.intelligence import (
    ask_portfolio,
    get_portfolio_gaps,
    get_ai_trends,
    get_portfolio_insights,
    get_cross_dimension_stats,
)
from tools.quality import get_quality_signals, list_taxonomy_gaps
from tools.graph import list_categories, get_repos_by_category, get_knowledge_graph

REPORIUM_API_URL = os.environ.get("REPORIUM_API_URL", "").rstrip("/")
REPORIUM_APP_TOKEN = os.environ.get("REPORIUM_APP_TOKEN", "")
MCP_API_TOKEN = os.environ.get("MCP_API_TOKEN", "")

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Reporium MCP HTTP Bridge",
    description="REST adapter for the Reporium MCP tool suite. Authenticate with X-MCP-Token.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_mcp_key_header = APIKeyHeader(name="X-MCP-Token", auto_error=False)


def _get_client() -> httpx.AsyncClient:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if REPORIUM_APP_TOKEN:
        headers["X-App-Token"] = REPORIUM_APP_TOKEN
    return httpx.AsyncClient(base_url=REPORIUM_API_URL, headers=headers, timeout=30.0)


async def _require_token(token: str = Depends(_mcp_key_header)) -> None:
    if not MCP_API_TOKEN:
        raise HTTPException(status_code=500, detail="Server misconfiguration: MCP_API_TOKEN not set")
    if token != MCP_API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing X-MCP-Token")


def _parse(raw: str) -> Any:
    """Parse JSON string returned by tool functions into a dict/list."""
    try:
        return json.loads(raw)
    except Exception:
        return {"result": raw}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok", "service": "reporium-mcp-http"}


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    query: str
    limit: int = 10


@app.post("/search", dependencies=[Depends(_require_token)])
@limiter.limit("60/minute")
async def search(request: Request, body: SearchRequest):
    async with _get_client() as client:
        return _parse(await search_repos(client, body.query, body.limit))


@app.post("/search/semantic", dependencies=[Depends(_require_token)])
@limiter.limit("60/minute")
async def search_semantic(request: Request, body: SearchRequest):
    async with _get_client() as client:
        return _parse(await search_repos_semantic(client, body.query, body.limit))


# ---------------------------------------------------------------------------
# Repos  (name=owner/repo passed as query param to avoid path-param conflicts)
# ---------------------------------------------------------------------------

@app.get("/repos/detail", dependencies=[Depends(_require_token)])
@limiter.limit("60/minute")
async def get_repo_endpoint(request: Request, name: str):
    async with _get_client() as client:
        return _parse(await get_repo(client, name))


@app.get("/repos/similar", dependencies=[Depends(_require_token)])
@limiter.limit("60/minute")
async def similar_repos(request: Request, name: str, limit: int = 5):
    async with _get_client() as client:
        return _parse(await find_similar_repos(client, name, limit))


@app.get("/repos/quality", dependencies=[Depends(_require_token)])
@limiter.limit("60/minute")
async def repo_quality(request: Request, name: str):
    async with _get_client() as client:
        return _parse(await get_repo_quality(client, name))


@app.get("/repos/quality-signals", dependencies=[Depends(_require_token)])
@limiter.limit("60/minute")
async def quality_signals(request: Request, name: str):
    async with _get_client() as client:
        return _parse(await get_quality_signals(client, name))


# ---------------------------------------------------------------------------
# Taxonomy
# ---------------------------------------------------------------------------

# Note: /taxonomy/dimensions and /taxonomy/gaps use literal path segments and
# must be declared BEFORE the parameterised routes to avoid being swallowed.

@app.get("/taxonomy/dimensions", dependencies=[Depends(_require_token)])
@limiter.limit("60/minute")
async def taxonomy_dimensions(request: Request):
    async with _get_client() as client:
        return _parse(await list_taxonomy_dimensions(client))


@app.get("/taxonomy/gaps", dependencies=[Depends(_require_token)])
@limiter.limit("60/minute")
async def taxonomy_gaps(
    request: Request,
    dimension: Optional[str] = None,
    min_severity: str = "medium",
):
    async with _get_client() as client:
        return _parse(await list_taxonomy_gaps(client, dimension=dimension, min_severity=min_severity))


@app.get("/taxonomy/{dimension}/values", dependencies=[Depends(_require_token)])
@limiter.limit("60/minute")
async def taxonomy_values(request: Request, dimension: str):
    async with _get_client() as client:
        return _parse(await list_taxonomy_values(client, dimension))


@app.get("/taxonomy/{dimension}/{value}", dependencies=[Depends(_require_token)])
@limiter.limit("60/minute")
async def repos_by_taxonomy(request: Request, dimension: str, value: str, limit: int = 20):
    async with _get_client() as client:
        return _parse(await get_repos_by_taxonomy(client, dimension, value, limit))


# ---------------------------------------------------------------------------
# Intelligence / Ask
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str


@app.post("/ask", dependencies=[Depends(_require_token)])
@limiter.limit("30/minute")
async def ask(request: Request, body: AskRequest):
    async with _get_client() as client:
        return _parse(await ask_portfolio(client, body.question))


@app.get("/gaps", dependencies=[Depends(_require_token)])
@limiter.limit("60/minute")
async def portfolio_gaps(request: Request):
    async with _get_client() as client:
        return _parse(await get_portfolio_gaps(client))


@app.get("/trends", dependencies=[Depends(_require_token)])
@limiter.limit("60/minute")
async def ai_trends(request: Request):
    async with _get_client() as client:
        return _parse(await get_ai_trends(client))


@app.get("/insights", dependencies=[Depends(_require_token)])
@limiter.limit("60/minute")
async def portfolio_insights(request: Request):
    async with _get_client() as client:
        return _parse(await get_portfolio_insights(client))


@app.get("/analytics/cross-dimension", dependencies=[Depends(_require_token)])
@limiter.limit("60/minute")
async def cross_dimension(request: Request, dim1: str, dim2: str, limit: int = 10):
    async with _get_client() as client:
        return _parse(await get_cross_dimension_stats(client, dim1, dim2, limit))


# ---------------------------------------------------------------------------
# Categories / Graph
# ---------------------------------------------------------------------------

@app.get("/categories", dependencies=[Depends(_require_token)])
@limiter.limit("60/minute")
async def categories(request: Request):
    async with _get_client() as client:
        return _parse(await list_categories(client))


@app.get("/categories/{category}/repos", dependencies=[Depends(_require_token)])
@limiter.limit("60/minute")
async def repos_by_category(request: Request, category: str, limit: int = 20):
    async with _get_client() as client:
        return _parse(await get_repos_by_category(client, category, limit))


@app.get("/graph/edges", dependencies=[Depends(_require_token)])
@limiter.limit("60/minute")
async def graph_edges(
    request: Request,
    edge_type: Optional[str] = None,
    limit: int = 50,
):
    async with _get_client() as client:
        return _parse(await get_knowledge_graph(client, edge_type=edge_type, limit=limit))
