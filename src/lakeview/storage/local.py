"""Local filesystem storage backend."""

import os

from lakeview.storage.base import EntryInfo


def resolve_local(path: str) -> str | None:
    if os.path.isdir(path):
        return path
    absolute = f"/{path}"
    if os.path.isdir(absolute):
        return absolute
    return None


def detect_format(path: str) -> str:
    if os.path.isdir(os.path.join(path, "_versions")):
        return "lance"
    if os.path.isdir(os.path.join(path, "_delta_log")):
        return "delta"
    meta = os.path.join(path, "metadata")
    if os.path.isdir(meta) and any(f.endswith(".metadata.json") for f in os.listdir(meta)):
        return "iceberg"
    return "directory"


def list_local(prefix: str) -> list[EntryInfo]:
    if not os.path.isdir(prefix):
        return []
    entries = []
    for name in sorted(os.listdir(prefix)):
        if name.startswith("."):
            continue
        full = os.path.join(prefix, name)
        if os.path.isdir(full):
            if name.startswith("_"):
                continue
            entries.append(EntryInfo(name=name, path=full, kind=detect_format(full)))
        else:
            try:
                size = os.path.getsize(full)
            except OSError:
                size = None
            entries.append(EntryInfo(name=name, path=full, kind="file", size=size))
    # Directories first, then files; alphabetical within each
    entries.sort(key=lambda e: (e.kind == "file", e.name))
    return entries
