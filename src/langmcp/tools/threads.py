"""Thread listing and state tools."""

from __future__ import annotations

from langmcp.checkpoint_utils import checkpoint_tuple_to_snapshot, thread_config
from langmcp.discovery import list_threads_for_profile
from langmcp.tools.context import ToolContext


def list_threads(
    ctx: ToolContext,
    *,
    profile: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    profile_name, cfg = ctx.profiles.get_profile(profile)
    data = list_threads_for_profile(
        profile_name,
        cfg.checkpointer,
        limit=limit,
        offset=offset,
    )
    if "error" in data:
        return ctx.finish(data, profile=profile_name)
    return ctx.finish(data, profile=profile_name)


def get_thread_state(
    ctx: ToolContext,
    thread_id: str,
    *,
    profile: str | None = None,
    checkpoint_id: str | None = None,
) -> dict:
    bundle, err = ctx.open_bundle(profile)
    if err is not None:
        return ctx.finish_connection_error(err, profile=profile)
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
