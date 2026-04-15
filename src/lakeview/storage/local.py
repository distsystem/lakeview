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
        full = os.path.join(prefix, name)
        if not os.path.isdir(full) or name.startswith(("_", ".")):
            continue
        entries.append(EntryInfo(name=name, path=full, kind=detect_format(full)))
    return entries
