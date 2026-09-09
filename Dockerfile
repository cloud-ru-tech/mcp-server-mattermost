# uv is pinned (a build tool must be deterministic); the base image floats
# (it must be fresh). The previous single-stage build inverted both roles by
# using ghcr.io/astral-sh/uv:python3.12-bookworm-slim as the base — that image
# is itself python:3.12-slim-bookworm plus the uv binary, and it stopped being
# rebuilt, so it shipped 26 fixable CRITICAL/HIGH OS advisories and blocked the
# 0.6.0 release at the Trivy gate.
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.9.30 /uv /uvx /usr/local/bin/

WORKDIR /app

# Optimization flags
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_PROGRESS=1

# Install dependencies first (cached unless pyproject.toml/uv.lock change)
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Install the project itself (re-runs only when src/ changes).
# --no-editable copies the package into site-packages instead of leaving a .pth
# pointing at /app/src, which the runtime stage does not carry.
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable


# Both stages share the same base, so the interpreter the venv was built
# against is byte-for-byte the one that runs it.
FROM python:3.12-slim-bookworm AS runtime

# Pick up Debian security updates published after the base image was last
# rebuilt. This is a RUN with no file inputs, so BuildKit would serve it from
# cache for as long as the base digest holds — exactly the case it exists for.
# The scan job passes `no-cache-filters: runtime` to force it; see
# .github/workflows/docker-publish.yml. Being in its own stage, re-running it
# never invalidates the uv sync layers.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Create non-root user for security. `-m` also creates /home/mcp, the WORKDIR
# below. No `chown -R /app` afterwards: it would rewrite every file in the venv
# and duplicate the whole ~100 MB tree into a second layer.
RUN useradd -m -u 1000 mcp

# Only the virtualenv ships; uv, uvx and the build cache stay in the builder.
# Left root-owned: nothing writes into it at runtime — UV_COMPILE_BYTECODE
# precompiled the .pyc in the builder against this same path — so the code the
# server executes is immutable to the account it runs as.
COPY --from=builder /app/.venv /app/.venv

USER mcp

# A relative `destination_dir` in download_file resolves against the cwd, so the
# cwd has to be writable by the runtime user. /app is deliberately not (see
# above), which leaves the user's home.
WORKDIR /home/mcp

# Default port for HTTP mode
EXPOSE 8000

# Health check for HTTP mode only
# In stdio mode, healthcheck will fail after start-period (this is expected)
# Use --no-healthcheck flag when running stdio mode in orchestration
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default: stdio mode. Override with MCP_TRANSPORT=http
CMD ["/app/.venv/bin/mcp-server-mattermost"]
