"""RootBackend Protocol — the basic unit behind /api/roots."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from lakeview.formats import DatasetReader
from lakeview.models import DatasetEntry


@runtime_checkable
class RootBackend(Protocol):
    name: str  # short id used in URLs, e.g. "s3", "local", "polaris"
    uri: str  # absolute base URI for display
    kind: str  # "storage" or "namespace"
    driver: str  # "local" / "s3" for storage; "polaris" / ... for namespace

    def list_entries(self, path: str = "") -> list[DatasetEntry]: ...

    def open_dataset(self, path: str) -> DatasetReader | None: ...

    def read_file(self, path: str, max_bytes: int) -> tuple[bytes, int] | None: ...
