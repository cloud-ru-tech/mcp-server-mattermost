# uv is pinned (a build tool must be deterministic); the base image floats (it
# must be fresh). Basing the image on a uv image inverts both roles.
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
# --no-editable: the runtime stage carries no src/ for a .pth to point at.
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable


# Same base as the builder, so the venv runs on the interpreter it was built
# against.
FROM python:3.12-slim-bookworm AS runtime

# Debian updates published after the base image was last rebuilt. A RUN with no
# file inputs, so BuildKit caches it while the base digest holds — the scan job
# forces it with `no-cache-filters: runtime`.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Non-root user; `-m` creates /home/mcp, the WORKDIR below. Never `chown -R
# /app` here — it rewrites every file in the venv into a second ~100 MB layer.
RUN useradd -m -u 1000 mcp

# Root-owned: nothing writes into the venv at runtime (the .pyc are precompiled
# in the builder against this same path), so the code the server executes is
# immutable to the account it runs as.
COPY --from=builder /app/.venv /app/.venv

USER mcp

# Relative paths resolve against the cwd, and /app is deliberately not writable.
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
