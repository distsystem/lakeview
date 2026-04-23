"""Schema plugins — format-specific views layered on top of DatasetReader."""

from __future__ import annotations

from typing import ClassVar

import pyarrow as pa
from pydantic import BaseModel

from lakeview.core import DatasetReader


class SchemaPlugin:
    """Base class for schema-specific views.

    Sub-classes declare ``REQUIRED_COLUMNS`` — a ``frozenset`` of column names
    that must be present for the plugin to apply. ``matches()`` checks the
    actual dataset schema against those field names.
    """

    name: ClassVar[str]
    REQUIRED_COLUMNS: ClassVar[frozenset[str]]

    @classmethod
    def matches(cls, schema: pa.Schema) -> bool:
        return cls.REQUIRED_COLUMNS.issubset({f.name for f in schema})

    def available_filters(self) -> list[str]:
        return ["all"]

    def view(
        self, reader: DatasetReader, filter_key: str, offset: int, limit: int
    ) -> tuple[BaseModel | None, int, list[BaseModel]]:
        """Return ``(stats, filtered_total, page_rows)`` in a single pass.

        Plugins should typically do **one** scan of their light columns and
        compute stats + filter + page via Arrow compute, so remote datasets
        don't pay latency for multiple scanner round-trips.
        """
        raise NotImplementedError

    def detail(self, reader: DatasetReader, key: str) -> BaseModel | None:
        """Resolve ``key`` (session id, offset, ...) to a detail record."""
        raise NotImplementedError


from lakeview.plugins.agent_run import AgentRunPlugin  # noqa: E402

# Ordered; first match wins.
_PLUGINS: list[SchemaPlugin] = [AgentRunPlugin()]


def detect_plugin(schema: pa.Schema) -> SchemaPlugin | None:
    for plugin in _PLUGINS:
        if plugin.matches(schema):
            return plugin
    return None
