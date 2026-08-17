"""FastMCP stdio server with all v0.1 read-only tools, resources, and prompts."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult

from langmcp.apps.inspector import TOOL_UI_META, apps_enabled, register_inspector
from langmcp.apps.responses import app_tool_result, threads_list_summary
from langmcp.profiles import ProfileManager
from langmcp.tools import analysis_tools, checkpoints, health, store, threads
from langmcp.tools.context import ToolContext

_mcp: FastMCP | None = None
_ctx: ToolContext | None = None


def create_mcp(profiles: ProfileManager) -> FastMCP:
    global _mcp, _ctx
    mcp = FastMCP("langmcp")
    ctx = ToolContext(profiles)
    _mcp = mcp
    _ctx = ctx

    @mcp.tool()
    def health_check(profile: str | None = None) -> dict:
        """Check connectivity and setup status for a profile (secrets redacted)."""
        return health.health_check(ctx, profile)

    @mcp.tool()
    def list_profiles() -> dict:
        """List configured profile names and backend types (no secrets)."""
        return health.list_profiles(ctx)

    if apps_enabled():

        @mcp.tool(meta=TOOL_UI_META)
        def list_threads(
            profile: str | None = None,
            limit: int = 50,
            offset: int = 0,
        ) -> CallToolResult:
            """List thread IDs discovered from the checkpointer backend."""
            payload = threads.list_threads(ctx, profile=profile, limit=limit, offset=offset)
            rows = payload.get("threads", [])
            count = len(rows) if isinstance(rows, list) else 0
            active = str(payload.get("profile", ctx.profiles.active_profile_name(profile)))
            return app_tool_result(
                payload,
                summary=threads_list_summary(
                    count,
                    active,
                    truncated=bool(payload.get("truncated")),
                ),
            )

    else:

        @mcp.tool()
        def list_threads(
            profile: str | None = None,
            limit: int = 50,
            offset: int = 0,
        ) -> dict:
            """List thread IDs discovered from the checkpointer backend."""
            return threads.list_threads(ctx, profile=profile, limit=limit, offset=offset)

    @mcp.tool()
    def get_thread_state(
        thread_id: str,
        checkpoint_id: str | None = None,
        profile: str | None = None,
    ) -> dict:
        """Get latest or specific checkpoint state for a thread."""
        return threads.get_thread_state(
            ctx, thread_id, profile=profile, checkpoint_id=checkpoint_id
        )

    @mcp.tool()
    def list_checkpoint_history(
        thread_id: str,
        limit: int = 20,
        page: int = 1,
        profile: str | None = None,
    ) -> dict:
        """List checkpoint history for a thread (paginated)."""
        return checkpoints.list_checkpoint_history(
            ctx, thread_id, profile=profile, limit=limit, page=page
        )

    @mcp.tool()
    def get_checkpoint(
        thread_id: str,
        checkpoint_id: str,
        profile: str | None = None,
    ) -> dict:
        """Get full state snapshot for a specific checkpoint."""
        return checkpoints.get_checkpoint(ctx, thread_id, checkpoint_id, profile=profile)

    @mcp.tool()
    def compare_checkpoints(
        thread_id: str,
        checkpoint_id_a: str,
        checkpoint_id_b: str,
        profile: str | None = None,
    ) -> dict:
        """Compare values between two checkpoints on a thread."""
        return checkpoints.compare_checkpoints(
            ctx,
            thread_id,
            checkpoint_id_a,
            checkpoint_id_b,
            profile=profile,
        )

    @mcp.tool()
    def summarize_thread(
        thread_id: str,
        profile: str | None = None,
        page: int = 1,
    ) -> dict:
        """Human-oriented transcript summary for a thread."""
        return checkpoints.summarize_thread(ctx, thread_id, profile=profile, page=page)

    @mcp.tool()
    def analyze_context_window(
        thread_id: str,
        profile: str | None = None,
        model_hint: str | None = None,
    ) -> dict:
        """Estimate token usage and flag large context windows."""
        return analysis_tools.analyze_context_window_tool(
            ctx, thread_id, profile=profile, model_hint=model_hint
        )

    @mcp.tool()
    def analyze_memory_gaps(
        thread_id: str,
        user_id: str,
        expected_namespace: str | None = None,
        profile: str | None = None,
    ) -> dict:
        """Detect likely long-term memory misconfiguration for a user/thread."""
        return analysis_tools.analyze_memory_gaps_tool(
            ctx,
            thread_id,
            user_id,
            profile=profile,
            expected_namespace=expected_namespace,
        )

    @mcp.tool()
    def list_namespaces(
        prefix: str | None = None,
        max_depth: int | None = None,
        profile: str | None = None,
    ) -> dict:
        """List store namespaces (PostgreSQL store only in v0.1)."""
        return store.list_namespaces(ctx, profile=profile, prefix=prefix, max_depth=max_depth)

    @mcp.tool()
    def search_store(
        namespace_prefix: str,
        query: str | None = None,
        filter: str | None = None,
        limit: int = 10,
        offset: int = 0,
        profile: str | None = None,
    ) -> dict:
        """Search the long-term memory store under a namespace prefix."""
        return store.search_store(
            ctx,
            namespace_prefix,
            profile=profile,
            query=query,
            filter=filter,
            limit=limit,
            offset=offset,
        )

    @mcp.tool()
    def get_store_item(
        namespace: str,
        key: str,
        profile: str | None = None,
    ) -> dict:
        """Get a single store item by namespace and key."""
        return store.get_store_item(ctx, namespace, key, profile=profile)

    @mcp.tool()
    def summarize_user_memory(
        user_id: str,
        application_context: str | None = None,
        profile: str | None = None,
    ) -> dict:
        """Summarize store items grouped under a user_id namespace prefix."""
        return store.summarize_user_memory(
            ctx, user_id, profile=profile, application_context=application_context
        )

    @mcp.resource(
        "langmcp://profiles",
        name="profiles",
        title="LangMCP Profiles",
        description="Configured LangMCP profile names, backend types, and active profile.",
        mime_type="application/json",
    )
    def profiles_resource() -> dict:
        """Configured profiles and active profile."""
        return health.list_profiles(ctx)

    @mcp.resource(
        "langmcp://profiles/{profile}/health",
        name="profile_health",
        title="Profile Health",
        description="Connectivity and setup status for a configured profile.",
        mime_type="application/json",
    )
    def profile_health_resource(profile: str) -> dict:
        """Connectivity and setup status for a profile."""
        return health.health_check(ctx, profile)

    @mcp.resource(
        "langmcp://profiles/{profile}/threads",
        name="profile_threads",
        title="Profile Threads",
        description="Discovered LangGraph thread IDs for a profile.",
        mime_type="application/json",
    )
    def profile_threads_resource(profile: str) -> dict:
        """Discovered thread IDs for a profile."""
        return threads.list_threads(ctx, profile=profile)

    @mcp.resource(
        "langmcp://profiles/{profile}/threads/{thread_id}/state",
        name="thread_state",
        title="Thread State",
        description="Latest checkpoint state for a LangGraph thread.",
        mime_type="application/json",
    )
    def thread_state_resource(profile: str, thread_id: str) -> dict:
        """Latest checkpoint state for a thread."""
        return threads.get_thread_state(ctx, thread_id, profile=profile)

    @mcp.resource(
        "langmcp://profiles/{profile}/threads/{thread_id}/summary",
        name="thread_summary",
        title="Thread Summary",
        description="Transcript-style summary for a LangGraph thread.",
        mime_type="application/json",
    )
    def thread_summary_resource(profile: str, thread_id: str) -> dict:
        """Transcript-style summary for a thread."""
        return checkpoints.summarize_thread(ctx, thread_id, profile=profile)

    @mcp.resource(
        "langmcp://profiles/{profile}/threads/{thread_id}/checkpoints",
        name="checkpoint_history",
        title="Checkpoint History",
        description="Recent checkpoint history for a LangGraph thread.",
        mime_type="application/json",
    )
    def checkpoint_history_resource(profile: str, thread_id: str) -> dict:
        """Recent checkpoint history for a thread."""
        return checkpoints.list_checkpoint_history(ctx, thread_id, profile=profile)

    @mcp.resource(
        "langmcp://profiles/{profile}/threads/{thread_id}/checkpoints/{checkpoint_id}",
        name="checkpoint_snapshot",
        title="Checkpoint Snapshot",
        description="Full state snapshot for a specific LangGraph checkpoint.",
        mime_type="application/json",
    )
    def checkpoint_snapshot_resource(profile: str, thread_id: str, checkpoint_id: str) -> dict:
        """Full state snapshot for a checkpoint."""
        return checkpoints.get_checkpoint(ctx, thread_id, checkpoint_id, profile=profile)

    @mcp.resource(
        "langmcp://profiles/{profile}/threads/{thread_id}/context-analysis",
        name="thread_context_analysis",
        title="Thread Context Analysis",
        description="Token estimate and context-window warnings for a thread.",
        mime_type="application/json",
    )
    def thread_context_analysis_resource(profile: str, thread_id: str) -> dict:
        """Context-window analysis for a thread."""
        return analysis_tools.analyze_context_window_tool(ctx, thread_id, profile=profile)

    @mcp.resource(
        "langmcp://profiles/{profile}/store/namespaces",
        name="store_namespaces",
        title="Store Namespaces",
        description="Long-term memory store namespaces for a profile.",
        mime_type="application/json",
    )
    def store_namespaces_resource(profile: str) -> dict:
        """Long-term memory store namespaces for a profile."""
        return store.list_namespaces(ctx, profile=profile)

    @mcp.resource(
        "langmcp://profiles/{profile}/store/items/{namespace}/{key}",
        name="store_item",
        title="Store Item",
        description="A single long-term memory store item by namespace and key.",
        mime_type="application/json",
    )
    def store_item_resource(profile: str, namespace: str, key: str) -> dict:
        """Long-term memory store item by namespace and key."""
        return store.get_store_item(ctx, namespace, key, profile=profile)

    @mcp.resource(
        "langmcp://profiles/{profile}/users/{user_id}/memory-summary",
        name="user_memory_summary",
        title="User Memory Summary",
        description="Grouped long-term memory summary for a user namespace.",
        mime_type="application/json",
    )
    def user_memory_summary_resource(profile: str, user_id: str) -> dict:
        """Grouped long-term memory summary for a user namespace."""
        return store.summarize_user_memory(ctx, user_id, profile=profile)

    @mcp.prompt()
    def debug_thread(
        thread_id: str,
        profile: str | None = None,
        user_id: str | None = None,
        model_hint: str | None = None,
    ) -> str:
        """Investigate one LangGraph thread using LangMCP inspection data."""
        profile_part = f" profile `{profile}`" if profile else " the active LangMCP profile"
        user_part = (
            f"\n- Run `analyze_memory_gaps` for user_id `{user_id}`."
            if user_id
            else "\n- If a user_id is evident in the thread metadata, check memory gaps for it."
        )
        model_part = f" with model_hint `{model_hint}`" if model_hint else ""
        return f"""Investigate LangGraph thread `{thread_id}` using{profile_part}.

