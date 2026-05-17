"""Unit tests for health_check connectivity vs setup."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from langmcp.profiles import ProfileManager
from langmcp.tools import health
from langmcp.tools.context import ToolContext


@pytest.fixture
def health_profile(tmp_path):
    config = tmp_path / "langmcp.toml"
    config.write_text(
        """
[defaults]
profile = "mock"
read_only = true

[profiles.mock]
checkpointer = "sqlite:///./mock.db"
store = "sqlite:///./mock.db"
""",
        encoding="utf-8",
    )
    return ProfileManager(config_path=config)


def test_health_check_connected_when_setup_fails(health_profile, monkeypatch):
    """Read access succeeds; setup failure is a warning, not a connectivity failure."""
    mock_cp = MagicMock()
    mock_cp.get_tuple.return_value = None
    mock_cp.setup.side_effect = PermissionError("permission denied for schema public")

    mock_store = MagicMock()
    mock_store.list_namespaces.return_value = []
    mock_store.setup.side_effect = PermissionError("permission denied for schema public")

    mock_bundle = MagicMock()
    mock_bundle.checkpointer = mock_cp
    mock_bundle.store = mock_store

    ctx = ToolContext(health_profile)
    monkeypatch.setattr(ctx, "bundle", lambda _name: mock_bundle)

    result = health.health_check(ctx, profile="mock")

    assert result["checkpointer_connected"] is True
    assert result["checkpointer_setup"] is False
    assert result["store_connected"] is True
    assert result["store_setup"] is False
    assert result["warning"] is not None
    assert "read access OK" in result["warning"]
    assert "permission denied" in result["warning"]
    mock_bundle.close.assert_called_once()


def test_health_check_fails_when_read_fails(health_profile, monkeypatch):
    mock_cp = MagicMock()
    mock_cp.get_tuple.side_effect = ConnectionError(
        "postgresql://user:secret@localhost:5432/db connection refused"
    )
    mock_bundle = MagicMock()
    mock_bundle.checkpointer = mock_cp
    mock_bundle.store = None

    ctx = ToolContext(health_profile)
    monkeypatch.setattr(ctx, "bundle", lambda _name: mock_bundle)

    result = health.health_check(ctx, profile="mock")

    assert result["checkpointer_connected"] is False
    assert result["checkpointer_setup"] is False
    assert "secret" not in (result.get("warning") or "")
    assert "***" in (result.get("warning") or "")
    mock_bundle.close.assert_called_once()
