# LangMCP Inspector (MCP App)

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

## Dev

Use an MCP Apps-capable host (Claude, VS Code Copilot, or `ext-apps` basic-host) with `show_inspector` after rebuilding.

Set `LANGMCP_APPS_ENABLED=false` to disable registration of `show_inspector`,
`ui://langmcp/inspector.html`, and app-only `__ui_*` tools while leaving normal
LangMCP tools available.

## Dummy Data Preview

Launch browser-only mock screens without a live MCP host:

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
