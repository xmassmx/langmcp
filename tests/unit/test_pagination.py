"""Unit tests for pagination."""

from langmcp.pagination import paginate_items, truncate_value


def test_paginate_items_single_page():
    items = [{"id": i} for i in range(5)]
    result = paginate_items(items, page=1, max_chars=50000)
    assert result["total_pages"] == 1
    assert len(result["items"]) == 5


def test_truncate_long_string():
    value = "x" * 1000
    truncated, was = truncate_value(value, 100)
    assert was
    assert "(+" in str(truncated)
