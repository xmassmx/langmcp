# LangMCP Inspector (MCP App)

> **Development status:** Experimental and unreleased. This app is available from
> the source branch only, is not part of PyPI `0.1.1`, and may change before release.

Bundled SPA for the in-chat LangMCP Inspector. The UI is intentionally focused on
the main workflow: **Health → Threads → Thread Debugger**. Checkpoint compare,
state inspection, context analysis, and memory diagnostics live inside the
Thread Debugger instead of becoming separate top-level apps.

## Build

```bash
cd apps/inspector
npm install
npm run build
```

Output is written to `src/langmcp/apps/inspector.html` and shipped inside the Python wheel.

After rebuilding, **reload the LangMCP MCP server** in your host so the updated bundle is served.

## Dev

### MCP protocol preview (recommended)

With dev dependencies installed:

```bash
pip install "langmcp[dev]"
fastmcp dev apps src/langmcp/server.py:dev_mcp
```

Opens a tool picker at `http://localhost:8080`, calls your server over MCP, and renders
`show_inspector` / `list_threads` in an AppBridge iframe with an MCP traffic inspector.

LangMCP uses `mcp.server.fastmcp` at runtime; the standalone `fastmcp` CLI is a **dev-only**
helper for local app debugging.

### Browser-only mock screens

Fast UI iteration without a live MCP host:

```bash
python scripts/preview_inspector_dummy.py --install
```

Open one screen only:

```bash
python scripts/preview_inspector_dummy.py --screen health
python scripts/preview_inspector_dummy.py --screen threads
python scripts/preview_inspector_dummy.py --screen thread
```

The preview uses `?mock=health`, `?mock=threads`, and `?mock=thread` query
parameters to bypass AppBridge and render deterministic dummy payloads.

### Watch rebuild

```bash
cd apps/inspector
npm run dev
```

## Production MCP Apps behavior

- **Entry tools** (`show_inspector`, `list_threads`) return a short text summary for the
  model and the full JSON payload in `structuredContent` for the iframe.
- **Backend tools** (`__ui_*`) are visible only inside the app (`visibility: ["app"]`).
- **Resource metadata** requests `clipboard` permission for copy buttons and disables the
  host border (`prefersBorder: false`) for a compact in-chat panel.
- **Host context**: when the MCP host provides theme or safe-area insets, the app follows
  the host instead of the manual sun/moon toggle.

Set `LANGMCP_APPS_ENABLED=false` to disable registration of `show_inspector`,
`ui://langmcp/inspector.html`, and app-only `__ui_*` tools while leaving normal
LangMCP tools available.
