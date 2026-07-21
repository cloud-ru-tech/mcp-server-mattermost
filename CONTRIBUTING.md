# Contributing to mcp-server-mattermost

Thank you for your interest in contributing!

## Development Setup

1. **Clone the repository:**

   ```bash
   git clone https://github.com/cloud-ru-tech/mcp-server-mattermost.git
   cd mcp-server-mattermost
   ```

2. **Install dependencies with uv:**
  
```bash
   uv sync --dev
   ```

## Running Tests

```bash
# Unit tests
uv run pytest

# Integration tests (requires Mattermost server or Docker)
uv run pytest tests/integration
```

## Code Style

This project uses strict code quality standards:

- **Formatter:** ruff format (120 character line length)
- **Linter:** ruff check (with most rules enabled)
- **Type checker:** mypy (strict mode)

Before submitting a PR, run:

```bash
uv run ruff format src tests
uv run ruff check src tests
uv run mypy src
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Ensure tests pass and linters are happy
5. Commit with a descriptive message
6. Push to your fork
7. Open a Pull Request

## Commit Messages

Use clear, descriptive commit messages:

- `feat: add support for custom emoji reactions`
- `fix: handle rate limit errors gracefully`
- `docs: update installation instructions`
- `test: add tests for file upload`
- `refactor: simplify channel listing logic`

## Dependency Updates (Dependabot)

Dependencies are kept current by [Dependabot](https://docs.github.com/en/code-security/dependabot),
configured in `.github/dependabot.yml`. It tracks four package ecosystems, each
checked **weekly** (Monday):

- **Python** (`pyproject.toml` + `uv.lock`)
- **GitHub Actions** (`.github/workflows/`)
- **Docker** base image (`Dockerfile`)
- **Docs toolchain** (`docs/requirements.txt`, used by ReadTheDocs)

A **cooldown** delays PRs until a release has "aged" (Python: patch 3 days, minor
7 days, major 14 days; Actions/Docker/docs: 3 days), so routine PRs arrive less often
than weekly and only for releases that have settled. Cooldown does **not** apply
to security updates — those are raised immediately.

### How PRs are grouped

| Update | Behavior |
| --- | --- |
| Python patch + minor | Combined into a single grouped PR (`python-minor-patch`) |
| Python major | One separate PR per dependency |
| GitHub Actions | Combined into one grouped PR |
| Docker base image | Separate PR |
| Docs toolchain (pip) | Separate PR |
| Security update | Separate, prioritized PR (never grouped) |

### How PRs are handled

All Dependabot PRs run the full CI (unit tests on Python 3.10–3.13, `ruff`,
`mypy`, Trivy SCA, integration tests) and are **merged manually** by a maintainer
after CI is green — there is no auto-merge.

- **Patch / minor (grouped):** confirm CI is green, skim the changelogs, merge.
- **Major:** review the migration guide and breaking changes, update code if
  needed, confirm full CI, then merge.
- **Security:** review with priority, confirm CI, merge promptly, and release a
  fixed version.

### Unmerged PRs

Dependabot does **not** create duplicates on the next weekly run. It updates the
existing open PR in place — bumping a grouped PR to include newly available
patches, moving a PR to a newer version if one is released, or rebasing after
`main` moves. Once an ecosystem reaches its open-PR limit (Python 5, Actions 3,
Docker 3, docs 2), no new PRs are opened until some are merged or closed. **Do not push
commits into a Dependabot PR branch** unless you intend to take it over —
manual edits stop Dependabot from auto-updating that PR.

### Library compatibility

This package is published to PyPI with intentionally broad version ranges (e.g.
`fastmcp>=3.4,<4`). Do **not** raise a dependency's minimum version without a
concrete reason — it forces downstream users to upgrade. Treat any PR that lifts
a lower bound as potentially breaking, and note the reason in the changelog.

## Questions?

Open an issue if you have questions or need help getting started.
