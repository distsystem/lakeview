"""Dataset format backends — readers + detection registry."""

from __future__ import annotations

import os
import typing

import lance
import pyarrow as pa


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


# -- Lance --


def _resolve_lance_uri(db_path: str) -> str:
    if "://" in db_path:
        return db_path
    if os.path.exists(db_path):
        return os.path.abspath(db_path)
    absolute = f"/{db_path}"
    if os.path.exists(absolute):
        return absolute
    raise FileNotFoundError(db_path)


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
    def open(cls, db_path: str) -> "LanceReader | None":
        if db_path in _lance_cache:
            ds = _lance_cache[db_path]
            ds.checkout_version(ds.latest_version)
            return cls(ds)
        try:
            ds = lance.dataset(_resolve_lance_uri(db_path))
            _lance_cache[db_path] = ds
            return cls(ds)
        except Exception:
            return None

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

    def scan(
        self,
        offset: int = 0,
        limit: int = 50,
        columns: list[str] | None = None,
        filter: str | None = None,
    ) -> list[dict]:
        return self.to_arrow(
            offset=offset, limit=limit, columns=columns, filter=filter
        ).to_pylist()

    def get_row(self, offset: int) -> dict | None:
        tbl = self._ds.to_table(offset=offset, limit=1)
        return tbl.to_pylist()[0] if tbl.num_rows else None


# -- Registry --

# Ordered; first matching marker set wins.
PROBERS: list[type] = [LanceReader]

_BY_KIND: dict[str, type] = {cls.KIND: cls for cls in PROBERS}


def detect(probe) -> type | None:
    for cls in PROBERS:
        if cls.detect(probe):
            return cls
    return None


def open_dataset(path: str, kind: str) -> DatasetReader | None:
    cls = _BY_KIND.get(kind)
    return cls.open(path) if cls else None
