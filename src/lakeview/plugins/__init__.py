"""Schema plugins — format-specific views layered on top of DatasetReader."""

from __future__ import annotations

from typing import ClassVar

import pyarrow as pa
from lancedb.pydantic import LanceModel
from pydantic import BaseModel

from lakeview.formats import DatasetReader


class SchemaPlugin:
    """Base class for schema-specific views.

    Sub-classes declare a `SCHEMA` (LanceModel) whose fields are the
    required columns for this plugin to apply. `matches()` checks the
    actual dataset schema against those field names.
    """

    name: ClassVar[str]
    SCHEMA: ClassVar[type[LanceModel]]

    @classmethod
    def matches(cls, schema: pa.Schema) -> bool:
        required = set(cls.SCHEMA.model_fields)
        return required.issubset({f.name for f in schema})

    def available_filters(self) -> list[str]:
        return ["all"]

    def summarize_rows(self, rows: list[dict]) -> BaseModel | None:
        return None

    def filter_rows(self, rows: list[dict], filter_key: str) -> list[dict]:
        return rows

    def sidebar_row(self, row: dict, row_offset: int) -> BaseModel:
        raise NotImplementedError

    def detail(self, reader: DatasetReader, offset: int) -> BaseModel | None:
        raise NotImplementedError


from lakeview.plugins.agent_run import AgentRunPlugin  # noqa: E402

# Ordered; first match wins.
_PLUGINS: list[SchemaPlugin] = [AgentRunPlugin()]


def detect_plugin(schema: pa.Schema) -> SchemaPlugin | None:
    for plugin in _PLUGINS:
        if plugin.matches(schema):
            return plugin
    return None
