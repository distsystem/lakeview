"""Storage layer — browse S3 and local directories, detect datalake formats."""

from lakeview.storage.base import EntryInfo
from lakeview.storage.local import list_local, resolve_local
from lakeview.storage.s3 import list_s3


def list_entries(prefix: str) -> tuple[str, list[EntryInfo]]:
    if not prefix:
        return "", []
    # Try local paths first
    resolved = resolve_local(prefix)
    if resolved:
        return resolved, list_local(resolved)
    return prefix, list_s3(prefix)
