"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_config(tmp_path: Path) -> Path:
    config = tmp_path / "langmcp.toml"
    config.write_text(
        """
[defaults]
profile = "test"
read_only = true
max_response_chars = 25000

[profiles.test]
checkpointer = "sqlite:///${SQLITE_PATH}"
""",
        encoding="utf-8",
    )
    return config


@pytest.fixture
def sqlite_path(tmp_path: Path) -> Path:
    return tmp_path / "checkpoints.db"
