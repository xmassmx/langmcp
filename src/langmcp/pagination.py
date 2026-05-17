"""Character-budget pagination for tool responses."""

from __future__ import annotations

import json
from typing import Any


def truncate_value(value: Any, max_chars: int) -> tuple[Any, bool]:
    """Truncate a JSON-serializable value to fit max_chars."""
    serialized = json.dumps(value, default=str)
    if len(serialized) <= max_chars:
        return value, False
    if isinstance(value, str):
        remaining = max(0, len(value) - max_chars)
        return value[: max_chars - 20] + f"(+{remaining} chars)", True
    if isinstance(value, list):
        truncated_list: list[Any] = []
        used = 2
        was_truncated = False
        for item in value:
            item_s = json.dumps(item, default=str)
            if used + len(item_s) + 1 > max_chars:
                was_truncated = True
                break
            truncated_list.append(item)
            used += len(item_s) + 1
        return truncated_list, was_truncated
    if isinstance(value, dict):
        truncated_dict: dict[str, Any] = {}
        used = 2
        was_truncated = False
        for k, v in value.items():
            entry_s = json.dumps({k: v}, default=str)
            if used + len(entry_s) > max_chars:
                was_truncated = True
                break
            truncated_dict[k] = v
            used += len(entry_s)
        return truncated_dict, was_truncated
    text = serialized[: max_chars - 20] + f"(+{len(serialized) - max_chars} chars)"
    return text, True


def paginate_items(
    items: list[Any],
    *,
    page: int = 1,
    max_chars: int = 25000,
) -> dict[str, Any]:
    """Paginate a list by character budget (LangSmith-style)."""
    if page < 1:
        page = 1
    pages: list[list[Any]] = []
    current: list[Any] = []
    current_size = 2
    for item in items:
        item_size = len(json.dumps(item, default=str))
        if current and current_size + item_size + 1 > max_chars:
            pages.append(current)
            current = []
            current_size = 2
        current.append(item)
        current_size += item_size + 1
    if current:
        pages.append(current)
    if not pages:
        pages = [[]]
    total_pages = len(pages)
    page = min(page, total_pages)
    page_items = pages[page - 1]
    serialized = json.dumps(page_items, default=str)
    return {
        "items": page_items,
        "page": page,
        "total_pages": total_pages,
        "truncated": len(items) > len(page_items) or total_pages > 1,
        "total_items": len(items),
        "max_chars": max_chars,
        "response_chars": len(serialized),
    }


def wrap_response(
    data: dict[str, Any],
    *,
    profile: str,
    max_chars: int,
    truncated: bool = False,
) -> dict[str, Any]:
    body, was_truncated = truncate_value(data, max_chars)
    if isinstance(body, dict):
        result = {**body}
    else:
        result = {"data": body}
    result["profile"] = profile
    result["truncated"] = truncated or was_truncated
    return result