Use the available LangMCP tools/resources to:
- Read the thread summary resource or call `summarize_thread`.
- Inspect recent checkpoint history.
- Analyze context-window pressure{model_part}.{user_part}
- Compare evidence from checkpoints, thread state, and memory before deciding.

Return a concise diagnostic report with:
- verdict
- evidence
- likely cause
- next action"""

    @mcp.prompt()
    def investigate_memory_gap(
        thread_id: str,
        user_id: str,
        profile: str | None = None,
        expected_namespace: str | None = None,
    ) -> str:
        """Check whether thread state and long-term memory are aligned."""
        profile_part = f" profile `{profile}`" if profile else " the active LangMCP profile"
        namespace_part = (
            f" Expected namespace: `{expected_namespace}`."
            if expected_namespace
            else " Infer the expected namespace if possible."
        )
        target = f"thread `{thread_id}` and user `{user_id}` using{profile_part}"
        return f"""Investigate a possible LangGraph memory gap for {target}.

{namespace_part}

Use `analyze_memory_gaps`, `summarize_thread`, and `summarize_user_memory`.
Decide whether this is a thread/config issue, store namespace issue, missing write,
or expected empty memory.
Return the verdict with concrete evidence."""

    @mcp.prompt()
    def compare_thread_checkpoints(
        thread_id: str,
        checkpoint_id_a: str,
        checkpoint_id_b: str,
        profile: str | None = None,
    ) -> str:
        """Explain behavioral differences between two checkpoints."""
        profile_part = f" profile `{profile}`" if profile else " the active LangMCP profile"
        target = (
            f"`{checkpoint_id_a}` and `{checkpoint_id_b}` for thread `{thread_id}` "
            f"using{profile_part}"
        )
        return f"""Compare checkpoints {target}.

