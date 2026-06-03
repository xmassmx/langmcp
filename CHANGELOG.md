# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Backend connectivity helpers that apply PostgreSQL connection timeouts and classify unreachable persistence backends.
- Unit coverage for backend timeout handling and unreachable-backend health responses.

### Fixed

- Tool calls now return structured `backend_unreachable` errors instead of hanging on unavailable checkpoint or store backends.
- Connection failure messages redact sensitive backend details before returning them to MCP clients.

## [0.1.1] - 2026-05-27

### Fixed

- README/Cursor example: replace angle-bracket config path placeholder so PyPI renders JSON correctly
- Project metadata: point PyPI homepage and documentation links to the public GitHub README
- README: add package, CI, publish, and license badges

## [0.1.0] - 2026-05-27

### Added

- MCP resources for profiles, profile health, threads, checkpoints, store items, and user memory summaries
- MCP prompts for thread debugging, memory-gap investigation, checkpoint comparison, and user-memory inspection
- Launch docs: `.env.example`, `.python-version`, `CONTRIBUTING.md`, and a public-ready README

### Fixed

- CLI: add `--version` / `-V` (publish smoke test and standard UX)
- Health/doctor: skip `setup()` when `read_only=true` so probes do not mutate schemas
- CHANGELOG release link aligned with `pyproject.toml` repository URL
- README/CONTRIBUTING integration examples point to `docker-compose.test.yml` credentials
- README quick smoke command uses `--version` before config is required
- `.gitignore`: ignore `ARTICLE.md`; allow `.env.example`

- Publish workflow: `langmcp doctor` smoke test fails on connectivity errors (no `|| true`)
- Health check and `doctor`: connectivity via read-only probes; `setup()` failures are warnings when reads succeed
- Sanitize exception messages in health/doctor output (strip URIs and passwords)
- Integration tests: assert seeded store key `theme`; default Redis URL `redis://localhost:6379/0`
- Config: `${DATABASE_URL}` falls back to `POSTGRES_URI` when unset
- Redis thread discovery: SCAN deadline; document `checkpoint:` key prefix
- CLI: remove unused import; avoid double profile config load on `serve --profile`
- Examples and `pyproject.toml` URLs aligned with README and repository

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

[0.1.1]: https://github.com/xmassmx/langmcp/releases/tag/v0.1.1
[0.1.0]: https://github.com/xmassmx/langmcp/releases/tag/v0.1.0
