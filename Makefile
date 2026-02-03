# Makefile
.PHONY: help lint format test test-cov clean install

# Default target
help:
	@echo "Available targets:"
	@echo "  make install   - Install dependencies"
	@echo "  make lint      - Run linting (ruff + mypy)"
	@echo "  make format    - Format code"
	@echo "  make test      - Run tests"
	@echo "  make test-cov  - Run tests with coverage report"
	@echo "  make clean     - Remove build artifacts"

install:
	uv sync --all-extras

lint:
	uv run ruff check src tests
	uv run mypy src

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

test:
	uv run pytest

test-cov:
	uv run pytest --cov-report=html --cov-report=term-missing

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
