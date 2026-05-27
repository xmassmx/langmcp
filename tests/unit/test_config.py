"""Unit tests for configuration and profiles."""

from __future__ import annotations

import os

import pytest

from langmcp.adapters.sqlite import sqlite_path_from_uri
from langmcp.config import expand_env, redact_uri
from langmcp.profiles import ProfileManager


def test_expand_env():
    os.environ["TEST_LANGMCP_VAR"] = "hello"
    assert expand_env("prefix-${TEST_LANGMCP_VAR}-suffix") == "prefix-hello-suffix"
    del os.environ["TEST_LANGMCP_VAR"]


def test_expand_env_database_url_fallback(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv(
        "POSTGRES_URI",
        "postgresql://langgraph:langgraph@localhost:5442/langgraph",
    )
    assert (
        expand_env("${DATABASE_URL}") == "postgresql://langgraph:langgraph@localhost:5442/langgraph"
    )
    monkeypatch.delenv("POSTGRES_URI", raising=False)


def test_sanitize_error_message():
    from langmcp.config import sanitize_error_message

    msg = "failed: postgresql://user:secret@localhost:5432/db"
    cleaned = sanitize_error_message(msg)
    assert "secret" not in cleaned
    assert "***" in cleaned


def test_redact_uri():
    uri = "postgresql://user:secret@localhost:5432/db"
    redacted = redact_uri(uri)
    assert "secret" not in redacted
    assert "***" in redacted
    assert "user" in redacted


def test_sqlite_uri_path_conversion():
    assert sqlite_path_from_uri("sqlite:////tmp/langmcp/cp.db") == "/tmp/langmcp/cp.db"
    assert (
        sqlite_path_from_uri("sqlite:///./.langgraph/checkpoints.db")
        == "./.langgraph/checkpoints.db"
    )
    assert sqlite_path_from_uri("sqlite:///C:/Users/me/cp.db") == "C:/Users/me/cp.db"


def test_profile_manager_loads(sample_config, sqlite_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(sqlite_path))
    pm = ProfileManager(config_path=sample_config)
    names = [p["name"] for p in pm.list_profiles()]
    assert "test" in names
    assert pm.read_only_enforced is True
    _, cfg = pm.get_profile("test")
    assert str(sqlite_path) in cfg.checkpointer


def test_profile_manager_loads_dotenv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("POSTGRES_URI", raising=False)
    (tmp_path / ".env").write_text(
        "POSTGRES_URI=postgresql://readonly:secret@localhost:5432/app\n",
        encoding="utf-8",
    )
    config = tmp_path / "langmcp.toml"
    config.write_text(
        """
[defaults]
profile = "dev"
read_only = true

[profiles.dev]
checkpointer = "${POSTGRES_URI}"
store = "${POSTGRES_URI}"
""",
        encoding="utf-8",
    )

    pm = ProfileManager(config_path=config)
    _, cfg = pm.get_profile("dev")

    assert cfg.checkpointer == "postgresql://readonly:secret@localhost:5432/app"
    assert cfg.store == "postgresql://readonly:secret@localhost:5432/app"


def test_read_only_required_false_raises(tmp_path, monkeypatch):
    config = tmp_path / "langmcp.toml"
    config.write_text(
        """
[defaults]
read_only = false
profile = "x"

[profiles.x]
checkpointer = "sqlite:///./x.db"
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("LANGMCP_READ_ONLY", "false")
    pm2 = ProfileManager(config_path=config)
    assert pm2.read_only_enforced is False
    from langmcp.tools.context import ToolContext

    with pytest.raises(RuntimeError, match="read_only"):
        ToolContext(pm2)
