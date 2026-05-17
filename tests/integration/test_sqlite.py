"""SQLite integration tests."""

from __future__ import annotations

import os

import pytest

from langmcp.profiles import ProfileManager
from langmcp.tools.context import ToolContext
from langmcp.tools import checkpoints, threads


@pytest.mark.integration
def test_sqlite_flow(tmp_path):
    if os.environ.get("SKIP_INTEGRATION"):
        pytest.skip("SKIP_INTEGRATION set")
    db = tmp_path / "cp.db"
    os.environ["SQLITE_PATH"] = db.as_posix()
    from tests.fixtures.seed_graph import seed

    seed("sqlite")
    config = tmp_path / "langmcp.toml"
    config.write_text(
        f"""
[defaults]
profile = "local"
read_only = true

[profiles.local]
checkpointer = "sqlite:///{db.as_posix()}"
""",
        encoding="utf-8",
    )
    pm = ProfileManager(config_path=config)
    ctx = ToolContext(pm)
    listed = threads.list_threads(ctx)
    assert any(t["thread_id"] == "test-1" for t in listed["threads"])
    summary = checkpoints.summarize_thread(ctx, "test-1")
    assert summary["message_count"] >= 2
