"""S3 storage backend — general 1-level browser.

Inputs and returned paths are `s3://bucket/key` URIs.
"""

import pyarrow.fs as pafs

from lakeview.storage.base import EntryInfo

S3_SCHEME = "s3://"


def _detect_format(fs: pafs.FileSystem, path: str) -> str:
    """Cheap format detection via single HEAD-style probe."""
    probes = (("_versions", "lance"), ("_delta_log", "delta"), ("metadata", "iceberg"))
    for marker, kind in probes:
        info = fs.get_file_info(f"{path}/{marker}")
        if info.type == pafs.FileType.Directory:
            return kind
    return "directory"


def list_s3(uri: str) -> list[EntryInfo]:
    if not uri.startswith(S3_SCHEME):
        raise ValueError(f"expected s3:// URI, got: {uri}")
    body = uri[len(S3_SCHEME) :].rstrip("/")
    try:
        fs, root = pafs.FileSystem.from_uri(uri)
        entries = fs.get_file_info(pafs.FileSelector(root, recursive=False))
    except OSError:
        return []

    results = []
    for e in sorted(entries, key=lambda x: x.base_name):
        name = e.base_name
        if not name or name.startswith("."):
            continue
        full_path = f"{S3_SCHEME}{body}/{name}"
        if e.type == pafs.FileType.Directory:
            if name.startswith("_"):
                continue
            kind = _detect_format(fs, e.path)
            results.append(EntryInfo(name=name, path=full_path, kind=kind))
        elif e.type == pafs.FileType.File:
            results.append(
                EntryInfo(
                    name=name,
                    path=full_path,
                    kind="file",
                    size=e.size,
                )
            )
    # Directories first, then files
    results.sort(key=lambda r: (r.kind == "file", r.name))
    return results
