"""Pydantic response models for the agent-run plugin."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AgentRunStats(BaseModel):
    total: int
    ok: int
    wrong: int
    error: int
    pending: int
    accuracy: float | None = None


class AgentRunSidebar(BaseModel):
    row_offset: int
    session_id: str | None = None
    correct: bool | None = None
    error: str | None = None
    output: Any | None = None
    metadata: Any | None = None


class AgentRunDetail(BaseModel):
    row: dict
    messages: list[dict]
