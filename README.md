# LangMCP

**Read-only MCP server for inspecting LangGraph checkpoints, thread state, and long-term memory.**

LangMCP helps you answer the debugging question that traces do not always answer:

> What is actually saved in my LangGraph persistence layer right now?

It is not a generic SQL MCP. It uses LangGraph-native checkpointer and store APIs,
connects through named profiles, and keeps database credentials out of tool
arguments.

## Why LangMCP

When a stateful agent behaves strangely, the problem is often not only the prompt.
It might be the checkpoint it resumed from, the user ID in configurable state, the
store namespace used for memory, or an oversized message history.

LangMCP gives MCP clients such as Cursor and Claude Desktop a safe inspection
surface for those questions.

| LangMCP | Not LangMCP |
|---------|-------------|
| Read-only inspection of LangGraph persistence | Arbitrary SQL execution |
| Profile-based connections | Raw DSNs in model-facing arguments |
| Tools, resources, and prompts for debugging state | A replacement for LangSmith or LangGraph Studio |
| Local stdio MCP server for development | LangGraph Agent Server API |

Use LangSmith for traces, LangGraph Studio for visual graph workflows, and
LangMCP when you want an assistant in your editor to inspect persisted state
through a narrow read-only interface.

## Features

- Profile-based config with environment variable expansion.
- Read-only enforcement in v0.1.
- Secret redaction in health checks and error output.
- PostgreSQL, SQLite, and Redis checkpointer inspection.
- PostgreSQL `PostgresStore` long-term memory inspection.
- MCP tools for threads, checkpoints, store data, and analysis.
- MCP resources for stable readable state URIs.
- MCP prompts for repeatable debugging workflows.
- Pagination and truncation for large responses.

## Installation

```bash
uv pip install "langmcp[all]"
```

Or run without installing:

```bash
uvx "langmcp[all]" --version
```

LangMCP supports Python 3.11 and 3.12. The repository includes a
`.python-version` file set to Python 3.12.

## Configuration

Copy the example config and environment files:

```bash
cp examples/langmcp.example.toml langmcp.toml
cp .env.example .env
```

Set a read-only database URI in `.env`:

```dotenv
POSTGRES_URI=postgresql://READONLY_USER:READONLY_PASSWORD@HOST:5432/DB_NAME
LANGMCP_READ_ONLY=true
```

LangMCP loads `.env` automatically when present. Existing shell environment
variables take precedence.

Example `langmcp.toml`:

```toml
[defaults]
profile = "dev"
read_only = true
max_response_chars = 25000

[profiles.dev]
checkpointer = "${POSTGRES_URI}"
store = "${POSTGRES_URI}"

[profiles.local_sqlite]
checkpointer = "sqlite:///./.langgraph/checkpoints.db"

[profiles.local_redis]
checkpointer = "redis://localhost:6379/0"
```

Environment overrides:

- `LANGMCP_CONFIG`
- `LANGMCP_PROFILE`
- `LANGMCP_READ_ONLY`
- `POSTGRES_URI`
- `LANGMCP_CHECKPOINTER_URI`
- `LANGMCP_STORE_URI`

## Verify Setup

Run:

```bash
langmcp doctor --config ./langmcp.toml
```

The doctor command checks connectivity, backend types, setup status, package
versions, and redacts sensitive URI fields.

## Cursor Setup

See [examples/cursor-mcp.json](examples/cursor-mcp.json).

Minimal shape:

```json
{
  "mcpServers": {
    "langmcp": {
      "command": "uvx",
      "args": ["langmcp[all]", "serve", "--config", "<ABSOLUTE_PATH_TO_LANGMCP_TOML>"],
      "env": {
        "LANGMCP_READ_ONLY": "true",
        "POSTGRES_URI": "postgresql://READONLY_USER:READONLY_PASSWORD@HOST:5432/DB_NAME"
      }
    }
  }
}
```

Start the server directly:

```bash
langmcp serve --config ./langmcp.toml
```

## Example Assistant Prompts

Once connected through MCP, ask your assistant:

```text
Use LangMCP to summarize thread THREAD_ID and check whether user memory exists for USER_ID.
```

```text
Compare checkpoint CHECKPOINT_A and CHECKPOINT_B for thread THREAD_ID. Tell me what changed.
```

```text
Analyze whether thread THREAD_ID is carrying too much context.
```

