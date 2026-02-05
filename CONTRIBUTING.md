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

## Questions?

Open an issue if you have questions or need help getting started.
