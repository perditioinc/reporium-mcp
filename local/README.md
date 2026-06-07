# reporium-mcp — $0 local-OSS dev substrate

Run the Reporium MCP server **locally at $0** against an offline OSS stub of the
Reporium API. **Additive and local-only** — production, live cloud resources,
and the running deployment are untouched. **The MCP application code
(`mcp_server.py`, `tools/*`) is unchanged.**

This is the `reporium-mcp` slice of epic
[perditioinc/reporium-system-design#5](https://github.com/perditioinc/reporium-system-design/issues/5)
(card [#6](https://github.com/perditioinc/reporium-system-design/issues/6),
Local-OSS dev substrate). It mirrors the reporium-api substrate (PR #569) for
the MCP repo, and does **not** depend on it: the stub here is self-contained, so
you can develop and test the MCP server before the API substrate lands.

## Cloud -> OSS substitution

| Paid (prod) | $0 local substitute | Transparent how |
|---|---|---|
| reporium-api on Cloud Run | `stub_api/` — a tiny OSS FastAPI service serving the same endpoints from a seed file | `REPORIUM_API_URL` env points the unmodified MCP server at the stub. **No code change.** |
| Neon Postgres + pgvector (behind the API) | static seed (`seed/repos.json`) | the stub reads the seed; no DB needed for the MCP contract |
| Paid embeddings (semantic search) | deterministic keyword-overlap scoring in the stub | preserves the `/search/semantic` response shape, $0/offline |
| App token / Secret Manager | not required (public read endpoints) | never contacted |

No cloud credentials, secrets, or paid services are used or required.

## What this proves

The MCP server is a thin HTTP client over `REPORIUM_API_URL`. The stub serves
every endpoint `tools/*.py` call, so all **18 MCP tools** can be exercised
end-to-end locally:

`/search`, `/search/semantic`, `/repos/{name}`, `/repos`, `/library/full`,
`/taxonomy/dimensions`, `/taxonomy/{dim}`, `/taxonomy/{dim}/{value}/repos`,
`/ask`, `/gaps`, `/gaps/taxonomy`, `/insights`, `/analytics/cross-dimension`,
`/graph/edges`, `/health`.

## Usage

```bash
# from the repo root (passthrough) or from local/
make up        # build + start stub-api and mcp container, wait for healthy
make smoke     # full e2e: up -> health -> all 18 tools vs stub -> down
make seed      # show what the stub serves
make ps        # service status
make logs      # tail logs
make down      # stop + remove everything (incl. volumes)
```

`make smoke` is the gate: it brings the stack up, asserts the stub `/health`,
then runs `smoke/smoke.py` **inside the mcp container** (the real
`mcp_server.py` + `tools/*`) against the local stub, asserting every tool
returns data and not an error payload. It always tears down afterward.

## Point a real MCP client at the local stub

The stdio server has no network port; an MCP client launches it over stdio.
To run the server by hand against the local stub:

```bash
make up
REPORIUM_API_URL=http://localhost:8000 python ../mcp_server.py
```

## Scope

- `stub_api/` is **not** the production reporium-api. It is a local fixture for
  $0 offline development of the MCP server. It does not replace the live API in
  any deployed environment.
- The seed (`seed/repos.json`) is a small representative sample, not the live
  1,500+ repo library.
