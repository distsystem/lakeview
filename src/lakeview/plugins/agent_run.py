"""Agent run plugin — rich views for datasets with messages + session_id + correct."""

import json
import re

import pyarrow as pa

from lakeview.formats.base import DatasetReader

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


def _decode_messages(messages: list) -> list[dict]:
    result = []
    for msg in messages:
        msg = _decode_json(dict(msg) if not isinstance(msg, dict) else msg)
        if "parts" in msg and isinstance(msg["parts"], list):
            msg["parts"] = [
                _decode_json(dict(p) if not isinstance(p, dict) else p)
                for p in msg["parts"]
            ]
        result.append(msg)
    return result


class AgentRunPlugin:
    name = "agent_run"

    @staticmethod
    def matches(schema: pa.Schema) -> bool:
        col_names = {f.name for f in schema}
        return {"messages", "session_id", "correct"}.issubset(col_names)

    def available_filters(self) -> list[str]:
        return ["all", "ok", "wrong", "error", "pending"]

    def summarize_rows(self, rows: list[dict]) -> dict:
        total = len(rows)
        ok = sum(1 for r in rows if r.get("correct") is True)
        error = sum(1 for r in rows if r.get("error"))
        wrong = sum(1 for r in rows if not r.get("error") and r.get("correct") is False)
        pending = total - ok - wrong - error
        return {
            "total": total,
            "ok": ok,
            "wrong": wrong,
            "error": error,
            "pending": pending,
            "accuracy": ok / total if total else None,
        }

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

    def sidebar_row(self, row: dict) -> dict:
        return {
            "session_id": row.get("session_id"),
            "correct": row.get("correct"),
            "error": row.get("error"),
            "output": row.get("output"),
            "metadata": row.get("metadata"),
        }

    def detail(self, reader: DatasetReader, offset: int) -> dict | None:
        row = reader.get_row(offset)
        if row is None:
            return None
        raw_messages = row.pop("messages", None) or []
        messages = _decode_messages(raw_messages)
        return {"row": row, "messages": messages}

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
