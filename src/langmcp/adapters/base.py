"""Adapter protocols for checkpointer and store access."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CheckpointerAdapter(Protocol):
    backend: str

    def setup(self) -> None: ...

    def get_tuple(self, config: dict[str, Any]) -> Any: ...

    def list_checkpoints(
        self, config: dict[str, Any], *, limit: int | None = None
    ) -> list[Any]: ...

    def close(self) -> None: ...


@runtime_checkable
class StoreAdapter(Protocol):
    backend: str

    def setup(self) -> None: ...

    def list_namespaces(
        self,
        *,
        prefix: tuple[str, ...] | None = None,
        max_depth: int | None = None,
    ) -> list[tuple[str, ...]]: ...

    def search(
        self,
        namespace_prefix: tuple[str, ...],
        *,
        query: str | None = None,
        filter: dict[str, Any] | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[Any]: ...

    def get(self, namespace: tuple[str, ...], key: str) -> Any: ...

    def close(self) -> None: ...
