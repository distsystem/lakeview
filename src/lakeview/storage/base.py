"""Storage layer types."""

import dataclasses


@dataclasses.dataclass(frozen=True)
class EntryInfo:
    name: str
    path: str
    kind: str  # "lance", "parquet", "delta", "iceberg", "directory"
    row_count: int | None = None
