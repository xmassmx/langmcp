"""Redis integration tests."""

from __future__ import annotations

import os

import pytest

from langmcp.profiles import ProfileManager
from langmcp.tools import threads
from langmcp.tools.context import ToolContext

REDIS_URI = os.environ.get("REDIS_URI", "redis://localhost:6379/0")


@pytest.mark.integration
def test_redis_flow(tmp_path):
    if os.environ.get("SKIP_INTEGRATION"):
        pytest.skip("SKIP_INTEGRATION set")
    try:
        import redis

        client = redis.from_url(REDIS_URI, socket_connect_timeout=2)
        client.ping()
        client.close()
    except Exception:
        pytest.skip("Redis not available")
    os.environ["REDIS_URI"] = REDIS_URI
    from tests.fixtures.seed_graph import seed

    seed("redis")
    config = tmp_path / "langmcp.toml"
    config.write_text(
        f"""
[defaults]
profile = "redis"
read_only = true

[profiles.redis]
checkpointer = "{REDIS_URI}"
""",
        encoding="utf-8",
    )
    pm = ProfileManager(config_path=config)
    ctx = ToolContext(pm)
    listed = threads.list_threads(ctx, profile="redis")
    thread_ids = [t["thread_id"] for t in listed["threads"]]
    assert "test-1" in thread_ids
    state = threads.get_thread_state(ctx, "test-1")
    assert "state" in state
