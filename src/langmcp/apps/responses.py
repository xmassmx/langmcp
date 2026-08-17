"""MCP App tool result helpers — short LLM text + full structuredContent for the iframe."""

from __future__ import annotations

from typing import Any

from mcp.types import CallToolResult, TextContent

INSPECTOR_SCHEMA_VERSION = 1


def app_tool_result(
    payload: dict[str, Any],
    *,
    summary: str,
    is_error: bool = False,
) -> CallToolResult:
    """Return a tool result with a concise model-visible summary and full structured payload."""
    return CallToolResult(
        content=[TextContent(type="text", text=summary)],
        structuredContent=payload,
        isError=is_error,
    )


def inspector_open_summary(view: str, profile: str, *, thread_id: str | None = None) -> str:
    """One-line summary when opening the LangMCP Inspector MCP App."""
    if view == "thread" and thread_id:
        return (
            f"Opened LangMCP Inspector (thread debugger, profile {profile}, "
            f"thread {thread_id}). Use the embedded UI."
        )
    return f"Opened LangMCP Inspector ({view} view, profile {profile}). Use the embedded UI."


def threads_list_summary(count: int, profile: str, *, truncated: bool = False) -> str:
    """One-line summary when listing threads with the MCP App UI."""
    suffix = " (truncated)" if truncated else ""
    noun = "thread" if count == 1 else "threads"
    return f"Listed {count} {noun} for profile {profile}{suffix}. Use the embedded UI."
