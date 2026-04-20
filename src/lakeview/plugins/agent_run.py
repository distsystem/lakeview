"""Agent run plugin — rich views for datasets with messages + session_id + correct."""

from __future__ import annotations

import json
import re
from typing import Any

import pyarrow as pa
import pyarrow.compute as pc
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

# Filter expressions pushed down to Lance. Values are Lance SQL strings.
_FILTERS: dict[str, str | None] = {
    "all": None,
    "ok": "correct = true AND error IS NULL",
    "wrong": "correct = false AND error IS NULL",
    "error": "error IS NOT NULL",
    "pending": "correct IS NULL AND error IS NULL",
}
_SIDEBAR_COLS = ["session_id", "correct", "error", "output", "metadata"]


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
        return list(_FILTERS)

    def summarize(self, reader: DatasetReader) -> AgentRunStats:
        """One scan of (correct, error) + vectorized Arrow aggregates."""
        tbl = reader.to_arrow(columns=["correct", "error"])
        total = tbl.num_rows
        correct = tbl["correct"].combine_chunks()
        has_err = pc.is_valid(tbl["error"].combine_chunks())
        no_err = pc.invert(has_err)

        def count(mask) -> int:
            return int(pc.sum(pc.cast(mask, pa.int64())).as_py() or 0)

        error_n = count(has_err)
        ok = count(pc.and_kleene(pc.equal(correct, True), no_err))
        wrong = count(pc.and_kleene(pc.equal(correct, False), no_err))
        pending = total - ok - wrong - error_n

        return AgentRunStats(
            total=total,
            ok=ok,
            wrong=wrong,
            error=error_n,
            pending=pending,
            accuracy=ok / total if total else None,
        )

    def page(
        self, reader: DatasetReader, filter_key: str, offset: int, limit: int
    ) -> tuple[int, list[AgentRunSidebar]]:
        predicate = _FILTERS.get(filter_key, None)
        total = reader.count_rows(filter=predicate)
        rows = reader.scan(
            offset=offset, limit=limit, columns=_SIDEBAR_COLS, filter=predicate
        )
        sidebars = [
            AgentRunSidebar(
                row_offset=offset + i,
                session_id=r.get("session_id"),
                correct=r.get("correct"),
                error=r.get("error"),
                output=r.get("output"),
                metadata=r.get("metadata"),
            )
            for i, r in enumerate(rows)
        ]
        return total, sidebars

    def detail(self, reader: DatasetReader, key: str) -> AgentRunDetail | None:
        row: dict | None
        if key.isdigit():
            row = reader.get_row(int(key))
        elif _SESSION_ID_RE.match(key):
            # Lance SQL: single-quoted string literal; key is UUID-safe already.
            tbl = reader.to_arrow(filter=f"session_id = '{key}'", limit=1)
            row = tbl.to_pylist()[0] if tbl.num_rows else None
        else:
            return None
        if row is None:
            return None
        raw_messages = row.pop("messages", None) or []
        return AgentRunDetail(row=row, messages=_decode_messages(raw_messages))
