"""StorageRootBackend — browse directory trees on local FS or S3."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from lakeview import formats
from lakeview.formats import DatasetReader
from lakeview.models import DatasetEntry
from lakeview.root_backends import fs

# obstore/lance release the GIL during I/O, so threads parallelize effectively.
_PROBE_WORKERS = 32


@dataclass
class StorageRootBackend:
    name: str
    uri: str
    driver: str  # "local" or "s3"
    kind: str = "storage"

    def list_entries(self, path: str = "") -> list[DatasetEntry]:
        entries = fs.list_entries_at(self.uri, path)
        dir_entries = [e for e in entries if e.kind == "directory"]
        if not dir_entries:
            return entries
        parent_store = fs.open_store_at(fs.join(self.uri, path))

        def upgrade(entry: DatasetEntry) -> None:
            probe = fs.Probe(parent_store, entry.name)
            cls = formats.detect(probe)
            if cls is None:
                return
            reader = cls.open(fs.join(self.uri, entry.path))
            if reader is None:
                return
            entry.kind = cls.KIND
            entry.row_count = reader.count_rows()

        with ThreadPoolExecutor(max_workers=_PROBE_WORKERS) as pool:
            list(pool.map(upgrade, dir_entries))
        return entries

    def open_dataset(self, path: str) -> DatasetReader | None:
        return formats.open_dataset(fs.join(self.uri, path.rstrip("/")))

    def read_file(self, path: str, max_bytes: int) -> tuple[bytes, int] | None:
        return fs.read_file_at(self.uri, path, max_bytes)
