"""Lance format backend."""

import os

import lance

from lakeview.formats.base import DatasetReader

_cache: dict[str, lance.LanceDataset] = {}


def _resolve_uri(db_path: str) -> str:
    if os.path.exists(db_path):
        return os.path.abspath(db_path)
    absolute = f"/{db_path}"
    if os.path.exists(absolute):
        return absolute
    return f"s3://{db_path}"


class LanceReader:
    def __init__(self, ds: lance.LanceDataset) -> None:
        self._ds = ds

    @classmethod
    def open(cls, db_path: str) -> "LanceReader | None":
        if db_path in _cache:
            ds = _cache[db_path]
            ds.checkout_version(ds.latest_version)
            return cls(ds)
        try:
            ds = lance.dataset(_resolve_uri(db_path))
            _cache[db_path] = ds
            return cls(ds)
        except Exception:
            return None

    @property
    def schema(self):
        return self._ds.schema

    def count_rows(self) -> int:
        return self._ds.count_rows()

    def scan(
        self,
        offset: int = 0,
        limit: int = 50,
        columns: list[str] | None = None,
    ) -> list[dict]:
        tbl = self._ds.to_table(offset=offset, limit=limit, columns=columns)
        return tbl.to_pylist()

    def get_row(self, offset: int) -> dict | None:
        tbl = self._ds.to_table(offset=offset, limit=1)
        if tbl.num_rows == 0:
            return None
        return tbl.to_pylist()[0]


# Satisfy the DatasetReader protocol check
_: type[DatasetReader] = LanceReader  # type: ignore[assignment]
