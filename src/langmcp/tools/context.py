"""Shared tool execution context."""

from __future__ import annotations

from langmcp.adapters.factory import (
    AdapterBundle,
    BackendConnectionError,
    get_adapters,
    store_required_error,
)
from langmcp.pagination import wrap_response
from langmcp.profiles import ProfileManager


class ToolContext:
    def __init__(self, profiles: ProfileManager) -> None:
        self.profiles = profiles
        if not profiles.read_only_enforced:
            raise RuntimeError(
                "LangMCP v0.1 requires read_only=true. Set LANGMCP_READ_ONLY=true or "
                "[defaults] read_only = true in langmcp.toml."
            )

    def bundle(self, profile: str | None = None) -> AdapterBundle:
        bundle, err = self.open_bundle(profile)
        if err is not None:
            raise BackendConnectionError(err)
        return bundle

    def open_bundle(self, profile: str | None = None) -> tuple[AdapterBundle | None, dict | None]:
        """Return (bundle, error_response). error_response is ready for ctx.finish()."""
        try:
            return get_adapters(self.profiles, profile), None
        except BackendConnectionError as exc:
            return None, exc.payload

    def finish_connection_error(
        self,
        err: dict,
        *,
        profile: str | None = None,
    ) -> dict:
        return self.finish(err, profile=err.get("profile", self.profiles.active_profile_name(profile)))

    def max_chars(self) -> int:
        return self.profiles.max_response_chars()

    def finish(self, data: dict, *, profile: str, truncated: bool = False) -> dict:
        return wrap_response(
            data,
            profile=profile,
            max_chars=self.max_chars(),
            truncated=truncated,
        )

    def require_store(self, bundle: AdapterBundle) -> dict | None:
        if bundle.store is None:
            return store_required_error(bundle.profile_name)
        return None