```text
Investigate a possible memory gap for thread THREAD_ID and user USER_ID.
```

## MCP Tools

All tools accept optional `profile` unless noted. Responses include `profile`,
`truncated`, and pagination fields where applicable.

| Tool | Description |
|------|-------------|
| `health_check` | Connectivity, backend types, redacted URIs |
| `list_profiles` | Profile names and backend types |
| `list_threads` | Discover thread IDs |
| `get_thread_state` | Latest or specific checkpoint state |
| `list_checkpoint_history` | Paginated checkpoint list |
| `get_checkpoint` | Full snapshot for one checkpoint |
| `compare_checkpoints` | Diff values and message count delta |
| `summarize_thread` | Transcript-style summary |
| `analyze_context_window` | Token estimate and size warnings |
| `analyze_memory_gaps` | Store versus thread user ID hints |
| `list_namespaces` | Store namespace tuples |
| `search_store` | Search under namespace prefix |
| `get_store_item` | Full store value by key |
| `summarize_user_memory` | Grouped keys under user prefix |

## MCP Resources

Resources expose readable state through stable MCP URIs.

| Resource URI | Description |
|--------------|-------------|
| `langmcp://profiles` | Configured profiles and active profile |
| `langmcp://profiles/{profile}/health` | Connectivity and setup status |
| `langmcp://profiles/{profile}/threads` | Discovered thread IDs |
| `langmcp://profiles/{profile}/threads/{thread_id}/state` | Latest thread state |
| `langmcp://profiles/{profile}/threads/{thread_id}/summary` | Transcript-style thread summary |
| `langmcp://profiles/{profile}/threads/{thread_id}/checkpoints` | Recent checkpoint history |
| `langmcp://profiles/{profile}/threads/{thread_id}/checkpoints/{checkpoint_id}` | Full checkpoint snapshot |
| `langmcp://profiles/{profile}/threads/{thread_id}/context-analysis` | Context-window analysis |
| `langmcp://profiles/{profile}/store/namespaces` | Long-term memory namespaces |
| `langmcp://profiles/{profile}/store/items/{namespace}/{key}` | One store item |
| `langmcp://profiles/{profile}/users/{user_id}/memory-summary` | User memory summary |

For multi-part namespaces, prefer the `get_store_item` tool if your MCP client
treats `/` as a path separator inside resource parameters.

## MCP Prompts

Prompts package repeatable investigations.

| Prompt | Description |
|--------|-------------|
| `debug_thread` | Diagnose one thread from summary, checkpoints, context analysis, and memory hints |
| `investigate_memory_gap` | Check whether thread state and long-term memory are aligned |
| `compare_thread_checkpoints` | Explain behavioral differences between two checkpoints |
| `inspect_user_memory` | Summarize and sanity-check long-term memory for one user |

## Backend Matrix

| Backend | Checkpointer | Store in v0.1 |
|---------|--------------|---------------|
| PostgreSQL | Full | Full through `PostgresStore` |
| SQLite | Full | Not supported |
| Redis | Full | Not supported |

## Security

1. Tools accept profile names, not raw DSNs.
2. `read_only=true` is enforced in v0.1.
3. Use a read-only PostgreSQL user for shared environments.
4. Passwords are redacted in `health_check` and CLI output.
5. Redis thread discovery uses `SCAN` with limits. Avoid broad scans on very large instances.
6. Commit `examples/langmcp.example.toml` and `.env.example`, not real `langmcp.toml` or `.env` files.

## Development

```bash
uv pip install -e ".[all,dev]"
ruff check .
pytest tests/unit -v
```

Integration tests use local Docker services:

```bash
docker compose -f docker-compose.test.yml up -d
POSTGRES_URI=postgresql://langgraph:langgraph@localhost:5442/langgraph \
  REDIS_URI=redis://localhost:6379/0 \
  pytest tests/integration -v -m integration
```

Use the local test values from `docker-compose.test.yml`. They are for Docker
integration tests only.

## Roadmap

- LangGraph Agent Server adapter.
- HTTP transport with team auth.
- Vector store inspection tools.
- Carefully scoped write workflows such as `update_thread_state` and `resume_thread`.

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

Good first issue ideas:

- Add examples for a specific LangGraph persistence backend.
- Improve error messages for unsupported store backends.
- Add a resource or prompt test for an edge case.

## License

MIT. See [LICENSE](LICENSE).
