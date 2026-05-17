"""CLI smoke tests."""

from __future__ import annotations

from typer.testing import CliRunner

from langmcp import __version__
from langmcp.cli import app

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == f"langmcp {__version__}"


def test_doctor_reports_unresolved_uri_without_traceback(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LANGMCP_CONFIG", raising=False)
    monkeypatch.delenv("LANGMCP_PROFILE", raising=False)
    monkeypatch.delenv("LANGMCP_READ_ONLY", raising=False)
    monkeypatch.delenv("LANGMCP_CHECKPOINTER_URI", raising=False)
    monkeypatch.delenv("LANGMCP_STORE_URI", raising=False)
    monkeypatch.delenv("POSTGRES_URI", raising=False)
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

    result = runner.invoke(app, ["doctor", "--config", str(config)])

    assert result.exit_code == 1
    assert "Config error:" in result.output
    assert "Unresolved environment variable" in result.output
    assert "Traceback" not in result.output


def test_doctor_rejects_non_read_only_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LANGMCP_CONFIG", raising=False)
    monkeypatch.delenv("LANGMCP_PROFILE", raising=False)
    monkeypatch.delenv("LANGMCP_READ_ONLY", raising=False)
    monkeypatch.delenv("LANGMCP_CHECKPOINTER_URI", raising=False)
    monkeypatch.delenv("LANGMCP_STORE_URI", raising=False)
    config = tmp_path / "langmcp.toml"
    config.write_text(
        """
[defaults]
profile = "dev"
read_only = false

[profiles.dev]
checkpointer = "sqlite:///./checkpoints.db"
""",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["doctor", "--config", str(config)])

    assert result.exit_code == 1
    assert "requires read_only=true" in result.output
    assert "Testing checkpointer read access" not in result.output
