"""LangMCP Inspector MCP App — entry tool, UI resource, and iframe-only backend tools."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP

from langmcp.tools import analysis_tools, checkpoints, health, store, threads
from langmcp.tools.context import ToolContext

INSPECTOR_URI = "ui://langmcp/inspector.html"
INSPECTOR_MIME = "text/html;profile=mcp-app"
TOOL_UI_META = {"ui": {"resourceUri": INSPECTOR_URI}}
APP_ONLY_META = {"ui": {"visibility": ["app"]}}

InspectorView = Literal["health", "threads", "thread", "compare", "memory"]
FALSEY_ENV_VALUES = {"0", "false", "no", "off"}


def apps_enabled() -> bool:
    """Return whether MCP Apps should be registered for this server process."""
    raw = os.environ.get("LANGMCP_APPS_ENABLED")
    if raw is None:
        return True
    return raw.strip().lower() not in FALSEY_ENV_VALUES


def _inspector_html_path() -> Path:
    return Path(__file__).with_name("inspector.html")


def load_inspector_html() -> str:
    path = _inspector_html_path()
    if not path.is_file():
        msg = (
            f"Inspector UI bundle missing at {path}. "
            "Run: cd apps/inspector && npm install && npm run build"
        )
        raise FileNotFoundError(msg)
    return path.read_text(encoding="utf-8")


def _build_health_seed(ctx: ToolContext, profile: str | None) -> dict:
    profiles_payload = health.list_profiles(ctx)
    profile_rows = profiles_payload.get("profiles", [])
    checks: list[dict] = []
    errors: list[str] = []
    for row in profile_rows:
        name = row["name"]
        try:
            checks.append(health.health_check(ctx, name))
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(f"health_check({name}): {exc}")
    active = ctx.profiles.active_profile_name(profile)
    return {
        "profiles": profiles_payload,
        "health_checks": checks,
        "active_profile": active,
        "errors": errors,
    }


def _build_threads_seed(
    ctx: ToolContext,
    profile: str | None,
    *,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    return threads.list_threads(ctx, profile=profile, limit=limit, offset=offset)


def _capture(errors: list[str], label: str, fn) -> dict | None:
    try:
        return fn()
    except Exception as exc:  # pragma: no cover - defensive guard for UI seeds
        errors.append(f"{label}: {exc}")
        return None


def _build_thread_seed(
    ctx: ToolContext,
    thread_id: str | None,
    profile: str | None,
    *,
    user_id: str | None = None,
    namespace_prefix: str | None = None,
    errors: list[str],
) -> dict:
    if not thread_id:
        errors.append("thread_id is required for the Thread Debugger.")
        return {}

    seed: dict = {"thread_id": thread_id}
    summary = _capture(
        errors,
        "summarize_thread",
        lambda: checkpoints.summarize_thread(ctx, thread_id, profile=profile),
    )
    history = _capture(
        errors,
        "list_checkpoint_history",
        lambda: checkpoints.list_checkpoint_history(ctx, thread_id, profile=profile),
    )
    context = _capture(
        errors,
        "analyze_context_window",
        lambda: analysis_tools.analyze_context_window_tool(ctx, thread_id, profile=profile),
    )
    state = _capture(
        errors,
        "get_thread_state",
        lambda: threads.get_thread_state(ctx, thread_id, profile=profile),
    )
    for key, value in (
        ("summary", summary),
        ("history", history),
        ("context", context),
        ("state", state),
    ):
        if value is not None:
            seed[key] = value

    if user_id:
        memory = _capture(
            errors,
            "summarize_user_memory",
            lambda: store.summarize_user_memory(ctx, user_id, profile=profile),
        )
        gaps = _capture(
            errors,
            "analyze_memory_gaps",
            lambda: analysis_tools.analyze_memory_gaps_tool(
                ctx,
                thread_id,
                user_id,
                profile=profile,
                expected_namespace=namespace_prefix,
            ),
        )
        if memory is not None:
            seed["memory"] = memory
        if gaps is not None:
            seed["memory_gaps"] = gaps
    return seed


def build_inspector_payload(
    ctx: ToolContext,
    view: InspectorView,
    profile: str | None = None,
    *,
    thread_id: str | None = None,
    user_id: str | None = None,
    namespace_prefix: str | None = None,
) -> dict:
    active = ctx.profiles.active_profile_name(profile)
    errors: list[str] = []
    seed: dict = {}

    if view == "health":
        health_seed = _build_health_seed(ctx, profile)
        seed = {
            "profiles": health_seed["profiles"],
            "health_checks": health_seed["health_checks"],
        }
        errors.extend(health_seed.get("errors", []))
    elif view == "threads":
        seed = {"threads": _build_threads_seed(ctx, profile)}
    elif view == "thread":
        profiles_payload = health.list_profiles(ctx)
        seed = {
            "profiles": profiles_payload,
            **_build_thread_seed(
                ctx,
                thread_id,
                profile,
                user_id=user_id,
                namespace_prefix=namespace_prefix,
                errors=errors,
            ),
        }
    else:
        errors.append(
            f"View '{view}' is not a top-level inspector screen. Use the Thread Debugger."
        )

    return {
        "view": view,
        "profile": active,
        "read_only": True,
        "seed": seed,
        "errors": errors,
    }


def register_inspector(mcp: FastMCP, ctx: ToolContext) -> None:
    """Register inspector UI resource, entry tool, and app-only backend tools."""

    @mcp.resource(
        INSPECTOR_URI,
        name="inspector_ui",
        title="LangMCP Inspector UI",
        description="Bundled HTML for the LangMCP Inspector MCP App.",
        mime_type=INSPECTOR_MIME,
    )
    def inspector_ui_resource() -> str:
        return load_inspector_html()

    @mcp.tool(
        title="Show Inspector",
        description=(
            "Open the LangMCP Inspector MCP App (health, threads, debugger). "
            "Prefer this over dumping raw JSON when inspecting LangGraph persistence."
        ),
        meta=TOOL_UI_META,
    )
    def show_inspector(
        view: InspectorView = "health",
        profile: str | None = None,
        thread_id: str | None = None,
        checkpoint_id_a: str | None = None,
        checkpoint_id_b: str | None = None,
        user_id: str | None = None,
        namespace_prefix: str | None = None,
    ) -> dict:
        """Open the in-chat inspector for LangGraph checkpoint and store debugging."""
        del checkpoint_id_a, checkpoint_id_b
        return build_inspector_payload(
            ctx,
            view,
            profile,
            thread_id=thread_id,
            user_id=user_id,
            namespace_prefix=namespace_prefix,
        )

    @mcp.tool(meta=APP_ONLY_META)
    def __ui_list_threads(
        profile: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """List threads (iframe-only)."""
        return threads.list_threads(ctx, profile=profile, limit=limit, offset=offset)

    @mcp.tool(meta=APP_ONLY_META)
    def __ui_health_check(profile: str | None = None) -> dict:
        """Health check for a profile (iframe-only)."""
        return health.health_check(ctx, profile)

    @mcp.tool(meta=APP_ONLY_META)
    def __ui_list_profiles() -> dict:
        """List configured profiles (iframe-only)."""
        return health.list_profiles(ctx)

    @mcp.tool(meta=APP_ONLY_META)
    def __ui_summarize_thread(
        thread_id: str,
        profile: str | None = None,
        page: int = 1,
    ) -> dict:
        """Summarize a thread transcript (iframe-only)."""
        return checkpoints.summarize_thread(ctx, thread_id, profile=profile, page=page)

    @mcp.tool(meta=APP_ONLY_META)
    def __ui_list_checkpoint_history(
        thread_id: str,
        limit: int = 20,
        page: int = 1,
        profile: str | None = None,
    ) -> dict:
        """List checkpoint history for a thread (iframe-only)."""
        return checkpoints.list_checkpoint_history(
            ctx, thread_id, profile=profile, limit=limit, page=page
        )

    @mcp.tool(meta=APP_ONLY_META)
    def __ui_get_checkpoint(
        thread_id: str,
        checkpoint_id: str,
        profile: str | None = None,
    ) -> dict:
        """Get a checkpoint snapshot (iframe-only)."""
        return checkpoints.get_checkpoint(ctx, thread_id, checkpoint_id, profile=profile)

    @mcp.tool(meta=APP_ONLY_META)
    def __ui_get_thread_state(
        thread_id: str,
        checkpoint_id: str | None = None,
        profile: str | None = None,
    ) -> dict:
        """Get thread state (iframe-only)."""
        return threads.get_thread_state(
            ctx, thread_id, checkpoint_id=checkpoint_id, profile=profile
        )

    @mcp.tool(meta=APP_ONLY_META)
    def __ui_analyze_context_window(
        thread_id: str,
        profile: str | None = None,
        model_hint: str | None = None,
    ) -> dict:
        """Analyze context pressure for a thread (iframe-only)."""
        return analysis_tools.analyze_context_window_tool(
            ctx, thread_id, profile=profile, model_hint=model_hint
        )

    @mcp.tool(meta=APP_ONLY_META)
    def __ui_compare_checkpoints(
        thread_id: str,
        checkpoint_id_a: str,
        checkpoint_id_b: str,
        profile: str | None = None,
    ) -> dict:
        """Compare two checkpoints (iframe-only)."""
        return checkpoints.compare_checkpoints(
            ctx,
            thread_id,
            checkpoint_id_a,
            checkpoint_id_b,
            profile=profile,
        )

    @mcp.tool(meta=APP_ONLY_META)
    def __ui_summarize_user_memory(
        user_id: str,
        application_context: str | None = None,
        profile: str | None = None,
    ) -> dict:
        """Summarize user memory (iframe-only)."""
        return store.summarize_user_memory(
            ctx, user_id, profile=profile, application_context=application_context
        )

    @mcp.tool(meta=APP_ONLY_META)
    def __ui_analyze_memory_gaps(
        thread_id: str,
        user_id: str,
        expected_namespace: str | None = None,
        profile: str | None = None,
    ) -> dict:
        """Analyze thread/store memory gaps (iframe-only)."""
        return analysis_tools.analyze_memory_gaps_tool(
            ctx,
            thread_id,
            user_id,
            profile=profile,
            expected_namespace=expected_namespace,
        )

    @mcp.tool(meta=APP_ONLY_META)
    def __ui_list_namespaces(
        prefix: str | None = None,
        max_depth: int | None = None,
        profile: str | None = None,
    ) -> dict:
        """List store namespaces for advanced lookup (iframe-only)."""
        return store.list_namespaces(ctx, profile=profile, prefix=prefix, max_depth=max_depth)

    @mcp.tool(meta=APP_ONLY_META)
    def __ui_search_store(
        namespace_prefix: str,
        query: str | None = None,
        filter: str | None = None,
        limit: int = 10,
        offset: int = 0,
        profile: str | None = None,
    ) -> dict:
        """Search store items for advanced lookup (iframe-only)."""
        return store.search_store(
            ctx,
            namespace_prefix,
            profile=profile,
            query=query,
            filter=filter,
            limit=limit,
            offset=offset,
        )

    @mcp.tool(meta=APP_ONLY_META)
    def __ui_get_store_item(
        namespace: str,
        key: str,
        profile: str | None = None,
    ) -> dict:
        """Get a store item for advanced lookup (iframe-only)."""
        return store.get_store_item(ctx, namespace, key, profile=profile)
