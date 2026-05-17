"""Shared Pydantic models for MCP tool responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BaseToolResponse(BaseModel):
    profile: str
    truncated: bool = False


class ThreadEntry(BaseModel):
    thread_id: str
    last_updated: str | None = None


class PaginatedResponse(BaseToolResponse):
    page: int = 1
    total_pages: int = 1
    max_chars: int = 25000


class HealthCheckResponse(BaseToolResponse):
    checkpointer_backend: str
    store_backend: str | None = None
    checkpointer_connected: bool
    store_connected: bool | None = None
    checkpointer_setup: bool
    store_setup: bool | None = None
    checkpointer_uri_redacted: str
    store_uri_redacted: str | None = None
    read_only: bool
    warning: str | None = None


class ProfileInfo(BaseModel):
    name: str
    checkpointer_backend: str
    store_backend: str
    has_store: str
