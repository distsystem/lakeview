"""Storage layer — browse S3 and local directories, detect datalake formats.

Path convention: `s3://bucket/prefix` routes to S3; anything else is a local
path. No implicit fallback — an unmatched local path returns empty.
"""

from lakeview.storage.base import EntryInfo
from lakeview.storage.local import list_local, resolve_local
from lakeview.storage.s3 import list_s3

S3_SCHEME = "s3://"


def is_s3(path: str) -> bool:
    return path.startswith(S3_SCHEME)


def list_entries(prefix: str) -> tuple[str, list[EntryInfo]]:
    if not prefix:
        return "", []
    if is_s3(prefix):
        return prefix, list_s3(prefix)
    resolved = resolve_local(prefix)
    if resolved:
        return resolved, list_local(resolved)
    return prefix, []
