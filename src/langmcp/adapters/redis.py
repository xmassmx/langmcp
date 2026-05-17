"""Redis checkpointer adapter (checkpoint-only in v0.1)."""

from __future__ import annotations

from typing import Any


class RedisCheckpointerAdapter:
    backend = "redis"

    def __init__(self, conn_string: str) -> None:
        from langgraph.checkpoint.redis import RedisSaver

        self._ctx = RedisSaver.from_conn_string(conn_string)
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
