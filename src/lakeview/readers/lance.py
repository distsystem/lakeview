"""Lance dataset reader — blob-aware with plain-binary column normalization."""

from __future__ import annotations

import lance
import pyarrow as pa

from lakeview.core.readers import (
    DatasetReader,
    Filter,
    is_plain_binary,
    normalize_binary_rows,
)

_BLOB_V1_META_KEY = b"lance-encoding:blob"
_BLOB_V2_EXT_NAME = "lance.blob.v2"


def _is_blob_v1_encoded(field: pa.Field) -> bool:
    """Legacy blob encoding: large_binary column with a metadata marker."""
    meta = field.metadata or {}
    return meta.get(_BLOB_V1_META_KEY) == b"true"


def _is_blob_v2_encoded(field: pa.Field) -> bool:
    """Blob v2: an Arrow extension type named ``lance.blob.v2``."""
    t = field.type
    return isinstance(t, pa.ExtensionType) and t.extension_name == _BLOB_V2_EXT_NAME


def is_lance_blob(field: pa.Field) -> bool:
    return _is_blob_v1_encoded(field) or _is_blob_v2_encoded(field)


def _sql_literal(value) -> str:
    if isinstance(value, str):
        # Lance SQL: escape single quotes by doubling.
        return "'" + value.replace("'", "''") + "'"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if value is None:
        return "NULL"
    return repr(value)


def _to_sql(filter: Filter | None) -> str | None:
    if not filter:
        return None
    return " AND ".join(f"{col} = {_sql_literal(v)}" for col, v in filter.items())


_lance_cache: dict[str, lance.LanceDataset] = {}


class LanceReader:
    KIND = "lance"
    MARKERS = ("_versions/",)

    def __init__(self, ds: lance.LanceDataset) -> None:
        self._ds = ds
        # Plain binary (bytes) columns need bytes → {size} normalization on
        # scan. Lance blob-encoded columns already materialize as descriptor
        # dicts, so they're excluded.
        self._plain_binary_names = frozenset(
            f.name
            for f in ds.schema
            if is_plain_binary(f) and not _is_blob_v1_encoded(f)
        )

    @classmethod
    def detect(cls, probe) -> bool:
        return all(probe.has_any(m) for m in cls.MARKERS)

    @classmethod
    def open(cls, uri: str) -> "LanceReader | None":
        if uri in _lance_cache:
            ds = _lance_cache[uri]
            ds.checkout_version(ds.latest_version)
            return cls(ds)
        try:
            ds = lance.dataset(uri)
        except Exception:
            return None
        _lance_cache[uri] = ds
        return cls(ds)

    @property
    def schema(self):
        return self._ds.schema

    def is_blob_column(self, field: pa.Field) -> bool:
        """Anything /blob can stream: raw bytes or a Lance blob descriptor."""
        return is_plain_binary(field) or is_lance_blob(field)

    def count_rows(self, filter: Filter | None = None) -> int:
        sql = _to_sql(filter)
        return self._ds.count_rows(filter=sql) if sql else self._ds.count_rows()

    def to_arrow(
        self,
        offset: int = 0,
        limit: int | None = None,
        columns: list[str] | None = None,
        filter: Filter | None = None,
    ) -> pa.Table:
        return self._ds.to_table(
            offset=offset, limit=limit, columns=columns, filter=_to_sql(filter)
        )

    def scan(
        self,
        offset: int = 0,
        limit: int = 50,
        columns: list[str] | None = None,
        filter: Filter | None = None,
    ) -> list[dict]:
        rows = self.to_arrow(
            offset=offset, limit=limit, columns=columns, filter=filter
        ).to_pylist()
        return normalize_binary_rows(rows, self._plain_binary_names)

    def get_row(self, offset: int) -> dict | None:
        tbl = self._ds.to_table(offset=offset, limit=1)
        if not tbl.num_rows:
            return None
        return normalize_binary_rows(tbl.to_pylist(), self._plain_binary_names)[0]

    def _blob_uri(self, offset: int, column: str) -> str | None:
        """Extract the ``blob_uri`` field from a v2 blob descriptor, if any."""
        tbl = self._ds.to_table(offset=offset, limit=1, columns=[column])
        if not tbl.num_rows:
            return None
        desc = tbl.to_pylist()[0].get(column)
        if isinstance(desc, dict):
            return desc.get("blob_uri") or None
        return None

    def read_blob(self, offset: int, column: str) -> tuple[bytes, str | None] | None:
        """Return ``(bytes, uri_or_none)``. URI is only set for v2 URI-refs."""
        try:
            field = self._ds.schema.field(column)
        except KeyError:
            return None
        if not self.is_blob_column(field):
            return None
        if is_lance_blob(field):
            uri = self._blob_uri(offset, column) if _is_blob_v2_encoded(field) else None
            blobs = self._ds.take_blobs(column, indices=[offset])
            if not blobs:
                return None
            with blobs[0] as bf:
                return bf.readall(), uri
        # plain binary: bytes come straight out of to_table
        tbl = self._ds.to_table(offset=offset, limit=1, columns=[column])
        if not tbl.num_rows:
            return None
        value = tbl.column(column)[0].as_py()
        return (bytes(value), None) if value is not None else None


# Advertise as a DatasetReader to satisfy the Protocol at registration.
_: type[DatasetReader] = LanceReader
