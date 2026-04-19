"""Storage layer — URI-based browse and file access via obstore.

Any input with a URI scheme (`s3://`, `gs://`, `file://`, ...) is passed
through to obstore; bare paths are treated as local filesystem paths and
resolved to absolute directories before use.
"""

from __future__ import annotations

from pathlib import Path

import obstore as obs
from obstore.store import LocalStore, from_url

from lakeview.storage.base import EntryInfo


def _has_scheme(uri: str) -> bool:
    return "://" in uri


def _open_dir(uri: str):
    """Return an obstore rooted at `uri` (which must denote a directory)."""
    if _has_scheme(uri):
        return from_url(uri)
    return LocalStore(uri)


def _resolve_local_dir(path: str) -> str | None:
    for candidate in (path, f"/{path}"):
        if Path(candidate).is_dir():
            return candidate
    return None


def _resolve_local_file(path: str) -> str | None:
    for candidate in (path, f"/{path}"):
        if Path(candidate).is_file():
            return candidate
    return None


def resolve_dir(uri: str) -> str | None:
    """Canonicalize a browse target or return None if it doesn't exist."""
    uri = uri.rstrip("/")
    if not uri:
        return None
    if _has_scheme(uri):
        return uri
    return _resolve_local_dir(uri)


_FORMAT_MARKERS: tuple[tuple[str, str], ...] = (
    ("_versions", "lance"),
    ("_delta_log", "delta"),
    ("metadata", "iceberg"),
)


def detect_format(uri: str) -> str:
    """Detect datalake format marker directories; fall back to 'directory'."""
    try:
        store = _open_dir(uri)
    except Exception:
        return "directory"
    for marker, kind in _FORMAT_MARKERS:
        try:
            result = obs.list_with_delimiter(store, prefix=f"{marker}/")
        except Exception:
            continue
        if result.get("objects") or result.get("common_prefixes"):
            return kind
    return "directory"


def list_entries(uri: str) -> tuple[str, list[EntryInfo]]:
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

    entries: list[EntryInfo] = []
    for prefix in result.get("common_prefixes", []):
        name = prefix.rstrip("/").rsplit("/", 1)[-1]
        if not name or name.startswith((".", "_")):
            continue
        child = f"{resolved}/{name}"
        entries.append(EntryInfo(name=name, path=child, kind=detect_format(child)))

    for meta in result.get("objects", []):
        path = str(meta.get("path") or "")
        name = path.rsplit("/", 1)[-1]
        if not name or name.startswith("."):
            continue
        entries.append(
            EntryInfo(
                name=name,
                path=f"{resolved}/{name}",
                kind="file",
                size=meta.get("size"),
            )
        )

    # Directories first, then files; alphabetical within each
    entries.sort(key=lambda e: (e.kind == "file", e.name))
    return resolved, entries


def read_file(uri: str, max_bytes: int) -> tuple[bytes, int] | None:
    """Read a file's contents. Returns (bytes, size) or None if not found.

    Raises ValueError if the file exceeds `max_bytes`.
    """
    target = uri if _has_scheme(uri) else _resolve_local_file(uri)
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
