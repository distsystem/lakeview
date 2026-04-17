"""S3 storage backend — general 1-level browser."""

import pyarrow.fs as pafs

from lakeview.storage.base import EntryInfo


def _detect_format(fs: pafs.FileSystem, path: str) -> str:
    """Cheap format detection via single HEAD-style probe."""
    probes = (("_versions", "lance"), ("_delta_log", "delta"), ("metadata", "iceberg"))
    for marker, kind in probes:
        info = fs.get_file_info(f"{path}/{marker}")
        if info.type == pafs.FileType.Directory:
            return kind
    return "directory"


def list_s3(prefix: str) -> list[EntryInfo]:
    bucket, _, base = prefix.partition("/")
    base_slash = f"{base}/" if base else ""
    try:
        fs, root = pafs.FileSystem.from_uri(f"s3://{prefix}")
        entries = fs.get_file_info(pafs.FileSelector(root, recursive=False))
    except OSError:
        return []

    results = []
    for e in sorted(entries, key=lambda x: x.base_name):
        name = e.base_name
        if not name or name.startswith("."):
            continue
        full_path = f"{bucket}/{base_slash}{name}"
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
