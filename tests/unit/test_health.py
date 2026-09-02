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


def test_health_check_read_only_skips_setup(health_profile, monkeypatch):
    """v0.1 read-only mode probes reads only; setup() must not run."""
    mock_cp = MagicMock()
    mock_cp.get_tuple.return_value = None

    mock_store = MagicMock()
    mock_store.list_namespaces.return_value = []

    mock_bundle = MagicMock()
    mock_bundle.checkpointer = mock_cp
    mock_bundle.store = mock_store

    ctx = ToolContext(health_profile)
    monkeypatch.setattr(ctx, "open_bundle", lambda _name: (mock_bundle, None))

    result = health.health_check(ctx, profile="mock")

    assert result["checkpointer_connected"] is True
    assert result["checkpointer_setup"] is False
    assert result["store_connected"] is True
    assert result["store_setup"] is False
    assert result["warning"] is None
    mock_store.list_namespaces.assert_called_once_with(max_depth=1)
    mock_cp.setup.assert_not_called()
    mock_store.setup.assert_not_called()
    mock_bundle.close.assert_called_once()


def test_probe_setup_warning_when_not_read_only():
    """When read_only is false, setup failure is a warning, not a connectivity failure."""
    mock_cp = MagicMock()
    mock_cp.get_tuple.return_value = None
    mock_cp.setup.side_effect = PermissionError("permission denied for schema public")

    mock_bundle = MagicMock()
    mock_bundle.checkpointer = mock_cp
    mock_bundle.store = None

    ok, setup_ok, warn = health._probe_checkpointer(mock_bundle, read_only=False)

    assert ok is True
    assert setup_ok is False
    assert warn is not None
    assert "read access OK" in warn
    assert "permission denied" in warn


def test_health_check_unreachable_backend(health_profile, monkeypatch):
    ctx = ToolContext(health_profile)
    monkeypatch.setattr(
        ctx,
        "open_bundle",
        lambda _name: (
            None,
            {
                "error": "backend_unreachable",
                "message": "Could not connect to checkpointer (postgresql): timeout",
                "profile": "mock",
                "backend": "postgresql",
                "role": "checkpointer",
            },
        ),
    )

    result = health.health_check(ctx, profile="mock")

    assert result["checkpointer_connected"] is False
    assert result["error"] == "backend_unreachable"
    assert "timeout" in (result.get("warning") or "")


def test_health_check_fails_when_read_fails(health_profile, monkeypatch):
    mock_cp = MagicMock()
    mock_cp.get_tuple.side_effect = ConnectionError(
        "postgresql://user:secret@localhost:5432/db connection refused"
    )
    mock_bundle = MagicMock()
    mock_bundle.checkpointer = mock_cp
    mock_bundle.store = None

    ctx = ToolContext(health_profile)
    monkeypatch.setattr(ctx, "open_bundle", lambda _name: (mock_bundle, None))

    result = health.health_check(ctx, profile="mock")

    assert result["checkpointer_connected"] is False
    assert result["checkpointer_setup"] is False
    assert "secret" not in (result.get("warning") or "")
    assert "***" in (result.get("warning") or "")
    mock_bundle.close.assert_called_once()
