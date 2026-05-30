"""Read-only thread discovery across checkpoint backends."""

from __future__ import annotations

import sqlite3
import time
from typing import Any
from urllib.parse import urlparse

from langmcp.adapters.sqlite import sqlite_path_from_uri
from langmcp.config import backend_type_from_uri, sanitize_error_message
from langmcp.connectivity import (
    backend_unreachable_error,
    connect_timeout_seconds,
    is_backend_connection_error,
    with_connect_timeout,
)

# LangGraph RedisSaver persists checkpoints under keys like checkpoint:{thread_id}:...
_REDIS_CHECKPOINT_KEY_PREFIX = "checkpoint:"

# LangGraph checkpoint-postgres table (v2+)
_POSTGRES_THREADS_SQL = """
SELECT thread_id, MAX(checkpoint->>'ts') AS last_updated
FROM checkpoints
GROUP BY thread_id
ORDER BY last_updated DESC NULLS LAST
LIMIT %s OFFSET %s
"""

_SQLITE_THREADS_SQL = """
SELECT thread_id, MAX(checkpoint_id) AS last_updated
FROM checkpoints
GROUP BY thread_id
ORDER BY last_updated DESC
LIMIT ? OFFSET ?
"""


def _postgres_conn_string(uri: str) -> str:
    parsed = urlparse(uri)
    scheme = parsed.scheme.replace("+psycopg", "")
    if scheme == "postgres":
        scheme = "postgresql"
    return uri.replace(parsed.scheme, scheme, 1)


def list_threads_postgres(uri: str, *, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    import psycopg
    from psycopg.rows import dict_row

    conn_str = with_connect_timeout(_postgres_conn_string(uri))
    timeout = connect_timeout_seconds()
    try:
        with psycopg.connect(
            conn_str,
            row_factory=dict_row,
            connect_timeout=timeout,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(_POSTGRES_THREADS_SQL, (limit, offset))
                rows = cur.fetchall()
    except Exception as exc:
        if is_backend_connection_error(exc):
            raise ConnectionError(sanitize_error_message(exc)) from exc
        raise
    return [
        {
            "thread_id": row["thread_id"],
            "last_updated": row.get("last_updated"),
        }
        for row in rows
    ]


def list_threads_sqlite(uri: str, *, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    db_path = sqlite_path_from_uri(uri)
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error as exc:
        if is_backend_connection_error(exc):
            raise ConnectionError(sanitize_error_message(exc)) from exc
        raise
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(_SQLITE_THREADS_SQL, (limit, offset))
        rows = cur.fetchall()
    finally:
        conn.close()
    return [{"thread_id": row["thread_id"], "last_updated": row["last_updated"]} for row in rows]


def list_threads_redis(
    uri: str,
    *,
    limit: int = 50,
    offset: int = 0,
    scan_count: int = 500,
    max_keys: int = 10000,
    scan_deadline_seconds: float = 30.0,
) -> tuple[list[dict[str, Any]], str | None]:
    """Discover threads via Redis key scan. Returns (threads, warning)."""
    import redis

    timeout = connect_timeout_seconds()
    try:
        client = redis.from_url(
            uri,
            socket_connect_timeout=timeout,
            socket_timeout=timeout,
        )
    except Exception as exc:
        if is_backend_connection_error(exc):
            raise ConnectionError(sanitize_error_message(exc)) from exc
        raise
    warning: str | None = None
    prefix = _REDIS_CHECKPOINT_KEY_PREFIX
    thread_ids: set[str] = set()
    scanned = 0
    cursor = 0
    deadline = time.monotonic() + scan_deadline_seconds
    while True:
        if time.monotonic() >= deadline:
            warning = (
                f"Redis SCAN stopped after {scan_deadline_seconds:g}s deadline; "
                "results may be incomplete."
            )
            break
        cursor, keys = client.scan(cursor=cursor, match=f"{prefix}*", count=scan_count)
        scanned += len(keys)
        for key in keys:
            key_str = key.decode() if isinstance(key, bytes) else str(key)
            parts = key_str.split(":")
            if len(parts) >= 2:
                thread_ids.add(parts[1])
        if cursor == 0 or scanned >= max_keys:
            break
    if scanned >= max_keys and not warning:
        warning = (
            f"Redis SCAN capped at {max_keys} keys; results may be incomplete. "
            "Use a dedicated Redis instance for development checkpoints."
        )
    sorted_ids = sorted(thread_ids)
    page = sorted_ids[offset : offset + limit]
    client.close()
    return [{"thread_id": tid, "last_updated": None} for tid in page], warning


def list_threads_for_uri(
    uri: str,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], str | None]:
    if "${" in uri:
        raise ValueError(
            "Unresolved environment variable in checkpointer URI. "
            "Set the referenced variable or update langmcp.toml."
        )
    scheme = urlparse(uri).scheme.lower().replace("+psycopg", "")
    if scheme in ("postgresql", "postgres"):
        return list_threads_postgres(uri, limit=limit, offset=offset), None
    if scheme == "sqlite":
        return list_threads_sqlite(uri, limit=limit, offset=offset), None
    if scheme in ("redis", "rediss"):
        return list_threads_redis(uri, limit=limit, offset=offset)
    raise ValueError(f"Thread discovery not supported for scheme: {scheme}")


def list_threads_for_profile(
    profile_name: str,
    checkpointer_uri: str,
    *,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List threads or return a structured backend_unreachable error dict."""
    backend = backend_type_from_uri(checkpointer_uri)
    try:
        threads, warning = list_threads_for_uri(
            checkpointer_uri,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        if is_backend_connection_error(exc) or isinstance(exc, (ValueError, OSError)):
            if isinstance(exc, ValueError) and "Unresolved" in str(exc):
                return {
                    "error": "config_error",
                    "message": str(exc),
                    "profile": profile_name,
                }
            return backend_unreachable_error(
                profile_name,
                exc,
                backend=backend,
                role="checkpointer",
            )
        raise
    data: dict[str, Any] = {"threads": threads, "limit": limit, "offset": offset}
    if warning:
        data["warning"] = warning
    return data
