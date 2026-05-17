# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Publish workflow: `langmcp doctor` smoke test fails on connectivity errors (no `|| true`)
- Health check and `doctor`: connectivity via read-only probes; `setup()` failures are warnings when reads succeed
- Sanitize exception messages in health/doctor output (strip URIs and passwords)
- Integration tests: assert seeded store key `theme`; default Redis URL `redis://localhost:6379/0`
- Config: `${DATABASE_URL}` falls back to `POSTGRES_URI` when unset
- Redis thread discovery: SCAN deadline; document `checkpoint:` key prefix
- CLI: remove unused import; avoid double profile config load on `serve --profile`
- Examples and `pyproject.toml` URLs aligned with README and repository

## [0.1.0] - 2026-05-17

### Added

- Initial release: read-only MCP server for LangGraph persistence inspection
- stdio transport via FastMCP (`mcp` 1.x)
- Profile-based configuration (`langmcp.toml`) with env expansion and secret redaction
- PostgreSQL checkpointer + PostgresStore adapters
- SQLite and Redis checkpointer adapters
- Thread discovery for Postgres, SQLite, and Redis
- 14 MCP tools: health, profiles, threads, checkpoints, store, and analysis
- CLI: `langmcp serve`, `langmcp doctor`
- Integration tests with Docker Compose (Postgres + Redis)
- CI (ruff + pytest) and PyPI publish workflow

### Security

- `read_only=true` enforced in v0.1
- No raw DSN parameters on MCP tools

[0.1.0]: https://github.com/langmcp/langmcp/releases/tag/v0.1.0
