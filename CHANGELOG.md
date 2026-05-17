# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
