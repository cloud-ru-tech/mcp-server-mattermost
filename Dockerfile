FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Optimization flags
ENV UV_COMPILE_BYTECODE=1 \
    UV_NO_PROGRESS=1 \
    PYTHONUNBUFFERED=1

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies as root (cache in /root/.cache/uv)
# The .venv will be in /app and accessible to non-root user
RUN uv sync --frozen --no-dev

# Create non-root user for security
RUN useradd -m -u 1000 mcp && chown -R mcp:mcp /app
USER mcp

# Copy source code
COPY --chown=mcp:mcp src ./src

# Default port for HTTP mode
EXPOSE 8000

# Health check for HTTP mode only
# In stdio mode, healthcheck will fail after start-period (this is expected)
# Use --no-healthcheck flag when running stdio mode in orchestration
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default: stdio mode. Override with MCP_TRANSPORT=http
CMD ["uv", "run", "mcp-server-mattermost"]
