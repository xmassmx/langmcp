"""Unit tests for MCP Apps inspector registration."""

from __future__ import annotations

import json

import pytest

from langmcp.apps.inspector import (
    INSPECTOR_URI,
    apps_enabled,
    build_inspector_payload,
    load_inspector_html,
)
from langmcp.profiles import ProfileManager
from langmcp.server import create_mcp


def test_inspector_html_bundle_exists():
    html = load_inspector_html()
    assert "<!DOCTYPE html>" in html.lower() or "<html" in html.lower()
    assert "LangMCP" in html


def test_build_inspector_payload_health(sample_config, sqlite_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(sqlite_path))
    from langmcp.tools.context import ToolContext

    ctx = ToolContext(ProfileManager(config_path=sample_config))
    payload = build_inspector_payload(ctx, "health")
    assert payload["view"] == "health"
    assert payload["read_only"] is True
    assert "profiles" in payload["seed"]
    assert "health_checks" in payload["seed"]


def test_build_inspector_payload_threads(sample_config, sqlite_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(sqlite_path))
    from langmcp.tools.context import ToolContext

    ctx = ToolContext(ProfileManager(config_path=sample_config))
    payload = build_inspector_payload(ctx, "threads")
    assert payload["view"] == "threads"
    assert "threads" in payload["seed"]


def test_build_inspector_payload_thread_requires_thread_id(sample_config, sqlite_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(sqlite_path))
    from langmcp.tools.context import ToolContext

    ctx = ToolContext(ProfileManager(config_path=sample_config))
    payload = build_inspector_payload(ctx, "thread")
    assert payload["view"] == "thread"
    assert any("thread_id is required" in error for error in payload["errors"])


def test_apps_enabled_env_toggle(monkeypatch):
    monkeypatch.delenv("LANGMCP_APPS_ENABLED", raising=False)
    assert apps_enabled() is True
    monkeypatch.setenv("LANGMCP_APPS_ENABLED", "false")
    assert apps_enabled() is False
    monkeypatch.setenv("LANGMCP_APPS_ENABLED", "1")
    assert apps_enabled() is True


@pytest.mark.asyncio
async def test_mcp_registers_inspector_surface(sample_config, sqlite_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(sqlite_path))
    mcp = create_mcp(ProfileManager(config_path=sample_config))

    tools = await mcp.list_tools()
    tool_names = {t.name for t in tools}
    assert "show_inspector" in tool_names
    assert "__ui_list_threads" in tool_names
    assert "__ui_health_check" in tool_names
    assert "__ui_get_checkpoint" in tool_names
    assert "__ui_compare_checkpoints" in tool_names
    assert "__ui_analyze_memory_gaps" in tool_names

    show = next(t for t in tools if t.name == "show_inspector")
    assert show.meta is not None
    assert show.meta.get("ui", {}).get("resourceUri") == INSPECTOR_URI

    resources = await mcp.list_resources()
    assert any(str(r.uri) == INSPECTOR_URI for r in resources)

    contents = await mcp.read_resource(INSPECTOR_URI)
    assert contents[0].mime_type == "text/html;profile=mcp-app"
    assert "LangMCP" in contents[0].content


@pytest.mark.asyncio
async def test_mcp_apps_can_be_disabled(sample_config, sqlite_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(sqlite_path))
    monkeypatch.setenv("LANGMCP_APPS_ENABLED", "false")
    mcp = create_mcp(ProfileManager(config_path=sample_config))

    tools = await mcp.list_tools()
    tool_names = {t.name for t in tools}
    assert "health_check" in tool_names
    assert "show_inspector" not in tool_names
    assert "__ui_list_threads" not in tool_names

    resources = await mcp.list_resources()
    assert all(str(r.uri) != INSPECTOR_URI for r in resources)


@pytest.mark.asyncio
async def test_show_inspector_tool_returns_seed(sample_config, sqlite_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(sqlite_path))
    mcp = create_mcp(ProfileManager(config_path=sample_config))

    result = await mcp.call_tool("show_inspector", {"view": "health"})
    if isinstance(result, dict):
        payload = result
    else:
        text = next(c.text for c in result if hasattr(c, "text"))
        payload = json.loads(text)

    assert payload["view"] == "health"
    assert payload["read_only"] is True
    assert "seed" in payload
