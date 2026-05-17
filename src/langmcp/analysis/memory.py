"""Long-term memory gap analysis."""

from __future__ import annotations

from typing import Any


def analyze_memory_gaps(
    *,
    thread_metadata: dict[str, Any],
    configurable: dict[str, Any],
    user_id: str,
    store_items: list[Any],
    expected_namespace: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    hints: list[dict[str, str]] = []
    meta_user = None
    if isinstance(thread_metadata, dict):
        meta_user = thread_metadata.get("user_id")
    cfg_user = configurable.get("user_id") if isinstance(configurable, dict) else None
    resolved_user = user_id or meta_user or cfg_user

    ns = expected_namespace or (resolved_user,) if resolved_user else ()
    if resolved_user and not store_items:
        hints.append(
            {
                "code": "empty_store_for_user",
                "message": (
                    f"No store items found under namespace prefix {ns!r}. "
                    "Verify the graph compiles with store=, user_id is in configurable, "
                    "and semantic indexing is enabled if using vector search."
                ),
            }
        )
    if meta_user and meta_user != user_id:
        hints.append(
            {
                "code": "user_id_mismatch",
                "message": (
                    f"Argument user_id={user_id!r} differs from checkpoint metadata "
                    f"user_id={meta_user!r}."
                ),
            }
        )
    if not resolved_user:
        hints.append(
            {
                "code": "missing_user_id",
                "message": "No user_id in arguments, metadata, or configurable.",
            }
        )
    return {
        "user_id": resolved_user,
        "namespace_checked": list(ns),
        "store_item_count": len(store_items),
        "hints": hints,
    }


def summarize_user_memory_items(
    user_id: str,
    items: list[Any],
    *,
    application_context: str | None = None,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        ns = getattr(item, "namespace", None) or (
            item.get("namespace") if isinstance(item, dict) else ()
        )
        key = getattr(item, "key", None) or (item.get("key") if isinstance(item, dict) else "")
        value = getattr(item, "value", None) or (
            item.get("value") if isinstance(item, dict) else None
        )
        ns_key = "/".join(str(x) for x in ns) if ns else "(root)"
        preview = str(value)[:200] if value is not None else ""
        grouped.setdefault(ns_key, []).append({"key": key, "value_preview": preview})
    return {
        "user_id": user_id,
        "application_context": application_context,
        "namespace_groups": grouped,
        "total_items": len(items),
    }
