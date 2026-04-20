"""Storage layer — URI-based browse and file access via obstore.

Any input with a URI scheme (`s3://`, `gs://`, `file://`, ...) is passed
through to obstore; bare paths are treated as local filesystem paths and
resolved to absolute directories before use.
"""

from __future__ import annotations

from pathlib import Path

import obstore as obs
from obstore.store import LocalStore, from_url

from lakeview.models import DatasetEntry


def _has_scheme(uri: str) -> bool:
    return "://" in uri


def _open_dir(uri: str):
    if _has_scheme(uri):
        return from_url(uri)
    return LocalStore(uri)


def _resolve_local(path: str, kind: str) -> str | None:
    check = Path.is_dir if kind == "dir" else Path.is_file
    for candidate in (path, f"/{path}"):
        if check(Path(candidate)):
            return candidate
    return None


def resolve_dir(uri: str) -> str | None:
    """Canonicalize a browse target or return None if it doesn't exist."""
    uri = uri.rstrip("/")
    if not uri:
        return None
    if _has_scheme(uri):
        return uri
    return _resolve_local(uri, "dir")


def open_store(uri: str):
    """Open an obstore rooted at a directory URI."""
    return _open_dir(uri)


class Probe:
    """Cheap existence probes against a subdirectory of a shared store.

    Uses prefix-filtered LIST (max-keys=1) so cost stays O(1) regardless
    of how many objects live under the directory. Reuses the parent
    store's HTTP client across all probes to avoid connection thrash.
    """

    def __init__(self, store, sub: str = "") -> None:
        self._store = store
        self._base = f"{sub.rstrip('/')}/" if sub else ""
        self._seen: dict[str, bool] = {}

    def has_any(self, marker: str) -> bool:
        key = f"{self._base}{marker}"
        if key in self._seen:
            return self._seen[key]
        hit = False
        try:
            for batch in obs.list(self._store, prefix=key, chunk_size=1):
                hit = len(batch) > 0
                break
        except Exception:
            hit = False
        self._seen[key] = hit
        return hit


def list_entries(uri: str) -> tuple[str, list[DatasetEntry]]:
    """List 1 level under `uri`. Returns (resolved_uri, entries)."""
    if not uri:
        return "", []
    resolved = resolve_dir(uri)
    if resolved is None:
        return uri, []

    try:
        store = _open_dir(resolved)
        result = obs.list_with_delimiter(store)
    except Exception:
        return resolved, []

    entries: list[DatasetEntry] = []
    for prefix in result.get("common_prefixes", []):
        name = prefix.rstrip("/").rsplit("/", 1)[-1]
        if not name or name.startswith((".", "_")):
            continue
        entries.append(
            DatasetEntry(name=name, path=f"{resolved}/{name}", kind="directory")
        )

    for meta in result.get("objects", []):
        path = str(meta.get("path") or "")
        name = path.rsplit("/", 1)[-1]
        if not name or name.startswith("."):
            continue
        entries.append(
            DatasetEntry(
                name=name,
                path=f"{resolved}/{name}",
                kind="file",
                size=meta.get("size"),
            )
        )

    entries.sort(key=lambda e: (e.kind == "file", e.name))
    return resolved, entries


def read_file(uri: str, max_bytes: int) -> tuple[bytes, int] | None:
    """Read a file's contents. Returns (bytes, size) or None if not found.

    Raises ValueError if the file exceeds `max_bytes`.
    """
    target = uri if _has_scheme(uri) else _resolve_local(uri, "file")
    if target is None:
        return None
    parent, _, name = target.rpartition("/")
    if not name:
        return None
    try:
        store = _open_dir(parent)
        meta = obs.head(store, name)
    except Exception:
        return None
    size = meta.get("size") or 0
    if size > max_bytes:
        raise ValueError(f"file too large: {target} ({size} > {max_bytes})")
    data = obs.get(store, name).bytes()
    return bytes(data), size
