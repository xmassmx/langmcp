"""Connection timeouts and backend error responses for unreachable persistence."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from langmcp.config import backend_type_from_uri, sanitize_error_message

_DEFAULT_CONNECT_TIMEOUT = 5.0


def connect_timeout_seconds() -> float:
    raw = os.environ.get("LANGMCP_CONNECT_TIMEOUT")
    if raw is None:
        return _DEFAULT_CONNECT_TIMEOUT
    try:
        value = float(raw)
    except ValueError:
        return _DEFAULT_CONNECT_TIMEOUT
    return max(0.5, value)


def with_connect_timeout(uri: str, timeout: float | None = None) -> str:
    """Append libpq connect_timeout to a PostgreSQL URI when not already set."""
    seconds = int(timeout if timeout is not None else connect_timeout_seconds())
    parsed = urlparse(uri)
    scheme = parsed.scheme.lower().replace("+psycopg", "")
    if scheme not in ("postgresql", "postgres"):
        return uri
    query = parse_qs(parsed.query, keep_blank_values=True)
    if "connect_timeout" not in query:
        query["connect_timeout"] = [str(seconds)]
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def is_backend_connection_error(exc: BaseException) -> bool:
    """True when the exception likely indicates an unreachable or misconfigured backend."""
    name = type(exc).__name__
    module = type(exc).__module__ or ""
    if name in ("ConnectionError", "ConnectionRefusedError", "TimeoutError", "ConnectionTimeout"):
        return True
    if "psycopg" in module and name in (
        "OperationalError",
        "ConnectionTimeout",
        "InterfaceError",
    ):
        return True
    if "redis" in module and name in ("ConnectionError", "TimeoutError"):
        return True
    if name == "OperationalError" and "sqlite3" in module:
        return True
    if isinstance(exc, OSError) and getattr(exc, "winerror", None) in (10061, 10060):
        return True
    if isinstance(exc, OSError) and getattr(exc, "errno", None) in (61, 110, 111, 113):
        return True
    return False


def backend_unreachable_error(
    profile: str,
    exc: BaseException,
    *,
    backend: str,
    role: str = "checkpointer",
) -> dict[str, Any]:
    """Structured tool response when a persistence backend cannot be reached."""
    detail = sanitize_error_message(str(exc))
    return {
        "error": "backend_unreachable",
        "message": (
            f"Could not connect to {role} ({backend}): {detail}. "
            "Verify the profile URI host/port, credentials, and that the database is running. "
            "Run health_check for this profile to diagnose connectivity."
        ),
        "profile": profile,
        "backend": backend,
        "role": role,
    }
