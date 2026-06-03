# Contributing to LangMCP

Thanks for considering a contribution. LangMCP is a small read-only MCP server for
inspecting LangGraph persistence, so the main priorities are safety, clarity, and
developer ergonomics.

## Good First Contributions

- Improve docs and examples.
- Add focused tests for existing tools, resources, or prompts.
- Add backend-specific edge case coverage.
- Improve error messages without exposing secrets.

## Development Setup

```bash
uv pip install -e ".[all,dev]"
pytest tests/unit -v
ruff check .
```

For integration tests, start the local test services first:

```bash
docker compose -f docker-compose.test.yml up -d
POSTGRES_URI=postgresql://langgraph:langgraph@localhost:5442/langgraph \
  REDIS_URI=redis://localhost:6379/0 \
  pytest tests/integration -v -m integration
```

Use the local test values from `docker-compose.test.yml`. They are for Docker
integration tests only. Do not commit real database credentials or a real
`langmcp.toml`.

## Branching

- **`develop`** — integration branch; open all feature and fix PRs here.
- **`main`** — production; merge from `develop` when releasing (not for day-to-day work).

```bash
git fetch origin
git switch develop
git pull
git switch -c feature/my-change
```

When opening a PR on GitHub, set the base branch to **`develop`**.

## Pull Request Guidelines

- Keep changes focused and explain the debugging workflow they support.
- Add or update tests for behavior changes.
- Update `CHANGELOG.md` under `## [Unreleased]` when changing `src/` or `tests/`.
- Keep the default surface read-only unless a future roadmap item explicitly
  introduces a write workflow.
- Do not log secrets, DSNs, or raw credentials.
- Run `ruff check .` and the relevant pytest suite before opening a PR.

## Reporting Issues

When reporting a bug, include:

- LangMCP version
- Python version
- backend type, such as PostgreSQL, SQLite, or Redis
- the tool/resource/prompt you used
- sanitized error output
- a minimal config shape with secrets removed
