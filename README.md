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

`reporium-mcp` is the MCP server for the Reporium platform. It turns the live portfolio into a tool surface that agents can query directly from Claude Code and other MCP-aware clients.

## Why MCP?

MCP makes the portfolio AI-native instead of screen-native.

Without MCP, an agent has to infer state from documentation or ask a human to look things up. With MCP, the agent can query the live portfolio directly:

- search for repos by keyword or semantics
- inspect a repo in detail
- browse taxonomy dimensions and values
- answer portfolio questions in natural language
- surface portfolio gaps and trend signals as part of an execution loop

That means portfolio intelligence becomes a first-class tool in agent workflows instead of a manual reference step.

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
REPORIUM_API_URL=https://your-reporium-api-url
REPORIUM_API_KEY=your-api-key-here
```

`REPORIUM_API_KEY` is optional if the target API is publicly reachable for the endpoints you use.

## Adding To Claude Code

```bash
claude mcp add reporium -- python /path/to/reporium-mcp/mcp_server.py
```

Replace `/path/to/reporium-mcp/` with the absolute path where you cloned this repo.

## Tool Surface

This server exposes 10 tools.

| Tool | What it does | Core parameters |
|------|--------------|-----------------|
| `search_repos` | Keyword search over repo names, descriptions, and other indexed text fields | `query`, `limit` |
| `search_repos_semantic` | Embedding-based semantic repo search with similarity scores | `query`, `limit` |
| `get_repo` | Full repo detail including taxonomy, skills, categories, commits, and metadata | `name` |
| `find_similar_repos` | Finds repos similar to a target repo by reusing its summary as a semantic query | `repo_name`, `limit` |
| `list_taxonomy_dimensions` | Lists active taxonomy dimensions with repo coverage counts | none |
| `list_taxonomy_values` | Lists available values for a specific taxonomy dimension | `dimension` |
| `get_repos_by_taxonomy` | Returns repos matching a taxonomy dimension/value pair | `dimension`, `value`, `limit` |
| `ask_portfolio` | Sends a natural-language portfolio question to the Reporium intelligence layer | `question` |
| `get_portfolio_gaps` | Returns portfolio gap analysis for under-covered areas | none |
| `get_ai_trends` | Returns trend-oriented signals from the current portfolio snapshot | none |

Supported taxonomy dimensions include:

- `skill_area`
- `industry`
- `use_case`
- `modality`
- `ai_trend`
- `deployment_context`

## Example Questions

Once the MCP server is installed in Claude Code, you can ask:

- "What repos do we have for healthcare NLP?"
- "Find me production-ready RAG frameworks in the library"
- "Show me repos similar to langchain"
- "List all taxonomy dimensions and their most common values"
- "What are the current portfolio gaps?"
- "What AI trends are rising in the portfolio?"
- "Which repos cover deployment context for on-device inference?"

## Relationship To The Rest Of Reporium

- `reporium-api` is the live data and intelligence backend
- `reporium` is the human-facing portfolio UI
- `reporium-mcp` is the agent-facing tool layer

All three should describe the same portfolio, just through different interfaces.
