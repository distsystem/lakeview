"""DatasetReader protocol — the contract for all format backends."""

import typing

import pyarrow as pa


class DatasetReader(typing.Protocol):
    @property
    def schema(self) -> pa.Schema: ...

    def count_rows(self) -> int: ...

    def scan(
        self,
        offset: int = 0,
        limit: int = 50,
        columns: list[str] | None = None,
    ) -> list[dict]: ...

    def get_row(self, offset: int) -> dict | None: ...
