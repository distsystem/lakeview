"""Generic dataset-reader contract — format-agnostic.

Every concrete reader (Lance today, Parquet / Delta tomorrow) implements the
``DatasetReader`` Protocol below. Helpers here cover only notions that apply
to *any* tabular format: mime sniffing, plain-binary column detection, and
post-scan bytes-to-descriptor normalization.

Filter abstraction is deliberately tiny — equality-only — so plugins can
express `column = value` predicates without writing Lance SQL directly.
"""

from __future__ import annotations

import mimetypes
import typing
from collections.abc import Mapping
from typing import Any, ClassVar

import magic
import pyarrow as pa

# libmagic's pattern DB is mmapped once and matching is thread-safe as long
# as we don't mutate the instance — fine for a read-only mime sniffer.
_MIME = magic.Magic(mime=True)

_PLAIN_BINARY_IDS = frozenset({pa.binary().id, pa.large_binary().id})


# -- Filters --

Filter = Mapping[str, Any]
"""Equality-only predicate. Extend when plugins need OR / range."""


def eq(column: str, value: Any) -> Filter:
    return {column: value}


# -- Column classification --


def is_plain_binary(field: pa.Field) -> bool:
    """Raw binary column that scans as Python `bytes` (not a blob descriptor)."""
    t = field.type
    return t.id in _PLAIN_BINARY_IDS or pa.types.is_fixed_size_binary(t)


# -- Mime --


def detect_mime(head: bytes, uri: str | None = None) -> str:
    """URI suffix first (cheap, unambiguous), else libmagic on the bytes."""
    if uri and (guess := mimetypes.guess_type(uri)[0]):
        return guess
    return _MIME.from_buffer(head) or "application/octet-stream"


# -- Row normalization --


def normalize_binary_rows(rows: list[dict], binary_cols: frozenset[str]) -> list[dict]:
    """Replace raw `bytes` with `{size}` so FastAPI can encode the rows.

    Columns that already materialize as descriptor dicts (e.g. Lance blobs)
    pass through untouched because they fail the `isinstance(v, bytes)` check.
    """
    if not binary_cols:
        return rows
    for row in rows:
        for col, v in row.items():
            if col in binary_cols and isinstance(v, (bytes, bytearray, memoryview)):
                row[col] = {"size": len(v)}
    return rows


# -- Reader Protocol --


class DatasetReader(typing.Protocol):
    KIND: ClassVar[str]
    MARKERS: ClassVar[tuple[str, ...]]

    @classmethod
    def detect(cls, probe) -> bool: ...

    @classmethod
    def open(cls, uri: str) -> "DatasetReader | None": ...

    @property
    def schema(self) -> pa.Schema: ...

    def is_blob_column(self, field: pa.Field) -> bool: ...

    def count_rows(self, filter: Filter | None = None) -> int: ...

    def to_arrow(
        self,
        offset: int = 0,
        limit: int | None = None,
        columns: list[str] | None = None,
        filter: Filter | None = None,
    ) -> pa.Table: ...

    def scan(
        self,
        offset: int = 0,
        limit: int = 50,
        columns: list[str] | None = None,
        filter: Filter | None = None,
    ) -> list[dict]: ...

    def get_row(self, offset: int) -> dict | None: ...

    def read_blob(
        self, offset: int, column: str
    ) -> tuple[bytes, str | None] | None: ...
