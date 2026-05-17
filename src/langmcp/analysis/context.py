"""Context window analysis (token estimates)."""

from __future__ import annotations

from typing import Any

from langmcp.checkpoint_utils import extract_messages
from langmcp.analysis.thread import _message_content

TRIM_MESSAGES_DOC = (
    "https://docs.langchain.com/oss/python/langgraph/add-memory#manage-message-history"
)


def estimate_tokens(text: str, model_hint: str | None = None) -> int:
    try:
        import tiktoken

        enc_name = "cl100k_base"
        if model_hint and "gpt-4" in model_hint:
            enc_name = "cl100k_base"
        enc = tiktoken.get_encoding(enc_name)
        return len(enc.encode(text))
    except ImportError:
        return max(1, len(text) // 4)


def analyze_context_window(
    values: dict[str, Any],
    *,
    model_hint: str | None = None,
) -> dict[str, Any]:
    messages = extract_messages(values)
    total_chars = 0
    for msg in messages:
        total_chars += len(_message_content(msg))
    combined = " ".join(_message_content(m) for m in messages)
    estimated_tokens = estimate_tokens(combined, model_hint)
    warnings: list[str] = []
    if total_chars > 100_000:
        warnings.append(f"Thread content is large ({total_chars} chars). Consider trimming.")
    if len(messages) > 50:
        warnings.append(f"Thread has {len(messages)} messages (>50). Consider summarization.")
    return {
        "message_count": len(messages),
        "total_chars": total_chars,
        "estimated_tokens": estimated_tokens,
        "estimation_method": "tiktoken" if _has_tiktoken() else "chars/4",
        "model_hint": model_hint,
        "warnings": warnings,
        "trim_messages_doc": TRIM_MESSAGES_DOC,
    }


def _has_tiktoken() -> bool:
    try:
        import tiktoken  # noqa: F401

        return True
    except ImportError:
        return False
