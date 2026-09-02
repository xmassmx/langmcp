"""Profile manager: load langmcp.toml, resolve active profile."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from langmcp.config import (
    DefaultsConfig,
    LangMcpSettings,
    ProfileConfig,
    apply_env_overrides,
    backend_type_from_uri,
    expand_env,
    load_toml_dict,
    redact_uri,
)


class ProfileManager:
    def __init__(self, config_path: Path | None = None) -> None:
        self._load_cwd_env()
        self._settings = LangMcpSettings()
        self._config_path = config_path or self._resolve_config_path()
        self._load_config_env(self._config_path)
        self._settings = LangMcpSettings()
        self._defaults = DefaultsConfig()
        self._profiles: dict[str, ProfileConfig] = {}
        if self._config_path and self._config_path.is_file():
            self._load_file(self._config_path)

    @staticmethod
    def _load_cwd_env() -> None:
        load_dotenv(Path.cwd() / ".env", override=False)

    @staticmethod
    def _load_config_env(config_path: Path | None) -> None:
        if config_path:
            load_dotenv(config_path.parent / ".env", override=False)

    @staticmethod
    def _resolve_config_path() -> Path | None:
        env = os.environ.get("LANGMCP_CONFIG")
        if env:
            return Path(env)
        for candidate in (Path("langmcp.toml"), Path.home() / ".langmcp.toml"):
            if candidate.is_file():
                return candidate
        return None

    def _load_file(self, path: Path) -> None:
        data = load_toml_dict(path)
        if "defaults" in data:
            self._defaults = DefaultsConfig.model_validate(data["defaults"])
        profiles_raw = data.get("profiles", {})
        for name, cfg in profiles_raw.items():
            if isinstance(cfg, dict):
                cp = expand_env(str(cfg.get("checkpointer", "")))
                store_val = cfg.get("store")
                store = expand_env(str(store_val)) if store_val else None
                user_namespace = expand_env(str(cfg.get("user_namespace", "{user_id}")))
                self._profiles[name] = ProfileConfig(
                    checkpointer=cp,
                    store=store,
                    user_namespace=user_namespace,
                )

    @property
    def config_path(self) -> Path | None:
        return self._config_path

    @property
    def defaults(self) -> DefaultsConfig:
        return self._defaults

    @property
    def read_only_enforced(self) -> bool:
        env_ro = self._settings.read_only
        if env_ro is not None:
            return env_ro
        return self._defaults.read_only

    def active_profile_name(self, override: str | None = None) -> str:
        return (
            override
            or self._settings.profile
            or os.environ.get("LANGMCP_PROFILE")
            or self._defaults.profile
        )

    def get_profile(self, name: str | None = None) -> tuple[str, ProfileConfig]:
        profile_name = self.active_profile_name(name)
        if profile_name not in self._profiles:
            available = ", ".join(sorted(self._profiles)) or "(none)"
            raise KeyError(f"Profile '{profile_name}' not found. Available profiles: {available}")
        raw = self._profiles[profile_name]
        resolved = apply_env_overrides(raw, self._settings)
        return profile_name, resolved

    def list_profiles(self) -> list[dict[str, str]]:
        result = []
        for name, cfg in sorted(self._profiles.items()):
            result.append(
                {
                    "name": name,
                    "checkpointer_backend": backend_type_from_uri(cfg.checkpointer),
                    "store_backend": (backend_type_from_uri(cfg.store) if cfg.store else "none"),
                    "has_store": str(cfg.store is not None).lower(),
                }
            )
        return result

    def profile_health_info(self, name: str | None = None) -> dict:
        profile_name, cfg = self.get_profile(name)
        return {
            "profile": profile_name,
            "checkpointer_uri_redacted": redact_uri(cfg.checkpointer),
            "store_uri_redacted": redact_uri(cfg.store) if cfg.store else None,
            "checkpointer_backend": backend_type_from_uri(cfg.checkpointer),
            "store_backend": (backend_type_from_uri(cfg.store) if cfg.store else None),
            "has_store": cfg.store is not None,
            "read_only": self.read_only_enforced,
            "max_response_chars": self._defaults.max_response_chars,
        }

    def max_response_chars(self) -> int:
        return self._defaults.max_response_chars
