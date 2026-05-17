"""Map LangGraph checkpoint tuples to JSON-friendly structures."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any


def _serialize(obj: Any) -> Any:
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(x) for x in obj]
    if hasattr(obj, "model_dump"):
        return _serialize(obj.model_dump())
    if hasattr(obj, "dict"):
        return _serialize(obj.dict())
    try:
        json.dumps(obj, default=str)
        return obj
    except (TypeError, ValueError):
        return str(obj)


def thread_config(thread_id: str, checkpoint_id: str | None = None) -> dict[str, Any]:
    cfg: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    if checkpoint_id:
        cfg["configurable"]["checkpoint_id"] = checkpoint_id
    return cfg


def checkpoint_tuple_to_snapshot(checkpoint_tuple: Any) -> dict[str, Any]:
    if checkpoint_tuple is None:
        return {"error": "not_found", "message": "No checkpoint found for the given config."}
    cp = getattr(checkpoint_tuple, "checkpoint", None) or {}
    metadata = getattr(checkpoint_tuple, "metadata", None) or {}
    config = getattr(checkpoint_tuple, "config", None) or {}
    parent_config = getattr(checkpoint_tuple, "parent_config", None)
    pending_writes = getattr(checkpoint_tuple, "pending_writes", None)

    channel_values = cp.get("channel_values", cp) if isinstance(cp, dict) else {}
    values = channel_values if isinstance(channel_values, dict) else {}

    return _serialize(
        {
            "values": values,
            "next": cp.get("next") if isinstance(cp, dict) else None,
            "tasks": cp.get("tasks") if isinstance(cp, dict) else None,
            "checkpoint": {
                "id": cp.get("id") if isinstance(cp, dict) else None,
                "ts": cp.get("ts") if isinstance(cp, dict) else None,
            },
            "metadata": metadata,
            "config": config,
            "parent_config": parent_config,
            "pending_writes": pending_writes,
        }
    )


def checkpoint_to_summary(checkpoint_tuple: Any) -> dict[str, Any]:
    if checkpoint_tuple is None:
        return {}
    cp = getattr(checkpoint_tuple, "checkpoint", None) or {}
    metadata = getattr(checkpoint_tuple, "metadata", None) or {}
    config = getattr(checkpoint_tuple, "config", None) or {}
    checkpoint_id = None
    if isinstance(cp, dict):
        checkpoint_id = cp.get("id")
    if not checkpoint_id and isinstance(config, dict):
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")
    return _serialize(
        {
            "checkpoint_id": checkpoint_id,
            "timestamp": cp.get("ts") if isinstance(cp, dict) else None,
            "next": cp.get("next") if isinstance(cp, dict) else None,
            "metadata": metadata,
        }
    )


def extract_messages(values: dict[str, Any]) -> list[Any]:
    messages = values.get("messages", [])
    if messages:
        return list(messages)
    for key in ("channel_values",):
        nested = values.get(key, {})
        if isinstance(nested, dict) and nested.get("messages"):
            return list(nested["messages"])
    return []
