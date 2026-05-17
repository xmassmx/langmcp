"""Health and profile listing tools."""

from __future__ import annotations

import importlib.metadata

from langmcp.tools.context import ToolContext


def health_check(ctx: ToolContext, profile: str | None = None) -> dict:
    info = ctx.profiles.profile_health_info(profile)
    profile_name = info["profile"]
    bundle = ctx.bundle(profile_name)
    cp_ok = False
    store_ok = None
    cp_setup = False
    store_setup = None
    warning = None
    try:
        bundle.checkpointer.setup()
        cp_setup = True
        bundle.checkpointer.get_tuple(
            {"configurable": {"thread_id": "__langmcp_health__"}}
        )
        cp_ok = True
    except Exception as exc:
        warning = f"Checkpointer: {exc}"
    finally:
        if bundle.store:
            try:
                bundle.store.setup()
                store_setup = True
                store_ok = True
            except Exception as exc:
                store_ok = False
                warning = (warning or "") + f" Store: {exc}"
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
            "warning": warning,
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
