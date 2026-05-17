"""Unit tests for the advertised MCP server surface."""

from __future__ import annotations

import json

import pytest

from langmcp.profiles import ProfileManager
from langmcp.server import create_mcp


@pytest.mark.asyncio
async def test_mcp_registers_resources_and_prompts(sample_config, sqlite_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(sqlite_path))
    mcp = create_mcp(ProfileManager(config_path=sample_config))

    resources = await mcp.list_resources()
    templates = await mcp.list_resource_templates()
    prompts = await mcp.list_prompts()

    assert [str(resource.uri) for resource in resources] == ["langmcp://profiles"]
    assert {template.uriTemplate for template in templates} >= {
        "langmcp://profiles/{profile}/health",
        "langmcp://profiles/{profile}/threads",
        "langmcp://profiles/{profile}/threads/{thread_id}/state",
        "langmcp://profiles/{profile}/threads/{thread_id}/summary",
        "langmcp://profiles/{profile}/threads/{thread_id}/checkpoints",
        "langmcp://profiles/{profile}/threads/{thread_id}/checkpoints/{checkpoint_id}",
        "langmcp://profiles/{profile}/threads/{thread_id}/context-analysis",
        "langmcp://profiles/{profile}/store/namespaces",
        "langmcp://profiles/{profile}/store/items/{namespace}/{key}",
        "langmcp://profiles/{profile}/users/{user_id}/memory-summary",
    }
    assert {prompt.name for prompt in prompts} >= {
        "debug_thread",
        "investigate_memory_gap",
        "compare_thread_checkpoints",
        "inspect_user_memory",
    }


@pytest.mark.asyncio
async def test_profiles_resource_returns_json(sample_config, sqlite_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(sqlite_path))
    mcp = create_mcp(ProfileManager(config_path=sample_config))

    contents = await mcp.read_resource("langmcp://profiles")
    payload = json.loads(contents[0].content)

    assert contents[0].mime_type == "application/json"
    assert payload["active_profile"] == "test"
    assert payload["profiles"][0]["name"] == "test"


@pytest.mark.asyncio
async def test_debug_thread_prompt_renders_workflow(sample_config, sqlite_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(sqlite_path))
    mcp = create_mcp(ProfileManager(config_path=sample_config))

    prompt = await mcp.get_prompt(
        "debug_thread",
        {
            "thread_id": "thread-1",
            "profile": "test",
            "user_id": "user-1",
            "model_hint": "gpt-4.1",
        },
    )
    text = prompt.messages[0].content.text

    assert "thread-1" in text
    assert "profile `test`" in text
    assert "analyze_memory_gaps" in text
    assert "user_id `user-1`" in text
