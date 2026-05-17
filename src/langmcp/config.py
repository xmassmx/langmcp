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


def expand_env(value: str) -> str:
    """Expand ${VAR} placeholders from environment."""

    def replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        return os.environ.get(key, match.group(0))

    return _ENV_VAR_PATTERN.sub(replacer, value)


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
    return ProfileConfig(checkpointer=expand_env(cp), store=expand_env(st) if st else None)


def load_toml_dict(path: Path) -> dict[str, Any]:
    import tomllib

    with path.open("rb") as f:
        return tomllib.load(f)
