"""Helpers for registering iframe-only MCP App backend tools."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from mcp.server.fastmcp import FastMCP

F = TypeVar("F", bound=Callable[..., Any])


def make_ui_tool_decorator(mcp: FastMCP, meta: dict[str, Any]):
    """Return a decorator that registers a tool visible only inside the MCP App iframe."""

    def ui_tool(name: str) -> Callable[[F], F]:
        def decorator(fn: F) -> F:
            registered = mcp.tool(name=name, meta=meta)(fn)
            return registered  # type: ignore[return-value]

        return decorator

    return ui_tool
