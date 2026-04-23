"""NamespaceRootBackend — browse Lance tables via a catalog server."""

from __future__ import annotations

from dataclasses import dataclass

from lakeview import core
from lakeview.core import DatasetReader
from lakeview.models import DatasetEntry
from lakeview.root_backends.polaris_client import PolarisClient


def _segments(path: str) -> list[str]:
    return [p for p in path.split("/") if p]


@dataclass
class NamespaceRootBackend:
    """Read-only browser over a configured catalog namespace.

    Tables are discovered via the catalog client; datasets are opened using
    the ``base-location`` the catalog returns, with storage options resolved
    locally (Lakeview uses its own AWS creds in Phase 2 — proper credential
    vending is a later concern).
    """

    name: str
    uri: str  # display URI, e.g. "polaris://lakeview_test@localhost:8181"
    client: PolarisClient
    driver: str = "polaris"
    kind: str = "namespace"

    def list_entries(self, path: str = "") -> list[DatasetEntry]:
        segs = _segments(path)
        children = self.client.list_namespaces(segs)
        tables = self.client.list_tables(segs) if segs else []
        entries: list[DatasetEntry] = []
        for child in children:
            leaf = child[-1] if child else ""
            if not leaf:
                continue
            entries.append(
                DatasetEntry(
                    name=leaf,
                    path=f"{path}/{leaf}" if path else leaf,
                    kind="namespace",
                )
            )
        # Polaris `list_tables` returns names only — the per-table format
        # lives in `describe_table`, fetching it would be N round-trips.
        # Label all catalog tables as "lance" here; open_dataset does the
        # real format → reader lookup when the user clicks in.
        for t in tables:
            entries.append(
                DatasetEntry(
                    name=t,
                    path=f"{path}/{t}" if path else t,
                    kind="lance",
                )
            )
        entries.sort(key=lambda e: (e.kind != "namespace", e.name))
        return entries

    def open_dataset(self, path: str) -> DatasetReader | None:
        segs = _segments(path)
        if not segs:
            return None
        ns, name = segs[:-1], segs[-1]
        table = self.client.describe_table(ns, name)
        if not table:
            return None
        base = table.get("base-location")
        cls = core.reader_for_format(table.get("format", ""))
        if not base or cls is None:
            return None
        return cls.open(base)

    def read_file(self, path: str, max_bytes: int) -> tuple[bytes, int] | None:
        # Namespace roots don't expose arbitrary file browsing per the design doc.
        return None
