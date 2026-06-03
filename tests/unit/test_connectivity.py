"""Unit tests for connection timeouts and unreachable-backend handling."""

from __future__ import annotations

import time

import pytest

from langmcp.connectivity import (
    backend_unreachable_error,
    is_backend_connection_error,
    with_connect_timeout,
)
from langmcp.discovery import list_threads_for_profile
from langmcp.profiles import ProfileManager
from langmcp.tools import threads
from langmcp.tools.context import ToolContext


def test_with_connect_timeout_appends_query_param():
    uri = "postgresql://user:pass@localhost:5442/langgraph"
    out = with_connect_timeout(uri, timeout=3)
    assert "connect_timeout=3" in out


def test_is_backend_connection_error_psycopg_timeout():
    try:
        import psycopg

        psycopg.connect(
            "postgresql://u:p@127.0.0.1:5430/nodb",
            connect_timeout=1,
        )
    except Exception as exc:
        assert is_backend_connection_error(exc)
    else:
        pytest.fail("expected connection failure")


def test_list_threads_unreachable_returns_error_fast(monkeypatch, tmp_path):
    monkeypatch.setenv("LANGMCP_CONNECT_TIMEOUT", "1")
    config = tmp_path / "langmcp.toml"
    config.write_text(
        """
[defaults]
profile = "bad"
read_only = true

[profiles.bad]
checkpointer = "postgresql://user:pass@127.0.0.1:5430/ai_ephemeral"
""",
        encoding="utf-8",
    )
    pm = ProfileManager(config_path=config)
    ctx = ToolContext(pm)
    start = time.perf_counter()
    result = threads.list_threads(ctx, profile="bad")
    elapsed = time.perf_counter() - start

    assert result["error"] == "backend_unreachable"
    assert result["profile"] == "bad"
    assert "5430" not in result["message"]
    assert elapsed < 8


def test_list_threads_for_profile_unresolved_env():
    data = list_threads_for_profile(
        "x",
        "${MISSING_VAR}",
        limit=10,
        offset=0,
    )
    assert data["error"] == "config_error"


def test_backend_unreachable_error_redacts_secrets():
    err = backend_unreachable_error(
        "dev",
        Exception("postgresql://user:secret@host:5430/db refused"),
        backend="postgresql",
    )
    assert "secret" not in err["message"]
    assert "***" in err["message"]
