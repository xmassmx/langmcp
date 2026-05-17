"""PostgreSQL checkpointer and store adapters."""

from __future__ import annotations

from typing import Any


class PostgresCheckpointerAdapter:
    backend = "postgresql"

    def __init__(self, conn_string: str) -> None:
        from langgraph.checkpoint.postgres import PostgresSaver

        self._ctx = PostgresSaver.from_conn_string(conn_string)
        self._saver = self._ctx.__enter__()

    def setup(self) -> None:
        self._saver.setup()

    def get_tuple(self, config: dict[str, Any]) -> Any:
        return self._saver.get_tuple(config)

    def list_checkpoints(
        self, config: dict[str, Any], *, limit: int | None = None
    ) -> list[Any]:
        kwargs: dict[str, Any] = {}
        if limit is not None:
            kwargs["limit"] = limit
        return list(self._saver.list(config, **kwargs))

    def close(self) -> None:
        self._ctx.__exit__(None, None, None)


class PostgresStoreAdapter:
    backend = "postgresql"

    def __init__(self, conn_string: str) -> None:
        from langgraph.store.postgres import PostgresStore

        self._ctx = PostgresStore.from_conn_string(conn_string)
        self._store = self._ctx.__enter__()

    def setup(self) -> None:
        self._store.setup()

    def list_namespaces(
        self,
        *,
        prefix: tuple[str, ...] | None = None,
        max_depth: int | None = None,
    ) -> list[tuple[str, ...]]:
        kwargs: dict[str, Any] = {}
        if prefix is not None:
            kwargs["prefix"] = prefix
        if max_depth is not None:
            kwargs["max_depth"] = max_depth
        return list(self._store.list_namespaces(**kwargs))

    def search(
        self,
        namespace_prefix: tuple[str, ...],
        *,
        query: str | None = None,
        filter: dict[str, Any] | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[Any]:
        kwargs: dict[str, Any] = {
            "namespace_prefix": namespace_prefix,
            "limit": limit,
            "offset": offset,
        }
        if query is not None:
            kwargs["query"] = query
        if filter is not None:
            kwargs["filter"] = filter
        return list(self._store.search(**kwargs))

    def get(self, namespace: tuple[str, ...], key: str) -> Any:
        return self._store.get(namespace, key)

    def close(self) -> None:
        self._ctx.__exit__(None, None, None)
