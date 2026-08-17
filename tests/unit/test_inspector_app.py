"""Unit tests for MCP Apps inspector registration."""

from __future__ import annotations

import json

import pytest
from mcp.types import CallToolResult

from langmcp.apps.inspector import (
    INSPECTOR_URI,
    RESOURCE_UI_META,
    TOOL_UI_META,
    apps_enabled,
    build_inspector_payload,
    load_inspector_html,
)
from langmcp.apps.responses import INSPECTOR_SCHEMA_VERSION
from langmcp.profiles import ProfileManager
from langmcp.server import create_mcp


def _structured_payload(result) -> dict:
    if isinstance(result, CallToolResult):
        assert result.structuredContent is not None
        return result.structuredContent  # type: ignore[return-value]
    if isinstance(result, dict):
        return result
    if hasattr(result, "structuredContent") and result.structuredContent is not None:
        return result.structuredContent
    if isinstance(result, (list, tuple)):
        blocks = result[0] if result and isinstance(result[0], (list, tuple)) else result
        text = next(c.text for c in blocks if hasattr(c, "text"))
        return json.loads(text)
    text = next(c.text for c in result if hasattr(c, "text"))
    return json.loads(text)


def _summary_text(result) -> str:
    if isinstance(result, CallToolResult):
        return result.content[0].text if result.content else ""
    if hasattr(result, "content") and result.content:
        block = result.content[0]
        return block.text if hasattr(block, "text") else str(block)
    return ""


def test_inspector_html_bundle_exists():
    html = load_inspector_html()
    assert "<!DOCTYPE html>" in html.lower() or "<html" in html.lower()
    assert "LangMCP" in html


def test_build_inspector_payload_health(sample_config, sqlite_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(sqlite_path))
    from langmcp.tools.context import ToolContext

    ctx = ToolContext(ProfileManager(config_path=sample_config))
    payload = build_inspector_payload(ctx, "health")
    assert payload["schema_version"] == INSPECTOR_SCHEMA_VERSION
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
    assert any(
        (isinstance(error, dict) and "thread_id is required" in error.get("message", ""))
        or (isinstance(error, str) and "thread_id is required" in error)
        for error in payload["errors"]
    )


def test_apps_enabled_env_toggle(monkeypatch):
    monkeypatch.delenv("LANGMCP_APPS_ENABLED", raising=False)
    assert apps_enabled() is True
    monkeypatch.setenv("LANGMCP_APPS_ENABLED", "false")
    assert apps_enabled() is False
    monkeypatch.setenv("LANGMCP_APPS_ENABLED", "1")
    assert apps_enabled() is True


def test_tool_ui_meta_shape():
    ui = TOOL_UI_META["ui"]
    assert ui["resourceUri"] == INSPECTOR_URI
    assert ui["prefersBorder"] is False
    assert ui["visibility"] == ["model", "app"]


def test_resource_ui_meta_shape():
    ui = RESOURCE_UI_META["ui"]
    assert ui["prefersBorder"] is False
    assert ui["permissions"]["clipboard"] is True


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
    show_ui = show.meta.get("ui", {})
    assert show_ui.get("resourceUri") == INSPECTOR_URI
    assert show_ui.get("prefersBorder") is False

    list_threads = next(t for t in tools if t.name == "list_threads")
    assert list_threads.meta is not None
    assert list_threads.meta.get("ui", {}).get("resourceUri") == INSPECTOR_URI

    resources = await mcp.list_resources()
    inspector_resource = next(r for r in resources if str(r.uri) == INSPECTOR_URI)
    assert inspector_resource.meta is not None
    assert inspector_resource.meta.get("ui", {}).get("permissions", {}).get("clipboard") is True

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
async def test_show_inspector_returns_structured_result(sample_config, sqlite_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(sqlite_path))
    mcp = create_mcp(ProfileManager(config_path=sample_config))

    result = await mcp.call_tool("show_inspector", {"view": "health"})
    payload = _structured_payload(result)
    summary = _summary_text(result)

    assert payload["view"] == "health"
    assert payload["read_only"] is True
    assert payload["schema_version"] == INSPECTOR_SCHEMA_VERSION
    assert "seed" in payload
    assert summary
    assert "Opened LangMCP Inspector" in summary
    assert len(summary) < len(json.dumps(payload))


@pytest.mark.asyncio
async def test_list_threads_returns_structured_result_when_apps_enabled(
    sample_config, sqlite_path, monkeypatch
):
    monkeypatch.setenv("SQLITE_PATH", str(sqlite_path))
    mcp = create_mcp(ProfileManager(config_path=sample_config))

    result = await mcp.call_tool("list_threads", {})
    payload = _structured_payload(result)
    summary = _summary_text(result)

    assert "profile" in payload
    assert summary
    assert "Listed" in summary
    assert len(summary) < len(json.dumps(payload))


@pytest.mark.asyncio
async def test_list_threads_returns_plain_dict_when_apps_disabled(
    sample_config, sqlite_path, monkeypatch
):
    monkeypatch.setenv("SQLITE_PATH", str(sqlite_path))
    monkeypatch.setenv("LANGMCP_APPS_ENABLED", "false")
    mcp = create_mcp(ProfileManager(config_path=sample_config))

    result = await mcp.call_tool("list_threads", {})
    payload = _structured_payload(result)
    assert "profile" in payload
    summary = _summary_text(result)
    assert not summary or "Listed" not in summary
