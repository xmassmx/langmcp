"""PostgreSQL integration tests (requires docker-compose)."""

from __future__ import annotations

import os

import pytest

from langmcp.profiles import ProfileManager
from langmcp.tools import checkpoints, store, threads
from langmcp.tools.context import ToolContext

POSTGRES_URI = os.environ.get(
    "POSTGRES_URI",
    "postgresql://langgraph:langgraph@localhost:5442/langgraph",
)


@pytest.fixture(scope="module")
def postgres_profile(tmp_path_factory):
    if os.environ.get("SKIP_INTEGRATION"):
        pytest.skip("SKIP_INTEGRATION set")
    try:
        import psycopg

        psycopg.connect(POSTGRES_URI, connect_timeout=2).close()
    except Exception:
        pytest.skip("PostgreSQL not available")

    from tests.fixtures.seed_graph import seed

    os.environ["POSTGRES_URI"] = POSTGRES_URI
    seed("postgres")

    config = tmp_path_factory.mktemp("cfg") / "langmcp.toml"
    config.write_text(
        f"""
[defaults]
profile = "pg"
read_only = true

[profiles.pg]
checkpointer = "{POSTGRES_URI}"
store = "{POSTGRES_URI}"
""",
        encoding="utf-8",
    )
    return ProfileManager(config_path=config)


@pytest.mark.integration
def test_postgres_list_threads(postgres_profile):
    ctx = ToolContext(postgres_profile)
    result = threads.list_threads(ctx, profile="pg")
    ids = [t["thread_id"] for t in result["threads"]]
    assert "test-1" in ids


@pytest.mark.integration
def test_postgres_summarize(postgres_profile):
    ctx = ToolContext(postgres_profile)
    result = checkpoints.summarize_thread(ctx, "test-1", profile="pg")
    assert result["message_count"] >= 2


@pytest.mark.integration
def test_postgres_search_store(postgres_profile):
    ctx = ToolContext(postgres_profile)
    result = store.search_store(ctx, "user-test-1", profile="pg", limit=10)
    keys = [i.get("key") for i in result.get("items", [])]
    assert "theme" in keys