Use `compare_checkpoints`, inspect either checkpoint if needed, and explain:
- changed state keys
- message count delta
- user-visible behavior change
- whether the change looks expected or suspicious"""

    if apps_enabled():
        register_inspector(mcp, ctx)

    @mcp.prompt()
    def inspect_user_memory(
        user_id: str,
        profile: str | None = None,
        application_context: str | None = None,
    ) -> str:
        """Summarize and sanity-check long-term memory for one user."""
        profile_part = f" profile `{profile}`" if profile else " the active LangMCP profile"
        context_part = (
            f" Application context: {application_context}"
            if application_context
            else " Note any assumptions you make about application context."
        )
        return f"""Inspect long-term memory for user `{user_id}` using{profile_part}.

{context_part}

Use `summarize_user_memory`, `list_namespaces`, and targeted
`search_store`/`get_store_item` calls as needed.
Return:
- useful remembered facts
- stale or risky facts
- namespace/key anomalies
- recommended cleanup or follow-up checks"""

    return mcp


def dev_mcp() -> FastMCP:
    """Factory entry point for `fastmcp dev apps src/langmcp/server.py:dev_mcp`."""
    return create_mcp(ProfileManager())


def run_server(profiles: ProfileManager) -> None:
    mcp = create_mcp(profiles)
    mcp.run(transport="stdio")
