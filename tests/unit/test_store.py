"""Unit tests for long-term memory store tools."""

from __future__ import annotations

from unittest.mock import MagicMock

from langmcp.profiles import ProfileManager
from langmcp.tools import store
from langmcp.tools.context import ToolContext


def _context_with_store(tmp_path, monkeypatch, *, user_namespace: str | None = None):
    namespace_config = (
        f'\nuser_namespace = "{user_namespace}"' if user_namespace is not None else ""
    )
    config = tmp_path / "langmcp.toml"
    config.write_text(
        f"""
[defaults]
profile = "mock"
read_only = true

[profiles.mock]
checkpointer = "sqlite:///./mock.db"
store = "sqlite:///./mock.db"{namespace_config}
""",
        encoding="utf-8",
    )
    ctx = ToolContext(ProfileManager(config_path=config))
    mock_store = MagicMock()
    mock_store.search.return_value = [
        {
            "namespace": ("users", "user-123", "preferences"),
            "key": "communication",
            "value": {"tone": "concise"},
        }
    ]
    bundle = MagicMock(profile_name="mock", store=mock_store)
    monkeypatch.setattr(ctx, "open_bundle", lambda _name: (bundle, None))
    return ctx, bundle, mock_store


def test_summarize_user_memory_uses_profile_namespace_template(tmp_path, monkeypatch):
    ctx, bundle, mock_store = _context_with_store(
        tmp_path,
        monkeypatch,
        user_namespace="users/{user_id}",
    )

    result = store.summarize_user_memory(ctx, "user-123", profile="mock")

    mock_store.search.assert_called_once_with(("users", "user-123"), limit=100, offset=0)
    assert result["namespace_prefix"] == ["users", "user-123"]
    assert result["total_items"] == 1
    assert "users/user-123/preferences" in result["namespace_groups"]
    bundle.close.assert_called_once()


def test_summarize_user_memory_preserves_legacy_namespace_default(tmp_path, monkeypatch):
    ctx, _bundle, mock_store = _context_with_store(tmp_path, monkeypatch)

    store.summarize_user_memory(ctx, "user-123", profile="mock")

    mock_store.search.assert_called_once_with(("user-123",), limit=100, offset=0)


def test_summarize_user_memory_allows_explicit_namespace_override(tmp_path, monkeypatch):
    ctx, _bundle, mock_store = _context_with_store(
        tmp_path,
        monkeypatch,
        user_namespace="users/{user_id}",
    )

    store.summarize_user_memory(
        ctx,
        "user-123",
        profile="mock",
        namespace_prefix="tenants/acme/people/{user_id}",
    )

    mock_store.search.assert_called_once_with(
        ("tenants", "acme", "people", "user-123"),
        limit=100,
        offset=0,
    )
