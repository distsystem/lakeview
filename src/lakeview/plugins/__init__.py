"""Schema plugins — format-specific views layered on top of DatasetReader."""

from __future__ import annotations

import typing

import pyarrow as pa

from lakeview.formats import DatasetReader
from lakeview.plugins.agent_run import AgentRunPlugin


class SchemaPlugin(typing.Protocol):
    name: str

    @staticmethod
    def matches(schema: pa.Schema) -> bool: ...

    def available_filters(self) -> list[str]: ...

    def summarize_rows(self, rows: list[dict]) -> dict: ...

    def filter_rows(self, rows: list[dict], filter_key: str) -> list[dict]: ...

    def sidebar_row(self, row: dict) -> dict: ...

    def detail(self, reader: DatasetReader, offset: int) -> dict | None: ...


# Ordered; first match wins.
_PLUGINS: list[SchemaPlugin] = [AgentRunPlugin()]


def detect_plugin(schema: pa.Schema) -> SchemaPlugin | None:
    for plugin in _PLUGINS:
        if plugin.matches(schema):
            return plugin
    return None
