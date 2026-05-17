# LangMCP

**Development MCP server for LangGraph checkpoint and store inspection** — the local counterpart to LangSmith traces.

LangMCP is **not** a generic SQL MCP. It uses LangGraph-native checkpointer and store APIs so you can inspect threads, checkpoints, and long-term memory during development without exposing database credentials to the LLM.

## What it is / what it is not

| LangMCP | Not LangMCP |
|---------|-------------|
| Read-only inspection of LangGraph persistence | Arbitrary SQL queries |
| Profile-based connections (`dev`, `local_sqlite`) | Raw DSNs in tool arguments |
| stdio MCP for Cursor / Claude Desktop | LangGraph Agent Server API (v0.2) |

Companion: keep your existing **docs-langchain** MCP for documentation; use LangMCP to answer *"what's in my DB right now?"*

## Quickstart

```bash
# Install with all backends
uv pip install "langmcp[all]"

# Or run without installing
uvx "langmcp[all]" doctor --config examples/langmcp.example.toml
```

Copy `examples/langmcp.example.toml` to `langmcp.toml` (gitignored) and set your URIs.

### Cursor configuration

See [`examples/cursor-mcp.json`](examples/cursor-mcp.json).

```bash
langmcp serve --config /path/to/langmcp.toml
```

## Profile setup

```toml
[defaults]
profile = "dev"
read_only = true
max_response_chars = 25000

[profiles.dev]
checkpointer = "postgresql://${POSTGRES_URI}"
store = "postgresql://${POSTGRES_URI}"

[profiles.local_sqlite]
checkpointer = "sqlite:///./.langgraph/checkpoints.db"

[profiles.local_redis]
checkpointer = "redis://localhost:6379/0"
```

Environment overrides: `LANGMCP_CONFIG`, `LANGMCP_PROFILE`, `LANGMCP_READ_ONLY`, `POSTGRES_URI`, `LANGMCP_CHECKPOINTER_URI`, `LANGMCP_STORE_URI`.

Run `langmcp doctor` to verify connectivity and migrations.

## MCP tools (v0.1.0)

All tools accept optional `profile` (default from config). Responses include `profile`, `truncated`, and pagination fields when applicable.

| Tool | Description |
|------|-------------|
| `health_check` | Connectivity, backend types, redacted URIs |
| `list_profiles` | Profile names and backend types |
| `list_threads` | Discover thread IDs |
| `get_thread_state` | Latest or specific checkpoint state |
| `list_checkpoint_history` | Paginated checkpoint list |
| `get_checkpoint` | Full snapshot for one checkpoint |
| `compare_checkpoints` | Diff values + message count delta |
| `summarize_thread` | Transcript-style summary |
| `analyze_context_window` | Token estimate and size warnings |
| `analyze_memory_gaps` | Store vs thread user_id hints |
| `list_namespaces` | Store namespace tuples |
| `search_store` | Search under namespace prefix |
| `get_store_item` | Full store value by key |
| `summarize_user_memory` | Grouped keys under user prefix |

## Backend matrix

| Backend | Checkpointer | Store (v0.1) |
|---------|--------------|--------------|
| PostgreSQL | Full | Full (`PostgresStore`) |
| SQLite | Full | Not supported — configure Postgres for store tools |
| Redis | Full | Not supported — use Postgres for store |

## Security

1. Tools accept **profile names only** — never raw DSNs or passwords.
2. **read_only=true** is enforced in v0.1.
3. Use a **read-only PostgreSQL user** for inspection profiles.
4. Passwords are **redacted** in `health_check` and CLI output.
5. Redis thread discovery uses **SCAN** with limits — avoid on large production instances.
6. Commit `langmcp.example.toml`, not `langmcp.toml` with secrets.

## Development

```bash
docker compose -f docker-compose.test.yml up -d
uv pip install -e ".[all,dev]"
pytest tests/unit -v
POSTGRES_URI=postgresql://langgraph:langgraph@localhost:5442/langgraph \
  REDIS_URI=redis://localhost:6379/0 \
  pytest tests/integration -v
```

## Roadmap (v0.2)

- LangGraph Agent Server adapter (`LANGGRAPH_API_URL`)
- Write tools: `update_thread_state`, `resume_thread`
- HTTP transport + team auth
- Vector store inspection tools

## License

MIT
