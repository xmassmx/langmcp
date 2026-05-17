"""Health and profile listing tools."""

from __future__ import annotations

import importlib.metadata

from langmcp.config import sanitize_error_message
from langmcp.tools.context import ToolContext

_HEALTH_CONFIG = {"configurable": {"thread_id": "__langmcp_health__"}}


def _probe_checkpointer(bundle) -> tuple[bool, bool, str | None]:
    """Test read access first, then optional setup(). Returns (connected, setup_ok, warning)."""
    try:
        bundle.checkpointer.get_tuple(_HEALTH_CONFIG)
    except Exception as exc:
        return False, False, f"Checkpointer: {sanitize_error_message(exc)}"

    cp_setup = False
    warning = None
    try:
        bundle.checkpointer.setup()
        cp_setup = True
    except Exception as exc:
        warning = (
            f"Checkpointer setup: {sanitize_error_message(exc)} "
            "(read access OK; setup may require write privileges)"
        )
    return True, cp_setup, warning


def _probe_store(bundle) -> tuple[bool | None, bool | None, str | None]:
    """Test store read access first, then optional setup()."""
    if not bundle.store:
        return None, None, None

    try:
        bundle.store.list_namespaces(max_depth=0)
    except Exception as exc:
        return False, False, f"Store: {sanitize_error_message(exc)}"

    store_setup = False
    warning = None
    try:
        bundle.store.setup()
        store_setup = True
    except Exception as exc:
        warning = (
            f"Store setup: {sanitize_error_message(exc)} "
            "(read access OK; setup may require write privileges)"
        )
    return True, store_setup, warning


def health_check(ctx: ToolContext, profile: str | None = None) -> dict:
    info = ctx.profiles.profile_health_info(profile)
    profile_name = info["profile"]
    bundle = ctx.bundle(profile_name)
    warnings: list[str] = []
    try:
        cp_ok, cp_setup, cp_warn = _probe_checkpointer(bundle)
        if cp_warn:
            warnings.append(cp_warn)
        store_ok, store_setup, store_warn = _probe_store(bundle)
        if store_warn:
            warnings.append(store_warn)
    finally:
        bundle.close()

    versions = {}
    for pkg in (
        "langgraph",
        "langgraph-checkpoint",
        "langgraph-checkpoint-postgres",
        "mcp",
        "langmcp",
    ):
        try:
            versions[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            pass

    return ctx.finish(
        {
            "checkpointer_connected": cp_ok,
            "store_connected": store_ok,
            "checkpointer_setup": cp_setup,
            "store_setup": store_setup,
            "checkpointer_backend": info["checkpointer_backend"],
            "store_backend": info.get("store_backend"),
            "checkpointer_uri_redacted": info["checkpointer_uri_redacted"],
            "store_uri_redacted": info.get("store_uri_redacted"),
            "read_only": info["read_only"],
            "has_store": info["has_store"],
            "warning": "; ".join(warnings) if warnings else None,
            "package_versions": versions,
        },
        profile=profile_name,
    )


def list_profiles(ctx: ToolContext) -> dict:
    profiles = ctx.profiles.list_profiles()
    active = ctx.profiles.active_profile_name()
    return ctx.finish(
        {"profiles": profiles, "active_profile": active},
        profile=active,
    )
