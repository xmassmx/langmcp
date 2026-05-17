"""Thread summarization and checkpoint comparison."""

from __future__ import annotations

from typing import Any

from langmcp.checkpoint_utils import extract_messages


def _message_role(msg: Any) -> str:
    if isinstance(msg, dict):
        if msg.get("type"):
            return str(msg["type"])
        if msg.get("role"):
            return str(msg["role"])
        return msg.get("id", "unknown")
    msg_type = getattr(msg, "type", None)
    if msg_type:
        return str(msg_type)
    return type(msg).__name__


def _message_content(msg: Any) -> str:
    if isinstance(msg, dict):
        content = msg.get("content", "")
    else:
        content = getattr(msg, "content", "")
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("text", block)))
            else:
                parts.append(str(block))
        return " ".join(parts)
    return str(content) if content is not None else ""


def _tool_calls(msg: Any) -> list[dict[str, Any]]:
    if isinstance(msg, dict):
        tc = msg.get("tool_calls") or msg.get("additional_kwargs", {}).get("tool_calls")
    else:
        tc = getattr(msg, "tool_calls", None)
    if not tc:
        return []
    result = []
    for call in tc:
        if isinstance(call, dict):
            result.append(
                {
                    "name": call.get("name") or call.get("function", {}).get("name"),
                    "id": call.get("id"),
                }
            )
        else:
            result.append({"name": getattr(call, "name", None), "id": getattr(call, "id", None)})
    return result


def summarize_thread_messages(values: dict[str, Any]) -> dict[str, Any]:
    messages = extract_messages(values)
    entries = []
    last_user = None
    last_assistant = None
    for msg in messages:
        role = _message_role(msg)
        content = _message_content(msg)
        entry: dict[str, Any] = {
            "role": role,
            "content_preview": content[:500] + ("..." if len(content) > 500 else ""),
        }
        tools = _tool_calls(msg)
        if tools:
            entry["tool_calls"] = tools
        entries.append(entry)
        role_lower = role.lower()
        if "human" in role_lower or role_lower == "user":
            last_user = content[:200]
        if "ai" in role_lower or role_lower == "assistant":
            last_assistant = content[:200]
    return {
        "message_count": len(messages),
        "transcript": entries,
        "last_user_message": last_user,
        "last_assistant_message": last_assistant,
    }


def compare_checkpoint_values(
    values_a: dict[str, Any],
    values_b: dict[str, Any],
) -> dict[str, Any]:
    keys_a = set(values_a.keys()) if isinstance(values_a, dict) else set()
    keys_b = set(values_b.keys()) if isinstance(values_b, dict) else set()
    added = sorted(keys_b - keys_a)
    removed = sorted(keys_a - keys_b)
    changed = []
    for key in sorted(keys_a & keys_b):
        try:
            if values_a[key] != values_b[key]:
                changed.append(key)
        except Exception:
            changed.append(key)
    msgs_a = extract_messages(values_a)
    msgs_b = extract_messages(values_b)
    return {
        "added_keys": added,
        "removed_keys": removed,
        "changed_keys": changed,
        "message_count_a": len(msgs_a),
        "message_count_b": len(msgs_b),
        "message_count_delta": len(msgs_b) - len(msgs_a),
    }
