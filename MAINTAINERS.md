# Maintainers Guide

Admin tasks for repository maintainers. These are GitHub **repository settings**
that cannot be committed as files; apply them via the GitHub UI or `gh` CLI
(requires admin permission on `cloud-ru-tech/mcp-server-mattermost`).

## Dependabot: required repository settings

The scheduled updates live in `.github/dependabot.yml`. The following must be
enabled once, in the repository settings, to complete the setup.

### 1. Security features

**UI:** Settings → Advanced Security (Code security) → enable:

- **Dependency graph** (on by default for public repos)
- **Dependabot alerts**
- **Dependabot security updates**

**CLI equivalent:**

```bash
# Dependabot alerts
gh api -X PUT repos/cloud-ru-tech/mcp-server-mattermost/vulnerability-alerts

# Dependabot security updates (automated security fix PRs)
gh api -X PUT repos/cloud-ru-tech/mcp-server-mattermost/automated-security-fixes
```

Security-update PRs are raised independently of the monthly schedule and are not
delayed by cooldown.

### 2. Branch protection on `main`

Dependabot PRs must not bypass CI. Require all checks and a Code Owner review
before merge.

**UI:** Settings → Branches → Add branch ruleset (or classic protection) for
`main`:

- Require a pull request before merging
- Require status checks to pass — select: `test (3.10)`, `test (3.11)`,
  `test (3.12)`, `test (3.13)`, `sca`, `integration-tests`
- Require branches to be up to date before merging
- Require review from Code Owners
- Do not allow direct pushes / bypassing

**CLI equivalent (classic branch protection):**

```bash
gh api -X PUT repos/cloud-ru-tech/mcp-server-mattermost/branches/main/protection \
  --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "test (3.10)",
      "test (3.11)",
      "test (3.12)",
      "test (3.13)",
      "sca",
      "integration-tests"
    ]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "require_code_owner_reviews": true,
    "required_approving_review_count": 1
  },
  "restrictions": null
}
JSON
```

> Check names come from the job names in `.github/workflows/ci.yml`
> (`test` matrix + `sca`) and `integration-tests.yml`. Confirm the exact
> strings on a real PR's checks list before locking them in — a typo makes a
> check "required" that never reports, blocking all merges.

### 3. Secrets — do not grant Dependabot production access

- Do **not** add any secrets under Settings → Secrets and variables →
  **Dependabot**. This project's workflows need none for PR validation.
- Dependabot PRs already run with a read-only `GITHUB_TOKEN` and have **no**
  access to Actions secrets — this is the correct, safe default.
- Publish workflows (`publish.yml`, `docker-publish.yml`) trigger only on
  `release: published`, and `publish-test.yml` only on manual
  `workflow_dispatch` — none of them ever run on a Dependabot PR.
- No workflow uses `pull_request_target`; keep it that way.

## Verifying the Dependabot config

After the config is merged to `main`:

1. Go to the repository's **Insights → Dependency graph → Dependabot** tab.
2. Each ecosystem (`uv`, `github-actions`, `docker`, `pip`) should be listed
   with a recent "last checked" time and **no config error**.
3. Use **"Check for updates"** to trigger a run on demand.
