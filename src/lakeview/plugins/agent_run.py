"""Agent run plugin — rich views for datasets with messages + session_id + correct."""

from __future__ import annotations

import json
import re
from typing import Any

from lancedb.pydantic import LanceModel

from lakeview.formats import DatasetReader
from lakeview.models import AgentRunDetail, AgentRunSidebar, AgentRunStats
from lakeview.plugins import SchemaPlugin


class AgentRunSchema(LanceModel):
    """Columns this plugin needs; matches by name (loose)."""

    session_id: str
    messages: list[Any]
    correct: bool | None


_SESSION_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_JSON_FIELDS = ("parts", "usage", "metadata")


def _decode_json(row: dict) -> dict:
    for col in _JSON_FIELDS:
        v = row.get(col)
        if isinstance(v, str):
            try:
                row[col] = json.loads(v)
            except json.JSONDecodeError:
                pass
    return row


def _decode_messages(messages: list[dict]) -> list[dict]:
    for msg in messages:
        _decode_json(msg)
        if isinstance(msg.get("parts"), list):
            for p in msg["parts"]:
                _decode_json(p)
    return messages


class AgentRunPlugin(SchemaPlugin):
    name = "agent_run"
    SCHEMA = AgentRunSchema

    def available_filters(self) -> list[str]:
        return ["all", "ok", "wrong", "error", "pending"]

    def summarize_rows(self, rows: list[dict]) -> AgentRunStats:
        total = len(rows)
        ok = sum(1 for r in rows if r.get("correct") is True)
        error = sum(1 for r in rows if r.get("error"))
        wrong = sum(1 for r in rows if not r.get("error") and r.get("correct") is False)
        pending = total - ok - wrong - error
        return AgentRunStats(
            total=total,
            ok=ok,
            wrong=wrong,
            error=error,
            pending=pending,
            accuracy=ok / total if total else None,
        )

    def filter_rows(self, rows: list[dict], filter_key: str) -> list[dict]:
        if filter_key in ("all", "", None):
            return rows
        checks = {
            "ok": lambda r: r.get("correct") is True,
            "error": lambda r: bool(r.get("error")),
            "wrong": lambda r: not r.get("error") and r.get("correct") is False,
            "pending": lambda r: not r.get("error") and r.get("correct") is None,
        }
        check = checks.get(filter_key)
        return [r for r in rows if check(r)] if check else rows

    def sidebar_row(self, row: dict, row_offset: int) -> AgentRunSidebar:
        return AgentRunSidebar(
            row_offset=row_offset,
            session_id=row.get("session_id"),
            correct=row.get("correct"),
            error=row.get("error"),
            output=row.get("output"),
            metadata=row.get("metadata"),
        )

    def detail(self, reader: DatasetReader, offset: int) -> AgentRunDetail | None:
        row = reader.get_row(offset)
        if row is None:
            return None
        raw_messages = row.pop("messages", None) or []
        return AgentRunDetail(row=row, messages=_decode_messages(raw_messages))

    def resolve_key(self, reader: DatasetReader, key: str) -> int | None:
        """Resolve a session_id or numeric offset to a row offset."""
        if key.isdigit():
            return int(key)
        if not _SESSION_ID_RE.match(key):
            return None
        # Scan all rows (without messages) to find matching session_id
        total = reader.count_rows()
        cols = [f.name for f in reader.schema if f.name != "messages"]
        rows = reader.scan(0, total, columns=cols)
        for i, r in enumerate(rows):
            if r.get("session_id") == key:
                return i
        return None
