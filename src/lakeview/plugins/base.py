"""SchemaPlugin protocol — the contract for schema-specific views."""

import typing

import pyarrow as pa

from lakeview.formats.base import DatasetReader


class SchemaPlugin(typing.Protocol):
    name: str

    @staticmethod
    def matches(schema: pa.Schema) -> bool: ...

    def available_filters(self) -> list[str]: ...

    def summarize_rows(self, rows: list[dict]) -> dict: ...

    def filter_rows(self, rows: list[dict], filter_key: str) -> list[dict]: ...

    def sidebar_row(self, row: dict) -> dict: ...

    def detail(self, reader: DatasetReader, offset: int) -> dict | None: ...
