"""Unit tests for analysis helpers."""

from langmcp.analysis.thread import compare_checkpoint_values, summarize_thread_messages


def test_summarize_thread_messages():
    values = {
        "messages": [
            {"type": "human", "content": "Hello"},
            {"type": "ai", "content": "Hi there", "tool_calls": [{"name": "search", "id": "1"}]},
        ]
    }
    summary = summarize_thread_messages(values)
    assert summary["message_count"] == 2
    assert summary["last_user_message"] == "Hello"
    assert len(summary["transcript"]) == 2


def test_compare_checkpoint_values():
    diff = compare_checkpoint_values(
        {"messages": [1, 2]},
        {"messages": [1, 2, 3], "extra": True},
    )
    assert "extra" in diff["added_keys"]
    assert diff["message_count_delta"] == 1
