# MCP HTTP Bridge — Deploy Auth Verification (2026-04-27)

**Ticket:** KAN-MCP-DEPLOY-VERIFY (round 1, parallel-tasks-board.md)
**Verifier:** autonomous agent (Opus 4.7 [1M])
**Subject:** PR [#14](https://github.com/perditioinc/reporium-mcp/pull/14) commit `d5b6d11`
"fix(deploy): replace ID-token smoke test with auth-enforcement probe" — landed 2026-04-23 20:32 PDT.

## TL;DR

**Verdict: PASS.** Cloud Run `--no-allow-unauthenticated` is enforced at the network edge,
the application's `X-MCP-Token` check is enforced behind it, and the deploy workflow's
post-deploy smoke test reads the load-bearing signal (unauthenticated probe → 403). The
legacy "mint ID token, expect 200" pattern is gone (replaced with "no auth, expect 401/403").

## Deploy state

| Field | Value |
|---|---|
| Service | `reporium-mcp-http` |
| Region | `us-central1` |
| Project | `perditio-platform` |
| URL | `https://reporium-mcp-http-wypbzj5gpa-uc.a.run.app` |
| Image | `us-central1-docker.pkg.dev/perditio-platform/cloud-run-source-deploy/reporium-mcp-http:d5b6d11...` |
| Revision flags | `--no-allow-unauthenticated`, runtime SA `reporium-mcp-runtime@`, `MCP_SHARED_SECRET` from secret `reporium-mcp-token:latest` |
| Last deploy run | [`24870785032`](https://github.com/perditioinc/reporium-mcp/actions/runs/24870785032) — success — 2026-04-24 03:34:20 UTC, smoke probe HTTP 403 (PASS) |

## Workflow probe (read from `.github/workflows/deploy-http.yml` lines 84-104)

```bash
SERVICE_URL="${{ steps.deploy.outputs.url }}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --http1.1 \
  "${SERVICE_URL}/health" --max-time 30)
case "$HTTP_CODE" in
  401|403) echo "MCP HTTP bridge reachable and auth enforced." ;;
  200)     exit 1 ;;   # auth not enforced — fail
  *)       exit 1 ;;   # 404/5xx — broken revision
esac
```

The probe deliberately makes an **unauthenticated** request and pass-conditions on 401/403.
Comment on lines 78-83 documents the rationale: `roles/run.invoker` on the service is bound
only to `workato-mcp@` (caller SA), and the deploy SA cannot mint identity tokens — so an
"authenticated probe" path was rejected as it would require broadening IAM bindings.

## Live probes (run from operator host 2026-04-27)

### 1. Unauthenticated GET /health — load-bearing data point

```
$ curl -s -o /dev/null -w "%{http_code}" --http1.1 \
    "https://reporium-mcp-http-wypbzj5gpa-uc.a.run.app/health" --max-time 30
403
```

Body: canonical Google `<title>403 Forbidden</title> ... Your client does not have
permission to get URL <code>/health</code> from this server.` HTML page (Cloud Run
frontend 403, NOT the FastAPI app — confirms request never reached Python).

**Result: matches workflow expectation.**

### 2. Unauthenticated GET / and POST /ask

```
GET  /     → 403 (Cloud Run frontend)
POST /ask  → 403 (Cloud Run frontend)
GET  /docs → 403 (Cloud Run frontend)
```

All Cloud Run-rejected. Auth enforcement is global (not just `/health`).

### 3. Authenticated probe — best-effort with operator user-account ID token

`gcloud auth print-identity-token --audiences=<URL>` errored "Invalid account type for
--audiences. Requires valid service account." (same constraint that motivated PR #14).
Plain `gcloud auth print-identity-token` returned a Google-issued JWT for
`team@perditio.com` (audience = gcloud client ID `32555940559.apps.googleusercontent.com`).

```
$ TOKEN=$(gcloud auth print-identity-token)
$ curl -s -H "Authorization: Bearer $TOKEN" \
    "https://reporium-mcp-http-wypbzj5gpa-uc.a.run.app/health"
HTTP 200
{"status":"ok","service":"reporium-mcp-http"}
```

`/health` returns 200 once Cloud Run frontend admits the request — the FastAPI handler
(`http_server.py:102-104`) has no `_require_token` dependency, by design (intended for
public probes/uptime checks once past the IAM gate).

```
$ curl -s -X POST -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    "https://reporium-mcp-http-wypbzj5gpa-uc.a.run.app/ask" \
    -d '{"question":"smoke test"}'
HTTP 401
{"detail":"Invalid or missing X-MCP-Token"}
```

Application-layer auth fires. With a deliberately wrong `X-MCP-Token` header added,
same response (401, same body). The dependency `_require_token` (`http_server.py:83-87`)
constant-time-compares against `MCP_SHARED_SECRET` (loaded from secret `reporium-mcp-token`).

**Result: two-layer defense works as designed. The bridge is unreachable without (a) IAM
permission to invoke the Cloud Run service AND (b) the MCP shared secret.**

## Cross-check — does the workflow probe match observed live behavior?

| Aspect | Workflow expectation | Live observation | Match? |
|---|---|---|---|
| Unauthenticated `/health` HTTP code | 401 or 403 | 403 | yes |
| Body shape | not asserted | Cloud Run frontend HTML 403 | yes |
| Pass when 200 | fail | (200 only with valid IAM token, unauthed → 403) | yes |
| Probe layer reached | Cloud Run edge | Cloud Run edge (Python never invoked) | yes |
| Legacy ID-token-presence check | removed | (workflow has no `print-identity-token` step) | yes |

## Verdict — PASS

1. Cloud Run frontend rejects all unauthenticated requests with 403 (not 200, not 5xx).
2. Application layer enforces `X-MCP-Token` on every non-health route.
3. The deploy workflow's smoke step (`Smoke test reachability and auth enforcement`)
   correctly pass-conditions on 401/403 from `/health` unauthenticated, fails on 200,
   and fails on 404/5xx — i.e., it tests the right signal.
4. The legacy "mint identity token, expect 200" pattern that Codex P2 #6 identified as
   broken since 2026-04-15 is gone. Replaced by an unauthenticated negative-path probe
   that requires zero IAM broadening.
5. Memory entry `mcp-deploy-auth (Codex P2 #6)` can be marked **CLOSED**.

## Residual notes (non-blocking)

- **Application-layer auth on `/health`:** intentional gap — `_require_token` is omitted
  so health probes from outside the MCP-token-holder set still work once IAM admits them.
  Acceptable because Cloud Run frontend is the actual gatekeeper, and `/health` reveals
  no sensitive state. Documented at `http_server.py:102-104`.
- **No automated authenticated probe in CI:** by design, per PR #14 commit message — adding
  one would require granting `roles/iam.serviceAccountTokenCreator` to the deploy SA, which
  expands attack surface. The unauthenticated probe is sufficient because 401/403 from
  Cloud Run is gameable only by removing `--no-allow-unauthenticated`, which the workflow
  itself declares (line 74) — so the diff would be visible in any malicious PR.
- **Workato caller path:** not exercised in this verification. `workato-mcp@` SA's last
  successful invocation should be confirmed separately by reading
  reporium-mcp's Cloud Run logs for a recent `audience: workato-mcp@` request. Out of
  scope for this ticket.

## References

- PR #14: https://github.com/perditioinc/reporium-mcp/pull/14
- Commit: `d5b6d1150ce645d421bb13161994952839bc73b4`
- Deploy workflow: `.github/workflows/deploy-http.yml`
- App entrypoint: `http_server.py`
- Successful post-fix run: actions/runs/24870785032
- Memory: `project_ask_sprint1_apr22.md` (Codex P2 #6 — mcp-deploy-auth)
