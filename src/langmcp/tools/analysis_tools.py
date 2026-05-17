"""Analysis MCP tools."""

from __future__ import annotations

from langmcp.analysis.context import analyze_context_window
from langmcp.analysis.memory import analyze_memory_gaps
from langmcp.checkpoint_utils import checkpoint_tuple_to_snapshot, thread_config
from langmcp.tools.context import ToolContext


def analyze_context_window_tool(
    ctx: ToolContext,
    thread_id: str,
    *,
    profile: str | None = None,
    model_hint: str | None = None,
) -> dict:
    bundle = ctx.bundle(profile)
    try:
        tup = bundle.checkpointer.get_tuple(thread_config(thread_id))
        snap = checkpoint_tuple_to_snapshot(tup)
        values = snap.get("values", {}) if isinstance(snap, dict) else {}
        analysis = analyze_context_window(values, model_hint=model_hint)
        return ctx.finish(
            {"thread_id": thread_id, **analysis},
            profile=bundle.profile_name,
        )
    finally:
        bundle.close()


def analyze_memory_gaps_tool(
    ctx: ToolContext,
    thread_id: str,
    user_id: str,
    *,
    profile: str | None = None,
    expected_namespace: str | None = None,
) -> dict:
    bundle = ctx.bundle(profile)
    err = ctx.require_store(bundle)
    if err:
        bundle.close()
        return ctx.finish(err, profile=bundle.profile_name)
    try:
        tup = bundle.checkpointer.get_tuple(thread_config(thread_id))
        snap = checkpoint_tuple_to_snapshot(tup)
        metadata = snap.get("metadata", {}) if isinstance(snap, dict) else {}
        config = snap.get("config", {}) if isinstance(snap, dict) else {}
        configurable = config.get("configurable", {}) if isinstance(config, dict) else {}
        ns: tuple[str, ...] | None = None
        if expected_namespace:
            ns = tuple(p for p in expected_namespace.split("/") if p)
        elif user_id:
            ns = (user_id,)
        items = bundle.store.search(ns or (user_id,), limit=20, offset=0)
        analysis = analyze_memory_gaps(
            thread_metadata=metadata if isinstance(metadata, dict) else {},
            configurable=configurable if isinstance(configurable, dict) else {},
            user_id=user_id,
            store_items=items,
            expected_namespace=ns,
        )
        return ctx.finish(
            {"thread_id": thread_id, **analysis},
            profile=bundle.profile_name,
        )
    finally:
        bundle.close()
