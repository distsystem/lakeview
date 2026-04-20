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

_SIDEBAR_COLS = ["session_id", "correct", "error", "output", "metadata"]
_FILTER_KEYS = ("all", "ok", "wrong", "error", "pending")


def _masks(tbl: pa.Table) -> dict[str, pa.ChunkedArray | None]:
    """Boolean masks per filter key over the light columns table."""
    correct = tbl["correct"]
    has_err = pc.is_valid(tbl["error"])
    no_err = pc.invert(has_err)
    correct_true = pc.equal(correct, True)
    correct_false = pc.equal(correct, False)
    correct_null = pc.invert(pc.is_valid(correct))
    return {
        "all": None,
        "ok": pc.and_kleene(correct_true, no_err),
        "wrong": pc.and_kleene(correct_false, no_err),
        "error": has_err,
        "pending": pc.and_kleene(correct_null, no_err),
    }


def _count(mask) -> int:
    return int(pc.sum(pc.cast(mask, pa.int64())).as_py() or 0)


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
        return list(_FILTER_KEYS)

    def view(
        self, reader: DatasetReader, filter_key: str, offset: int, limit: int
    ) -> tuple[AgentRunStats, int, list[AgentRunSidebar]]:
        """Single scan of the light columns; compute stats + filter + page
        entirely in Arrow compute. One S3 round-trip for the whole request."""
        tbl = reader.to_arrow(columns=_SIDEBAR_COLS)
        masks = _masks(tbl)

        total = tbl.num_rows
        ok = _count(masks["ok"])
        wrong = _count(masks["wrong"])
        error_n = _count(masks["error"])
        pending = total - ok - wrong - error_n
        stats = AgentRunStats(
            total=total,
            ok=ok,
            wrong=wrong,
            error=error_n,
            pending=pending,
            accuracy=ok / total if total else None,
        )

        mask = masks.get(filter_key)
        filtered = tbl if mask is None else tbl.filter(mask)
        page = filtered.slice(offset, limit)
        sidebars = [
            AgentRunSidebar(
                row_offset=offset + i,
                session_id=r.get("session_id"),
                correct=r.get("correct"),
                error=r.get("error"),
                output=r.get("output"),
                metadata=r.get("metadata"),
            )
            for i, r in enumerate(page.to_pylist())
        ]
        return stats, filtered.num_rows, sidebars

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
