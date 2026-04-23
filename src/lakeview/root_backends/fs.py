"""Low-level obstore helpers keyed off absolute URIs.

Consumed by ``StorageRootBackend``. No root concept — just URIs in, data out.
"""

from __future__ import annotations

import obstore as obs
from obstore.store import LocalStore, from_url

from lakeview.models import DatasetEntry


def join(base_uri: str, rel: str = "") -> str:
    """Append ``rel`` under ``base_uri``; empty and trailing slashes are normalized."""
    rel = rel.strip("/")
    return f"{base_uri}/{rel}" if rel else base_uri


def open_store_at(uri: str):
    """Open an obstore rooted at ``uri`` (scheme URI or local path)."""
    return from_url(uri) if "://" in uri else LocalStore(uri)


class Probe:
    """Cheap existence check against a subdirectory of a shared store.

    Uses prefix-filtered LIST (max-keys=1) so cost stays O(1) regardless
    of how many objects live under the directory. Reuses the parent
    store's HTTP client to avoid connection thrash.
    """

    def __init__(self, store, sub: str = "") -> None:
        self._store = store
        self._base = f"{sub.rstrip('/')}/" if sub else ""

    def has_any(self, marker: str) -> bool:
        key = f"{self._base}{marker}"
        try:
            for batch in obs.list(self._store, prefix=key, chunk_size=1):
                return len(batch) > 0
        except Exception:
            return False
        return False


def list_entries_at(base_uri: str, rel: str = "") -> list[DatasetEntry]:
    """List 1 level under ``base_uri/rel``. Entry paths are relative to base."""
    uri = join(base_uri, rel)
    try:
        store = open_store_at(uri)
        result = obs.list_with_delimiter(store)
    except Exception:
        return []

    rel = rel.strip("/")
    entries: list[DatasetEntry] = []
    for prefix in result.get("common_prefixes", []):
        name = prefix.rstrip("/").rsplit("/", 1)[-1]
        if not name or name.startswith((".", "_")):
            continue
        entries.append(
            DatasetEntry(
                name=name,
                path=f"{rel}/{name}" if rel else name,
                kind="directory",
            )
        )
    for meta in result.get("objects", []):
        p = str(meta.get("path") or "")
        name = p.rsplit("/", 1)[-1]
        if not name or name.startswith("."):
            continue
        entries.append(
            DatasetEntry(
                name=name,
                path=f"{rel}/{name}" if rel else name,
                kind="file",
                size=meta.get("size"),
            )
        )
    entries.sort(key=lambda e: (e.kind == "file", e.name))
    return entries


def read_file_at(base_uri: str, rel: str, max_bytes: int) -> tuple[bytes, int] | None:
    """Read a file under ``base_uri/rel``. Returns (bytes, size) or None.

    Raises ValueError if the file exceeds ``max_bytes``.
    """
    parent_rel, _, name = rel.rpartition("/")
    if not name:
        return None
    parent_uri = join(base_uri, parent_rel)
    try:
        store = open_store_at(parent_uri)
        meta = obs.head(store, name)
    except Exception:
        return None
    size = meta.get("size") or 0
    if size > max_bytes:
        raise ValueError(f"file too large: {base_uri}/{rel} ({size} > {max_bytes})")
    data = obs.get(store, name).bytes()
    return bytes(data), size
