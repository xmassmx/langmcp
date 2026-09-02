"""Configuration models and secret redaction."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")
_ENV_FALLBACKS: dict[str, tuple[str, ...]] = {
    "DATABASE_URL": ("POSTGRES_URI",),
}
_URI_IN_MESSAGE = re.compile(
    r"(postgresql|postgres|redis|rediss|sqlite)(\+\w+)?://[^\s\"')]+",
    re.IGNORECASE,
)


def _resolve_env_var(key: str) -> str | None:
    val = os.environ.get(key)
    if val:
        return val
    for alt in _ENV_FALLBACKS.get(key, ()):
        alt_val = os.environ.get(alt)
        if alt_val:
            return alt_val
    return None


def expand_env(value: str) -> str:
    """Expand ${VAR} placeholders from environment."""

    def replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        resolved = _resolve_env_var(key)
        return resolved if resolved is not None else match.group(0)

    return _ENV_VAR_PATTERN.sub(replacer, value)


def sanitize_error_message(message: str) -> str:
    """Strip credentials and URIs from exception text before surfacing to users."""

    def _redact_match(match: re.Match[str]) -> str:
        return redact_uri(match.group(0))

    text = _URI_IN_MESSAGE.sub(_redact_match, str(message))
    return re.sub(r":([^:@/]+)@", ":***@", text)


def redact_uri(uri: str) -> str:
    """Redact password in connection URIs for safe display."""
    if not uri:
        return uri
    try:
        parsed = urlparse(uri)
        if parsed.password:
            netloc = parsed.hostname or ""
            if parsed.port:
                netloc = f"{netloc}:{parsed.port}"
            if parsed.username:
                netloc = f"{parsed.username}:***@{netloc}"
            else:
                netloc = f"***@{netloc}"
            return urlunparse(
                (
                    parsed.scheme,
                    netloc,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment,
                )
            )
    except Exception:
        pass
    return re.sub(r":([^:@/]+)@", ":***@", uri, count=1)


def backend_type_from_uri(uri: str) -> str:
    scheme = urlparse(uri).scheme.lower().replace("+psycopg", "")
    if scheme in ("postgresql", "postgres"):
        return "postgresql"
    if scheme == "sqlite":
        return "sqlite"
    if scheme in ("redis", "rediss"):
        return "redis"
    return scheme or "unknown"


class ProfileConfig(BaseModel):
    checkpointer: str
    store: str | None = None
    user_namespace: str = "{user_id}"


class DefaultsConfig(BaseModel):
    profile: str = "dev"
    read_only: bool = True
    max_response_chars: int = 25000


class LangMcpSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LANGMCP_", extra="ignore")

    config_path: Path | None = Field(default=None, validation_alias="LANGMCP_CONFIG")
    profile: str | None = Field(default=None, validation_alias="LANGMCP_PROFILE")
    read_only: bool | None = Field(default=None, validation_alias="LANGMCP_READ_ONLY")
    checkpointer_uri: str | None = Field(default=None, validation_alias="LANGMCP_CHECKPOINTER_URI")
    store_uri: str | None = Field(default=None, validation_alias="LANGMCP_STORE_URI")


def apply_env_overrides(
    profile: ProfileConfig,
    settings: LangMcpSettings,
) -> ProfileConfig:
    cp = settings.checkpointer_uri or profile.checkpointer
    st = settings.store_uri or profile.store
    return ProfileConfig(
        checkpointer=expand_env(cp),
        store=expand_env(st) if st else None,
        user_namespace=expand_env(profile.user_namespace),
    )


def load_toml_dict(path: Path) -> dict[str, Any]:
    import tomllib

    with path.open("rb") as f:
        return tomllib.load(f)
