# reporium-mcp Roadmap

## Current State (March 2026)

`reporium-mcp` is the agent-facing MCP server for the Reporium platform.

- The server currently exposes 15 tools backed by the live `reporium-api`
- Tool coverage includes keyword search, semantic search, repo detail lookup, similar repos, taxonomy browsing, portfolio Q&A, gaps, AI trends, proactive portfolio insights, cross-dimension analytics, and quality lookups
- The server is designed for Claude Code and other MCP-aware clients
- Configuration is intentionally small: API URL plus optional API key

## Tool Surface

The currently implemented tools are:

1. `search_repos`
2. `search_repos_semantic`
3. `get_repo`
4. `find_similar_repos`
5. `list_taxonomy_dimensions`
6. `list_taxonomy_values`
7. `get_repos_by_taxonomy`
8. `ask_portfolio`
9. `get_portfolio_gaps`
10. `get_ai_trends`
11. `get_portfolio_insights`
12. `get_cross_dimension_stats`
13. `get_repo_quality`
14. `get_quality_signals`
15. `list_taxonomy_gaps`

## Recent Platform Additions

- Portfolio insight and cross-dimension analytics tools
- Repo quality lookup tools
- Taxonomy gap inspection tools
- Documentation and environment-example cleanup for operator setup

## What Is Next

- Keep tool coverage aligned as the API grows
- Add deployment guidance for shared team environments if the MCP server moves beyond local execution
- Scale with the broader platform to 10K repos without changing the MCP contract
- Support safer public query flows by relying on upstream API rate limiting
- Keep commit-stat-derived tools current as downstream activity signals improve
