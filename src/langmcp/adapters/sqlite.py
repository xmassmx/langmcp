"""SQLite checkpointer adapter (checkpoint-only in v0.1)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def sqlite_path_from_uri(uri: str) -> str:
    """Convert sqlite:///path URI to a filesystem path for SqliteSaver."""
    if uri.startswith("sqlite:"):
        parsed = urlparse(uri)
        path = parsed.path
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            return path[1:]
        if path.startswith("//"):
            return path[1:]
        if path.startswith(("/./", "/../")):
            return path[1:]
        return path or parsed.netloc
    return uri


class SqliteCheckpointerAdapter:
    backend = "sqlite"

    def __init__(self, conn_string: str) -> None:
        from langgraph.checkpoint.sqlite import SqliteSaver

        db_path = sqlite_path_from_uri(conn_string)
        self._ctx = SqliteSaver.from_conn_string(db_path)
        self._saver = self._ctx.__enter__()

    def setup(self) -> None:
        self._saver.setup()

    def get_tuple(self, config: dict[str, Any]) -> Any:
        return self._saver.get_tuple(config)

    def list_checkpoints(self, config: dict[str, Any], *, limit: int | None = None) -> list[Any]:
        kwargs: dict[str, Any] = {}
        if limit is not None:
            kwargs["limit"] = limit
        return list(self._saver.list(config, **kwargs))

    def close(self) -> None:
        self._ctx.__exit__(None, None, None)
