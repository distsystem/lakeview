"""Storage layer — root-relative browse via obstore.

Roots are declared at startup from the environment:
  - ``s3``: ``s3://$S3_BUCKET/$S3_PREFIX`` (when both are set)
  - ``local``: the server's cwd

Downstream code always works in terms of ``(root, rel)`` pairs. The root
name maps to a base URI; ``rel`` is joined underneath. Raw schemes and
double-slashes never enter URLs.
"""

from __future__ import annotations

import os
from pathlib import Path

import obstore as obs
from dotenv import load_dotenv
from obstore.store import LocalStore, from_url

from lakeview.models import DatasetEntry

# Auto-load repo-root .env for dev. In prod the orchestrator sets env vars
# directly so this is a no-op.
load_dotenv()


def _load_roots() -> dict[str, str]:
    roots: dict[str, str] = {}
    bucket = os.environ.get("S3_BUCKET")
    prefix = os.environ.get("S3_PREFIX")
    if bucket and prefix:
        roots["s3"] = f"s3://{bucket}/{prefix}"
    roots["local"] = str(Path.cwd())
    return roots


_ROOTS = _load_roots()


def roots() -> dict[str, str]:
    """Map of configured root names to their absolute base URI."""
    return dict(_ROOTS)


def resolve(root: str, rel: str = "") -> str | None:
    """Expand a ``(root, rel)`` pair into the absolute URI obstore wants."""
    base = _ROOTS.get(root)
    if base is None:
        return None
    rel = rel.strip("/")
    return f"{base}/{rel}" if rel else base


def _open_dir(uri: str):
    return from_url(uri) if "://" in uri else LocalStore(uri)


def open_store(root: str, rel: str = ""):
    """Open an obstore rooted at ``(root, rel)``."""
    uri = resolve(root, rel)
    return _open_dir(uri) if uri is not None else None


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


def list_entries(root: str, rel: str = "") -> list[DatasetEntry]:
    """List 1 level under ``(root, rel)``. Entry paths are relative to root."""
    uri = resolve(root, rel)
    if uri is None:
        return []
    try:
        store = _open_dir(uri)
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


def read_file(root: str, rel: str, max_bytes: int) -> tuple[bytes, int] | None:
    """Read a file's contents. Returns (bytes, size) or None if not found.

    Raises ValueError if the file exceeds ``max_bytes``.
    """
    parent_rel, _, name = rel.rpartition("/")
    if not name:
        return None
    parent_uri = resolve(root, parent_rel)
    if parent_uri is None:
        return None
    try:
        store = _open_dir(parent_uri)
        meta = obs.head(store, name)
    except Exception:
        return None
    size = meta.get("size") or 0
    if size > max_bytes:
        raise ValueError(f"file too large: {root}/{rel} ({size} > {max_bytes})")
    data = obs.get(store, name).bytes()
    return bytes(data), size
