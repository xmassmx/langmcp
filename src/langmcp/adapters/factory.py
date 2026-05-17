"""Resolve profile URIs to LangGraph adapters."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from langmcp.adapters.postgres import PostgresCheckpointerAdapter, PostgresStoreAdapter
from langmcp.adapters.redis import RedisCheckpointerAdapter
from langmcp.adapters.sqlite import SqliteCheckpointerAdapter
from langmcp.profiles import ProfileManager


@dataclass
class AdapterBundle:
    profile_name: str
    checkpointer: object
    store: object | None
    checkpointer_uri: str
    store_uri: str | None

    def close(self) -> None:
        if hasattr(self.checkpointer, "close"):
            self.checkpointer.close()
        if self.store is not None and hasattr(self.store, "close"):
            self.store.close()


def _scheme(uri: str) -> str:
    return urlparse(uri).scheme.lower().replace("+psycopg", "")


def _ensure_resolved_uri(uri: str, *, label: str) -> None:
    if "${" in uri:
        raise ValueError(
            f"Unresolved environment variable in {label} URI. "
            "Set the referenced variable or update langmcp.toml."
        )
    if not _scheme(uri):
        raise ValueError(f"Missing URI scheme in {label} URI: {uri!r}")


def build_checkpointer(uri: str) -> object:
    _ensure_resolved_uri(uri, label="checkpointer")
    scheme = _scheme(uri)
    if scheme in ("postgresql", "postgres"):
        return PostgresCheckpointerAdapter(uri)
    if scheme == "sqlite":
        return SqliteCheckpointerAdapter(uri)
    if scheme in ("redis", "rediss"):
        return RedisCheckpointerAdapter(uri)
    raise ValueError(f"Unsupported checkpointer URI scheme: {scheme}")


def build_store(uri: str) -> object:
    _ensure_resolved_uri(uri, label="store")
    scheme = _scheme(uri)
    if scheme in ("postgresql", "postgres"):
        return PostgresStoreAdapter(uri)
    raise ValueError(
        f"Store not supported for scheme '{scheme}' in v0.1. "
        "Use PostgreSQL for long-term memory store."
    )


def get_adapters(
    profiles: ProfileManager,
    profile_name: str | None = None,
) -> AdapterBundle:
    name, cfg = profiles.get_profile(profile_name)
    cp = build_checkpointer(cfg.checkpointer)
    store = build_store(cfg.store) if cfg.store else None
    return AdapterBundle(
        profile_name=name,
        checkpointer=cp,
        store=store,
        checkpointer_uri=cfg.checkpointer,
        store_uri=cfg.store,
    )


def store_available(bundle: AdapterBundle) -> bool:
    return bundle.store is not None


def store_required_error(profile: str) -> dict:
    return {
        "error": "store_not_configured",
        "message": (
            f"Profile '{profile}' has no store URI. "
            "Configure a PostgreSQL store URI in langmcp.toml for long-term memory tools."
        ),
        "profile": profile,
    }
