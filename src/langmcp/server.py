"""FastMCP stdio server with all v0.1 read-only tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

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
        return checkpoints.get_checkpoint(
            ctx, thread_id, checkpoint_id, profile=profile
        )

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
        return checkpoints.summarize_thread(
            ctx, thread_id, profile=profile, page=page
        )

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
        return store.list_namespaces(
            ctx, profile=profile, prefix=prefix, max_depth=max_depth
        )

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

    return mcp


def run_server(profiles: ProfileManager) -> None:
    mcp = create_mcp(profiles)
    mcp.run(transport="stdio")
