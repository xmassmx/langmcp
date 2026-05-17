"""Thread listing and state tools."""

from __future__ import annotations

from langmcp.checkpoint_utils import checkpoint_tuple_to_snapshot, thread_config
from langmcp.discovery import list_threads_for_uri
from langmcp.tools.context import ToolContext


def list_threads(
    ctx: ToolContext,
    *,
    profile: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    bundle = ctx.bundle(profile)
    try:
        threads, warning = list_threads_for_uri(
            bundle.checkpointer_uri,
            limit=limit,
            offset=offset,
        )
        data: dict = {"threads": threads, "limit": limit, "offset": offset}
        if warning:
            data["warning"] = warning
        return ctx.finish(data, profile=bundle.profile_name)
    finally:
        bundle.close()


def get_thread_state(
    ctx: ToolContext,
    thread_id: str,
    *,
    profile: str | None = None,
    checkpoint_id: str | None = None,
) -> dict:
    bundle = ctx.bundle(profile)
    try:
        config = thread_config(thread_id, checkpoint_id)
        tup = bundle.checkpointer.get_tuple(config)
        snapshot = checkpoint_tuple_to_snapshot(tup)
        return ctx.finish(
            {"thread_id": thread_id, "state": snapshot},
            profile=bundle.profile_name,
        )
    finally:
        bundle.close()
