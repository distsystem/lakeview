"""Dataset format backends — readers + detection registry."""

from __future__ import annotations

import mimetypes
import typing

import lance
import magic
import pyarrow as pa

# libmagic's pattern DB is mmapped once and matching is thread-safe as long
# as we don't mutate the instance — fine for a read-only mime sniffer.
_MIME = magic.Magic(mime=True)

_BLOB_V1_META_KEY = b"lance-encoding:blob"
_BLOB_V2_EXT_NAME = "lance.blob.v2"
_PLAIN_BINARY_IDS = frozenset({pa.binary().id, pa.large_binary().id})


def is_blob_v1_encoded(field: pa.Field) -> bool:
    """Legacy blob encoding: large_binary column with a metadata marker."""
    meta = field.metadata or {}
    return meta.get(_BLOB_V1_META_KEY) == b"true"


def is_blob_v2_encoded(field: pa.Field) -> bool:
    """Blob v2: an Arrow extension type named lance.blob.v2."""
    t = field.type
    return isinstance(t, pa.ExtensionType) and t.extension_name == _BLOB_V2_EXT_NAME


def is_plain_binary(field: pa.Field) -> bool:
    """Raw binary column that scans as Python `bytes` (not a blob descriptor)."""
    t = field.type
    return t.id in _PLAIN_BINARY_IDS or pa.types.is_fixed_size_binary(t)


def is_blob_column(field: pa.Field) -> bool:
    """Anything the /blob endpoint can stream — binary bytes or a Lance blob."""
    return (
        is_plain_binary(field) or is_blob_v1_encoded(field) or is_blob_v2_encoded(field)
    )


def detect_mime(head: bytes, uri: str | None = None) -> str:
    """URI suffix first (cheap, unambiguous), else libmagic on the bytes."""
    if uri and (guess := mimetypes.guess_type(uri)[0]):
        return guess
    return _MIME.from_buffer(head) or "application/octet-stream"


def _normalize_binary_rows(rows: list[dict], binary_cols: list[str]) -> list[dict]:
    """Replace raw `bytes` with `{size}` so FastAPI can encode the rows.

    Lance blob-encoded columns (v1 or v2) already materialize as descriptor
    dicts — those pass through untouched.
    """
    if not binary_cols:
        return rows
    for row in rows:
        for col in binary_cols:
            v = row.get(col)
            if isinstance(v, (bytes, bytearray, memoryview)):
                row[col] = {"size": len(v)}
    return rows


class DatasetReader(typing.Protocol):
    @property
    def schema(self) -> pa.Schema: ...

    def count_rows(self, filter: str | None = None) -> int: ...

    def to_arrow(
        self,
        offset: int = 0,
        limit: int | None = None,
        columns: list[str] | None = None,
        filter: str | None = None,
    ) -> pa.Table: ...

    def scan(
        self,
        offset: int = 0,
        limit: int = 50,
        columns: list[str] | None = None,
        filter: str | None = None,
    ) -> list[dict]: ...

    def get_row(self, offset: int) -> dict | None: ...

    def read_blob(
        self, offset: int, column: str
    ) -> tuple[bytes, str | None] | None: ...


# -- Lance --


_lance_cache: dict[str, lance.LanceDataset] = {}


class LanceReader:
    KIND = "lance"
    MARKERS = ("_versions/",)

    def __init__(self, ds: lance.LanceDataset) -> None:
        self._ds = ds

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

    def count_rows(self, filter: str | None = None) -> int:
        return self._ds.count_rows(filter=filter) if filter else self._ds.count_rows()

    def to_arrow(
        self,
        offset: int = 0,
        limit: int | None = None,
        columns: list[str] | None = None,
        filter: str | None = None,
    ) -> pa.Table:
        return self._ds.to_table(
            offset=offset, limit=limit, columns=columns, filter=filter
        )

    def _plain_binary_cols(self, columns: list[str] | None) -> list[str]:
        """Plain binary columns — need bytes → {size} normalization."""
        names = set(columns) if columns else None
        return [
            f.name
            for f in self._ds.schema
            if is_plain_binary(f)
            and not is_blob_v1_encoded(f)
            and (names is None or f.name in names)
        ]

    def scan(
        self,
        offset: int = 0,
        limit: int = 50,
        columns: list[str] | None = None,
        filter: str | None = None,
    ) -> list[dict]:
        rows = self.to_arrow(
            offset=offset, limit=limit, columns=columns, filter=filter
        ).to_pylist()
        return _normalize_binary_rows(rows, self._plain_binary_cols(columns))

    def get_row(self, offset: int) -> dict | None:
        tbl = self._ds.to_table(offset=offset, limit=1)
        if not tbl.num_rows:
            return None
        rows = _normalize_binary_rows(tbl.to_pylist(), self._plain_binary_cols(None))
        return rows[0]

    def _blob_uri(self, offset: int, column: str) -> str | None:
        """Extract the blob_uri field from a v2 blob descriptor, if any."""
        tbl = self._ds.to_table(offset=offset, limit=1, columns=[column])
        if not tbl.num_rows:
            return None
        desc = tbl.to_pylist()[0].get(column)
        if isinstance(desc, dict):
            uri = desc.get("blob_uri")
            return uri or None
        return None

    def read_blob(self, offset: int, column: str) -> tuple[bytes, str | None] | None:
        """Return (bytes, uri_or_none). URI is only set for v2 URI-refs."""
        try:
            field = self._ds.schema.field(column)
        except KeyError:
            return None
        if not is_blob_column(field):
            return None
        if is_blob_v1_encoded(field) or is_blob_v2_encoded(field):
            uri = self._blob_uri(offset, column) if is_blob_v2_encoded(field) else None
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


# -- Registry --
#
# Only Lance today. When a second backend lands, turn `detect` into a
# dispatch loop and thread the chosen class through `open_dataset`.


def detect(probe) -> type[LanceReader] | None:
    return LanceReader if LanceReader.detect(probe) else None


def open_dataset(uri: str) -> DatasetReader | None:
    return LanceReader.open(uri)
