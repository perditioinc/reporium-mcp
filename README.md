# reporium-mcp
<!-- perditio-badges-start -->
[![Tests](https://github.com/perditioinc/reporium-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/perditioinc/reporium-mcp/actions/workflows/test.yml)
![Last Commit](https://img.shields.io/github/last-commit/perditioinc/reporium-mcp)
![License](https://img.shields.io/github/license/perditioinc/reporium-mcp)
![python](https://img.shields.io/badge/python-3.11%2B-3776ab)
![suite](https://img.shields.io/badge/suite-Reporium-6e40c9)
![mcp](https://img.shields.io/badge/MCP-Claude%20Code-6e40c9)
![tools](https://img.shields.io/badge/tools-10-blue)
<!-- perditio-badges-end -->

An MCP (Model Context Protocol) server that makes your Reporium AI repo library queryable by Claude and other AI agents. Once installed, Claude Code can answer questions like "What repos do we have for healthcare NLP?", "Find me production-ready RAG frameworks", or "What are the gaps in our ML portfolio?" — all as live queries against your Reporium API, without leaving your conversation.

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```
REPORIUM_API_URL=https://your-reporium-api-url
REPORIUM_API_KEY=your-api-key-here   # optional, if your API requires auth
```

## Adding to Claude Code

```bash
claude mcp add reporium -- python /path/to/reporium-mcp/mcp_server.py
```

Replace `/path/to/reporium-mcp/` with the actual absolute path where you cloned this repo.

## Available Tools

### Search

| Tool | Description | Parameters |
|------|-------------|------------|
| `search_repos` | Keyword/text search across the library | `query` (required), `limit` (default: 10) |
| `search_repos_semantic` | Semantic/vector similarity search with scores | `query` (required), `limit` (default: 10) |

### Repository Details

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_repo` | Full repo detail: taxonomy, skills, categories, commits | `name` (required) |
| `find_similar_repos` | Find repos similar to a given repo using its summary | `repo_name` (required), `limit` (default: 5) |

### Taxonomy Browsing

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_taxonomy_dimensions` | All active dimensions with repo counts | none |
| `list_taxonomy_values` | All values for a dimension, sorted by repo count | `dimension` (required) |
| `get_repos_by_taxonomy` | Repos matching a dimension + value pair | `dimension` (required), `value` (required), `limit` (default: 20) |

Valid taxonomy dimensions: `skill_area`, `industry`, `use_case`, `modality`, `ai_trend`, `deployment_context`

### Portfolio Intelligence

| Tool | Description | Parameters |
|------|-------------|------------|
| `ask_portfolio` | Ask a natural language question about the whole library | `question` (required) |
| `get_portfolio_gaps` | Gap analysis: which areas have insufficient coverage | none |
| `get_ai_trends` | Trending AI topics in the library by repo count and score | none |

## Example Queries

Once the MCP server is installed in Claude Code, you can ask:

- "What repos do we have for healthcare NLP?"
- "Find me production-ready RAG frameworks in the library"
- "What's the most represented industry in our library?"
- "Show me all repos tagged with the ai_trend 'agents'"
- "What are the gaps in our machine learning portfolio?"
- "Find repos similar to langchain"
- "What trending AI topics are best covered in our library?"
- "Do we have anything for real-time fraud detection?"
- "List all skill areas and how many repos cover each"
