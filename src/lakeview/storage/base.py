"""Storage layer types."""

import dataclasses


@dataclasses.dataclass(frozen=True)
class EntryInfo:
    name: str
    path: str
    kind: str  # "lance", "parquet", "delta", "iceberg", "directory", "file"
    row_count: int | None = None
    size: int | None = None  # bytes, only for "file"
