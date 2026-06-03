"""Long-term memory store tools."""

from __future__ import annotations

from typing import Any

from langmcp.analysis.memory import summarize_user_memory_items
from langmcp.tools.context import ToolContext


def _parse_namespace(prefix: str | None) -> tuple[str, ...] | None:
    if prefix is None:
        return None
    if not prefix:
        return ()
    return tuple(p.strip() for p in prefix.split("/") if p.strip())


def list_namespaces(
    ctx: ToolContext,
    *,
    profile: str | None = None,
    prefix: str | None = None,
    max_depth: int | None = None,
) -> dict:
    bundle, conn_err = ctx.open_bundle(profile)
    if conn_err is not None:
        return ctx.finish_connection_error(conn_err, profile=profile)
    err = ctx.require_store(bundle)
    if err:
        bundle.close()
        return ctx.finish(err, profile=bundle.profile_name)
    try:
        ns_prefix = _parse_namespace(prefix)
        namespaces = bundle.store.list_namespaces(prefix=ns_prefix, max_depth=max_depth)
        return ctx.finish(
            {"namespaces": [list(ns) for ns in namespaces]},
            profile=bundle.profile_name,
        )
    finally:
        bundle.close()


def search_store(
    ctx: ToolContext,
    namespace_prefix: str,
    *,
    profile: str | None = None,
    query: str | None = None,
    filter: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> dict:
    bundle, conn_err = ctx.open_bundle(profile)
    if conn_err is not None:
        return ctx.finish_connection_error(conn_err, profile=profile)
    err = ctx.require_store(bundle)
    if err:
        bundle.close()
        return ctx.finish(err, profile=bundle.profile_name)
    try:
        import json

        ns = _parse_namespace(namespace_prefix) or ()
        filter_dict: dict[str, Any] | None = None
        if filter:
            filter_dict = json.loads(filter)
        items = bundle.store.search(
            ns,
            query=query,
            filter=filter_dict,
            limit=limit,
            offset=offset,
        )
        previews = []
        for item in items:
            ns_val = getattr(item, "namespace", None) or (
                item.get("namespace") if isinstance(item, dict) else ()
            )
            key = getattr(item, "key", None) or (item.get("key") if isinstance(item, dict) else "")
            value = getattr(item, "value", None) or (
                item.get("value") if isinstance(item, dict) else None
            )
            updated = getattr(item, "updated_at", None) or (
                item.get("updated_at") if isinstance(item, dict) else None
            )
            value_str = str(value)
            previews.append(
                {
                    "namespace": list(ns_val) if ns_val else [],
                    "key": key,
                    "value_preview": value_str[:500] + ("..." if len(value_str) > 500 else ""),
                    "updated_at": str(updated) if updated else None,
                }
            )
        return ctx.finish(
            {"items": previews, "limit": limit, "offset": offset},
            profile=bundle.profile_name,
        )
    finally:
        bundle.close()


def get_store_item(
    ctx: ToolContext,
    namespace: str,
    key: str,
    *,
    profile: str | None = None,
) -> dict:
    bundle, conn_err = ctx.open_bundle(profile)
    if conn_err is not None:
        return ctx.finish_connection_error(conn_err, profile=profile)
    err = ctx.require_store(bundle)
    if err:
        bundle.close()
        return ctx.finish(err, profile=bundle.profile_name)
    try:
        ns = _parse_namespace(namespace) or ()
        item = bundle.store.get(ns, key)
        value = getattr(item, "value", None) if item is not None else None
        if value is None and isinstance(item, dict):
            value = item.get("value", item)
        return ctx.finish(
            {"namespace": list(ns), "key": key, "value": value},
            profile=bundle.profile_name,
        )
    finally:
        bundle.close()


def summarize_user_memory(
    ctx: ToolContext,
    user_id: str,
    *,
    profile: str | None = None,
    application_context: str | None = None,
) -> dict:
    bundle, conn_err = ctx.open_bundle(profile)
    if conn_err is not None:
        return ctx.finish_connection_error(conn_err, profile=profile)
    err = ctx.require_store(bundle)
    if err:
        bundle.close()
        return ctx.finish(err, profile=bundle.profile_name)
    try:
        items = bundle.store.search((user_id,), limit=100, offset=0)
        summary = summarize_user_memory_items(
            user_id,
            items,
            application_context=application_context,
        )
        return ctx.finish(summary, profile=bundle.profile_name)
    finally:
        bundle.close()
