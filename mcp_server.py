import asyncio
import os
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

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

load_dotenv()

REPORIUM_API_URL = os.environ.get("REPORIUM_API_URL", "").rstrip("/")
REPORIUM_API_KEY = os.environ.get("REPORIUM_API_KEY", "")

app = Server("reporium")


def get_client() -> httpx.AsyncClient:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if REPORIUM_API_KEY:
        headers["X-API-Key"] = REPORIUM_API_KEY
    return httpx.AsyncClient(base_url=REPORIUM_API_URL, headers=headers, timeout=30.0)


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_repos",
            description="Search the Reporium AI repo library using keyword/text matching. Returns repos matching the query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10).",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="search_repos_semantic",
            description="Search the Reporium AI repo library using semantic/vector similarity. Returns repos with similarity scores, ideal for conceptual or natural language queries like 'production-ready RAG frameworks' or 'healthcare NLP tools'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A natural language or conceptual query to find semantically similar repos.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10).",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_repo",
            description="Get full details for a specific repository by name, including taxonomy classifications, skills, categories, and recent commits.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The repository name (e.g., 'owner/repo' or just 'repo').",
                    },
                },
                "required": ["name"],
            },
        ),
        types.Tool(
            name="find_similar_repos",
            description="Find repositories similar to a given repo, using its readme summary for semantic similarity matching. Returns similar repos with similarity scores.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "description": "The name of the repository to find similar repos for.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of similar repos to return (default: 5).",
                        "default": 5,
                    },
                },
                "required": ["repo_name"],
            },
        ),
        types.Tool(
            name="list_taxonomy_dimensions",
            description="List all active taxonomy dimensions used to categorize repos in the library (e.g., skill_area, industry, use_case), along with their repo counts.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="list_taxonomy_values",
            description="List all values for a specific taxonomy dimension, sorted by repo count. Use this to explore what categories exist within a dimension like 'skill_area' or 'industry'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dimension": {
                        "type": "string",
                        "description": "The taxonomy dimension to list values for. Valid options: skill_area, industry, use_case, modality, ai_trend, deployment_context.",
                        "enum": ["skill_area", "industry", "use_case", "modality", "ai_trend", "deployment_context"],
                    },
                },
                "required": ["dimension"],
            },
        ),
        types.Tool(
            name="get_repos_by_taxonomy",
            description="Get repositories matching a specific taxonomy dimension and value. For example, dimension='industry' value='healthcare' returns all healthcare repos.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dimension": {
                        "type": "string",
                        "description": "The taxonomy dimension. Valid options: skill_area, industry, use_case, modality, ai_trend, deployment_context.",
                        "enum": ["skill_area", "industry", "use_case", "modality", "ai_trend", "deployment_context"],
                    },
                    "value": {
                        "type": "string",
                        "description": "The taxonomy value to filter by (e.g., 'nlp', 'healthcare', 'rag').",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of repos to return (default: 20).",
                        "default": 20,
                    },
                },
                "required": ["dimension", "value"],
            },
        ),
        types.Tool(
            name="ask_portfolio",
            description="Ask a natural language question about the entire repo library portfolio. The AI will analyze the library and answer questions like 'What are our strongest areas?', 'Do we have anything for real-time fraud detection?', or 'What's missing from our ML ops coverage?'",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "A natural language question about the repo library portfolio.",
                    },
                },
                "required": ["question"],
            },
        ),
        types.Tool(
            name="get_portfolio_gaps",
            description="Get a gap analysis of the repo library showing which skill areas, industries, or taxonomy categories have insufficient coverage. Useful for identifying what to add to the library.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="get_ai_trends",
            description="Get trending AI topics represented in the repo library, sorted by repo count and trending score. Shows what AI trends are best covered in the library.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="get_portfolio_insights",
            description="Get proactive portfolio intelligence signals: rising gaps, stale repos, velocity leaders, near-duplicate clusters.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="get_cross_dimension_stats",
            description="Get a breakdown of how many repos exist at the intersection of two taxonomy dimensions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dim1": {
                        "type": "string",
                        "description": "The first taxonomy dimension to analyze.",
                    },
                    "dim2": {
                        "type": "string",
                        "description": "The second taxonomy dimension to analyze.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of dimension-value pairs to return (default: 10).",
                        "default": 10,
                    },
                },
                "required": ["dim1", "dim2"],
            },
        ),
        types.Tool(
            name="get_repo_quality",
            description="Get quality signals for a repo: has_tests, has_ci, commit velocity, overall quality score.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The repository name (e.g., 'owner/repo' or just 'repo').",
                    },
                },
                "required": ["name"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    if not REPORIUM_API_URL:
        result = '{"error": "REPORIUM_API_URL environment variable is not set. Please configure it in your .env file."}'
        return [types.TextContent(type="text", text=result)]

    async with get_client() as client:
        if name == "search_repos":
            result = await search_repos(client, arguments["query"], arguments.get("limit", 10))
        elif name == "search_repos_semantic":
            result = await search_repos_semantic(client, arguments["query"], arguments.get("limit", 10))
        elif name == "get_repo":
            result = await get_repo(client, arguments["name"])
        elif name == "find_similar_repos":
            result = await find_similar_repos(client, arguments["repo_name"], arguments.get("limit", 5))
        elif name == "list_taxonomy_dimensions":
            result = await list_taxonomy_dimensions(client)
        elif name == "list_taxonomy_values":
            result = await list_taxonomy_values(client, arguments["dimension"])
        elif name == "get_repos_by_taxonomy":
            result = await get_repos_by_taxonomy(
                client, arguments["dimension"], arguments["value"], arguments.get("limit", 20)
            )
        elif name == "ask_portfolio":
            result = await ask_portfolio(client, arguments["question"])
        elif name == "get_portfolio_gaps":
            result = await get_portfolio_gaps(client)
        elif name == "get_ai_trends":
            result = await get_ai_trends(client)
        elif name == "get_portfolio_insights":
            result = await get_portfolio_insights(client)
        elif name == "get_cross_dimension_stats":
            result = await get_cross_dimension_stats(
                client,
                arguments["dim1"],
                arguments["dim2"],
                arguments.get("limit", 10),
            )
        elif name == "get_repo_quality":
            result = await get_repo_quality(client, arguments["name"])
        else:
            result = f'{{"error": "Unknown tool: {name}"}}'

    return [types.TextContent(type="text", text=result)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
