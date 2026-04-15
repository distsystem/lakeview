"""S3 storage backend."""

import pyarrow.fs as pafs

from lakeview.storage.base import EntryInfo


def list_s3(prefix: str) -> list[EntryInfo]:
    bucket, _, base = prefix.partition("/")
    base_slash = f"{base}/" if base else ""
    try:
        fs, root = pafs.FileSystem.from_uri(f"s3://{prefix}")
        entries = fs.get_file_info(pafs.FileSelector(root, recursive=False))
    except OSError:
        return []

    runs = sorted(
        (e for e in entries if e.type == pafs.FileType.Directory),
        key=lambda e: e.base_name,
    )
    datasets = []
    for run in runs:
        subs = fs.get_file_info(pafs.FileSelector(run.path, recursive=False))
        for sub in sorted(subs, key=lambda e: e.base_name):
            if sub.type == pafs.FileType.Directory:
                name = f"{run.base_name}/{sub.base_name}"
                datasets.append(EntryInfo(
                    name=name,
                    path=f"{bucket}/{base_slash}{name}",
                    kind="lance",
                ))
    return datasets
