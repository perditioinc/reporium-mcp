# reporium-mcp
<!-- perditio-badges-start -->
[![Tests](https://github.com/perditioinc/reporium-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/perditioinc/reporium-mcp/actions/workflows/test.yml)
![Last Commit](https://img.shields.io/github/last-commit/perditioinc/reporium-mcp)
![License](https://img.shields.io/github/license/perditioinc/reporium-mcp)
![python](https://img.shields.io/badge/python-3.11%2B-3776ab)
![suite](https://img.shields.io/badge/suite-Reporium-6e40c9)
![mcp](https://img.shields.io/badge/MCP-Claude%20Code-6e40c9)
![tools](https://img.shields.io/badge/tools-18-blue)
<!-- perditio-badges-end -->

`reporium-mcp` is the MCP server for the [Reporium](https://www.reporium.com) AI development tool library. It gives Claude and other MCP-aware AI agents direct access to 1,500+ curated AI repos — search, taxonomy, portfolio intelligence, knowledge graph, and quality signals.

## Why MCP?

Without MCP, an agent has to infer portfolio state from documentation or ask a human to look things up. With MCP, Claude can query the live library directly:

- Search for repos by keyword or semantic similarity
- Inspect any repo in full detail (taxonomy, skills, quality signals, recent commits)
- Browse and filter by taxonomy dimensions (skill area, industry, use case, AI trend…)
- Ask natural-language portfolio questions ("what are the best production RAG frameworks?")
- Find similar repos, surface portfolio gaps, and check AI trend coverage
- Explore the knowledge graph (alternatives, dependencies, compatible tools)
- Browse repos by the 21 canonical AI categories
- Check quality signals for individual repos

That makes portfolio intelligence a first-class tool in agent workflows instead of a manual research step.

---

## Quick Start (Claude Code)

### 1. Prerequisites

- Python 3.11+
- `pip` or `uv`

### 2. Clone and install

```bash
git clone https://github.com/perditioinc/reporium-mcp.git
cd reporium-mcp
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env   # create from template
```

Edit `.env`:

```env
# Required: URL of the Reporium API
REPORIUM_API_URL=https://reporium-api-573778300586.us-central1.run.app

# Optional: app token forwarded as X-App-Token for rate-limited or private endpoints
REPORIUM_APP_TOKEN=your-app-token-here
```

> The public Reporium API does not require a key for read-only operations.

### 4. Register with Claude Code

**Option A — Claude Code CLI:**

```bash
claude mcp add reporium -- python /absolute/path/to/reporium-mcp/mcp_server.py
```

**Option B — Edit `.claude.json` directly:**

Find your `.claude.json` file (usually `~/.claude.json` or `C:\Users\<name>\.claude.json`) and add the server under the project's `mcpServers` key:

```json
{
  "projects": {
    "/path/to/your/project": {
      "mcpServers": {
        "reporium": {
          "type": "stdio",
          "command": "python",
          "args": ["/absolute/path/to/reporium-mcp/mcp_server.py"],
          "env": {
            "REPORIUM_API_URL": "https://reporium-api-573778300586.us-central1.run.app",
            "REPORIUM_APP_TOKEN": "your-app-token-here"
          }
        }
      }
    }
  }
}
```

> **Windows users:** Use the full Python path, e.g. `C:/Python313/python` or `C:/Users/<name>/AppData/Local/Programs/Python/Python313/python.exe`. Forward slashes work on Windows in JSON.

### 5. Restart Claude Code and verify

After restarting, Claude Code will list available tools. Try:

> "Use the reporium MCP to search for RAG frameworks"

---

## Tool Reference (18 tools)

### Search

| Tool | Description | Parameters |
|------|-------------|------------|
| `search_repos` | Keyword search over names, descriptions, and summaries | `query`, `limit` |
| `search_repos_semantic` | Embedding-based semantic search with similarity scores | `query`, `limit` |

### Repo Detail

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_repo` | Full repo detail — taxonomy, skills, quality, commits | `name` |
| `find_similar_repos` | Find repos similar to a given repo by semantic similarity | `repo_name`, `limit` |
| `get_repo_quality` | Quality signals: has_tests, has_ci, velocity, overall score | `name` |
| `get_quality_signals` | Raw quality_signals dict for a repo | `repo_name` |

### Taxonomy

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_taxonomy_dimensions` | List all active taxonomy dimensions with repo counts | — |
| `list_taxonomy_values` | List values for a dimension, sorted by repo count | `dimension` |
| `get_repos_by_taxonomy` | Get repos by taxonomy dimension + value | `dimension`, `value`, `limit` |
| `list_taxonomy_gaps` | Underrepresented taxonomy values (gap analysis) | `dimension`, `min_severity` |

Supported dimensions: `skill_area`, `industry`, `use_case`, `modality`, `ai_trend`, `deployment_context`

### Portfolio Intelligence

| Tool | Description | Parameters |
|------|-------------|------------|
| `ask_portfolio` | Natural-language question against the full library | `question` |
| `get_portfolio_gaps` | Gap analysis — which areas have insufficient coverage | — |
| `get_ai_trends` | Trending AI topics in the library by repo count | — |
| `get_portfolio_insights` | Rising gaps, stale repos, velocity leaders, near-duplicates | — |
| `get_cross_dimension_stats` | Repo counts at the intersection of two dimensions | `dim1`, `dim2`, `limit` |

### Knowledge Graph

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_categories` | List the 21 canonical primary category IDs and labels | — |
| `get_repos_by_category` | Get repos by primary category | `category`, `limit` |
| `get_knowledge_graph` | Edges between repos: ALTERNATIVE_TO, COMPATIBLE_WITH, DEPENDS_ON, SIMILAR_TO, EXTENDS | `edge_type`, `limit` |

---

## Example Prompts

Once installed, ask Claude things like:

```
Search the Reporium library for production-ready RAG frameworks
```
```
What AI repos do we have for healthcare NLP use cases?
```
```
Find repos similar to langchain/langchain
```
```
What are the current portfolio gaps in skill_area coverage?
```
```
What AI trends are best represented in the library right now?
```
```
Show me repos in the ai-agents category
```
```
Get the knowledge graph edges of type ALTERNATIVE_TO
```
```
Check the quality signals for vllm-project/vllm
```
```
What's missing from our MLOps coverage?
```

---

## Architecture

```
Claude Code / MCP Client
       │  stdio
       ▼
 mcp_server.py          ← MCP protocol handler (18 tools)
       │
       ▼
 tools/
   search.py            ← search_repos, search_repos_semantic
   repos.py             ← get_repo, find_similar_repos, get_repo_quality
   taxonomy.py          ← list/get taxonomy tools
   intelligence.py      ← ask_portfolio, gaps, trends, insights
   quality.py           ← get_quality_signals, list_taxonomy_gaps
   graph.py             ← list_categories, get_repos_by_category, get_knowledge_graph
       │
       ▼ HTTP
 Reporium API (FastAPI on Cloud Run)
       │
       ▼
 Neon PostgreSQL + pgvector
```

---

## Relationship to the Reporium Suite

| Repo | Role |
|------|------|
| `reporium-api` | Live data + intelligence backend (FastAPI, Cloud Run) |
| `reporium` | Human-facing portfolio UI (Next.js, Vercel) |
| `reporium-mcp` | Agent-facing tool layer (MCP server, stdio) |
| `reporium-db` | Nightly sync pipeline (GitHub → PostgreSQL) |

All describe the same 1,500+ repo portfolio through different interfaces.

---

## Development

```bash
# Run tests
python -m pytest tests/ -v

# Test against a local API
REPORIUM_API_URL=http://localhost:8000 python mcp_server.py
```

## Contributing

PRs welcome. Open an issue first for large changes.
