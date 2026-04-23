# reporium-mcp — Workload Identity Federation deploy setup

**Date:** 2026-04-22
**Author:** Claude (autonomous session follow-up on Codex P2 #6)
**Status:** GCP side executed; repo side in draft PR.

## Background

`.github/workflows/deploy-http.yml` has been failing on every push to main since
2026-04-15 because `secrets.GCP_SA_KEY` is empty. Rather than re-generate a
long-lived JSON key (brittle, rotates on a schedule, leak risk), we migrate to
Workload Identity Federation: GitHub Actions mints a short-lived OIDC token,
GCP exchanges it for a federated access token, no secret in the repo or in
GitHub Actions.

## What was set up on the GCP side

All commands run against project `perditio-platform` (`573778300586`).

### 1. OIDC provider inside the existing `github-pool`

```
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --workload-identity-pool=github-pool \
  --location=global \
  --project=perditio-platform \
  --display-name="GitHub Actions OIDC" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository_owner == 'perditioinc'"
```

Attribute condition `repository_owner == 'perditioinc'` ensures only OIDC
tokens coming from perditioinc-org repos can ever be exchanged through this
provider — a stolen token from some other GitHub org cannot use it.

Resource name:

```
projects/573778300586/locations/global/workloadIdentityPools/github-pool/providers/github-provider
```

### 2. Deploy-specific runtime SA

```
gcloud iam service-accounts create reporium-mcp-deploy \
  --project=perditio-platform \
  --display-name="Reporium MCP deploy (GitHub Actions via WIF)" \
  --description="Used by perditioinc/reporium-mcp deploy-http.yml to deploy reporium-mcp-http Cloud Run service via Workload Identity Federation"
```

Email: `reporium-mcp-deploy@perditio-platform.iam.gserviceaccount.com`

### 3. Project-level roles on the deploy SA

| Role | Why |
|---|---|
| `roles/run.admin` | Create/update Cloud Run revisions |
| `roles/cloudbuild.builds.editor` | Source-deploy triggers a Cloud Build |
| `roles/storage.admin` | Cloud Build uploads source to gcs-source bucket |
| `roles/artifactregistry.writer` | Push built container image |
| `roles/logging.logWriter` | Stream build + deploy logs |

### 4. actAs on the Cloud Build compute SA

Source-deploy runs as the default compute SA; the deploy SA needs
`iam.serviceAccountUser` on it.

```
gcloud iam service-accounts add-iam-policy-binding 573778300586-compute@developer.gserviceaccount.com \
  --member="serviceAccount:reporium-mcp-deploy@perditio-platform.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser" \
  --project=perditio-platform
```

### 5. WIF impersonation binding (the money step)

Allow the federated identity from the `perditioinc/reporium-mcp` repo (and ONLY
that repo) to impersonate the deploy SA:

```
gcloud iam service-accounts add-iam-policy-binding \
  reporium-mcp-deploy@perditio-platform.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/573778300586/locations/global/workloadIdentityPools/github-pool/attribute.repository/perditioinc/reporium-mcp" \
  --project=perditio-platform
```

Note the `attribute.repository/perditioinc/reporium-mcp` subject — this is
repo-scoped, so if we later want to reuse `github-pool` + `github-provider` for
other repos (recommended), we bind each repo's principalSet to its own deploy
SA. One pool + one provider + N deploy SAs is the standard pattern.

## What's in the repo-side PR

Changes to `.github/workflows/deploy-http.yml`:

1. Add `permissions: id-token: write` (required for OIDC minting)
2. Replace `credentials_json: ${{ secrets.GCP_SA_KEY }}` with:
   ```yaml
   workload_identity_provider: projects/573778300586/locations/global/workloadIdentityPools/github-pool/providers/github-provider
   service_account: reporium-mcp-deploy@perditio-platform.iam.gserviceaccount.com
   ```

No other changes to the workflow. `deploy-cloudrun@v2` step unchanged — it
picks up the federated credential automatically.

## Cleanup after merge

Once the first WIF-authenticated deploy succeeds, delete the orphaned GitHub
secret to close the attack surface:

```
gh secret delete GCP_SA_KEY --repo perditioinc/reporium-mcp
```

## Verification plan

After merging this PR:

1. Any commit to `main` touching one of the workflow's paths (http_server.py,
   tools/**, requirements*.txt, Dockerfile.http, deploy-http.yml) should now
   succeed.
2. Or manually: `gh workflow run deploy-http.yml --repo perditioinc/reporium-mcp`
3. Expected: Cloud Run revision updated, smoke test `/health` → 200.

If the first run fails, the most likely causes (in order):
- Missing role — expand the role list above.
- Attribute condition too tight — the `repository_owner == 'perditioinc'`
  filter was verified during setup, but if GitHub ever changes OIDC claim
  shape, it might not match. In that case: `gcloud iam workload-identity-pools providers update-oidc github-provider --location=global --workload-identity-pool=github-pool --attribute-condition=...`

## Why this is better than rotating GCP_SA_KEY

- **No long-lived credential in the repo.** OIDC tokens are minted per-run,
  expire in ≤10 minutes, and can never leak persistently.
- **No secret rotation burden.** Service-account keys have a 90-day effective
  rotation lifetime in practice; WIF has none — the trust relationship is in
  IAM, not in a file.
- **Tighter blast radius.** The attribute condition + repo-scoped principalSet
  mean only commits pushed to `perditioinc/reporium-mcp` can impersonate —
  stolen PATs and replay attacks from other repos are not enough.
- **Aligns with Codex P2 recommendation (2026-04-22) and Google's own guidance** —
  `credentials_json` is no longer the recommended path.
