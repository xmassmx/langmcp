"""Checkpoint history and comparison tools."""

from __future__ import annotations

from langmcp.analysis.thread import compare_checkpoint_values, summarize_thread_messages
from langmcp.checkpoint_utils import (
    checkpoint_to_summary,
    checkpoint_tuple_to_snapshot,
    thread_config,
)
from langmcp.pagination import paginate_items
from langmcp.tools.context import ToolContext


def list_checkpoint_history(
    ctx: ToolContext,
    thread_id: str,
    *,
    profile: str | None = None,
    limit: int = 20,
    page: int = 1,
) -> dict:
    bundle, conn_err = ctx.open_bundle(profile)
    if conn_err is not None:
        return ctx.finish_connection_error(conn_err, profile=profile)
    try:
        config = thread_config(thread_id)
        history = bundle.checkpointer.list_checkpoints(config, limit=limit)
        summaries = [checkpoint_to_summary(cp) for cp in history]
        paged = paginate_items(summaries, page=page, max_chars=ctx.max_chars())
        return ctx.finish(
            {
                "thread_id": thread_id,
                "checkpoints": paged["items"],
                "page": paged["page"],
                "total_pages": paged["total_pages"],
                "total_items": paged["total_items"],
            },
            profile=bundle.profile_name,
            truncated=paged["truncated"],
        )
    finally:
        bundle.close()


def get_checkpoint(
    ctx: ToolContext,
    thread_id: str,
    checkpoint_id: str,
    *,
    profile: str | None = None,
) -> dict:
    bundle, conn_err = ctx.open_bundle(profile)
    if conn_err is not None:
        return ctx.finish_connection_error(conn_err, profile=profile)
    try:
        config = thread_config(thread_id, checkpoint_id)
        tup = bundle.checkpointer.get_tuple(config)
        snapshot = checkpoint_tuple_to_snapshot(tup)
        return ctx.finish(
            {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
                "state": snapshot,
            },
            profile=bundle.profile_name,
        )
    finally:
        bundle.close()


def compare_checkpoints(
    ctx: ToolContext,
    thread_id: str,
    checkpoint_id_a: str,
    checkpoint_id_b: str,
    *,
    profile: str | None = None,
) -> dict:
    bundle, conn_err = ctx.open_bundle(profile)
    if conn_err is not None:
        return ctx.finish_connection_error(conn_err, profile=profile)
    try:
        tup_a = bundle.checkpointer.get_tuple(thread_config(thread_id, checkpoint_id_a))
        tup_b = bundle.checkpointer.get_tuple(thread_config(thread_id, checkpoint_id_b))
        snap_a = checkpoint_tuple_to_snapshot(tup_a)
        snap_b = checkpoint_tuple_to_snapshot(tup_b)
        values_a = snap_a.get("values", {}) if isinstance(snap_a, dict) else {}
        values_b = snap_b.get("values", {}) if isinstance(snap_b, dict) else {}
        diff = compare_checkpoint_values(values_a, values_b)
        return ctx.finish(
            {
                "thread_id": thread_id,
                "checkpoint_id_a": checkpoint_id_a,
                "checkpoint_id_b": checkpoint_id_b,
                "diff": diff,
            },
            profile=bundle.profile_name,
        )
    finally:
        bundle.close()


def summarize_thread(
    ctx: ToolContext,
    thread_id: str,
    *,
    profile: str | None = None,
    page: int = 1,
) -> dict:
    bundle, conn_err = ctx.open_bundle(profile)
    if conn_err is not None:
        return ctx.finish_connection_error(conn_err, profile=profile)
    try:
        tup = bundle.checkpointer.get_tuple(thread_config(thread_id))
        snap = checkpoint_tuple_to_snapshot(tup)
        values = snap.get("values", {}) if isinstance(snap, dict) else {}
        summary = summarize_thread_messages(values)
        paged = paginate_items(
            summary.get("transcript", []),
            page=page,
            max_chars=ctx.max_chars(),
        )
        return ctx.finish(
            {
                "thread_id": thread_id,
                "message_count": summary["message_count"],
                "last_user_message": summary.get("last_user_message"),
                "last_assistant_message": summary.get("last_assistant_message"),
                "transcript": paged["items"],
                "page": paged["page"],
                "total_pages": paged["total_pages"],
            },
            profile=bundle.profile_name,
            truncated=paged["truncated"],
        )
    finally:
        bundle.close()
