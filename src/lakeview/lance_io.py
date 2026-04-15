"""Lance dataset I/O — open, cache, query.

Extracted and generalized from agent/viewer/app.py.
"""

import json
import os
import re

import lance
import pyarrow.fs as pafs

_SESSION_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_JSON_FIELDS = ("parts", "usage", "metadata")


# -- URI resolution --


def resolve_uri(db_path: str) -> str:
    if os.path.exists(db_path):
        return os.path.abspath(db_path)
    absolute = f"/{db_path}"
    if os.path.exists(absolute):
        return absolute
    return f"s3://{db_path}"


# -- Dataset registry (open + cache) --

_datasets: dict[str, lance.LanceDataset] = {}


def open_dataset(db_path: str) -> lance.LanceDataset | None:
    if db_path in _datasets:
        ds = _datasets[db_path]
        ds.checkout_version(ds.latest_version)
        return ds
    try:
        ds = lance.dataset(resolve_uri(db_path))
        _datasets[db_path] = ds
        return ds
    except Exception:
        return None


# -- Row listing (without messages) --

_rows_cache: dict[str, tuple[int, list[dict]]] = {}


def list_all_rows(ds: lance.LanceDataset, db_path: str) -> list[dict]:
    ver = ds.version
    cached = _rows_cache.get(db_path)
    if cached and cached[0] == ver:
        return cached[1]

    total = ds.count_rows()
    if not total:
        _rows_cache[db_path] = (ver, [])
        return []

    cols = [f.name for f in ds.schema if f.name != "messages"]
    rows = [
        {**row, "row_offset": i}
        for i, row in enumerate(ds.to_table(columns=cols).to_pylist())
    ]
    _rows_cache[db_path] = (ver, rows)
    return rows


# -- Single run (with messages) --


def _decode_json(row: dict) -> dict:
    for col in _JSON_FIELDS:
        v = row.get(col)
        if isinstance(v, str):
            try:
                row[col] = json.loads(v)
            except json.JSONDecodeError:
                pass
    return row


def _decode_messages(messages: list) -> list[dict]:
    result = []
    for msg in messages:
        msg = _decode_json(dict(msg) if not isinstance(msg, dict) else msg)
        if "parts" in msg and isinstance(msg["parts"], list):
            msg["parts"] = [_decode_json(dict(p) if not isinstance(p, dict) else p) for p in msg["parts"]]
        result.append(msg)
    return result


def _resolve_offset(ds: lance.LanceDataset, db_path: str, key: str) -> int | None:
    """Resolve a session_id key to a row offset via the cached row list."""
    if key.isdigit():
        return int(key)
    if not _SESSION_ID_RE.match(key):
        return None
    rows = list_all_rows(ds, db_path)
    for r in rows:
        if r.get("session_id") == key:
            return r["row_offset"]
    return None


def load_run(ds: lance.LanceDataset, key: str, db_path: str = "") -> tuple[dict, list[dict]] | None:
    offset = _resolve_offset(ds, db_path, key)
    if offset is None:
        return None

    tbl = ds.to_table(offset=offset, limit=1)
    if tbl.num_rows == 0:
        return None

    row = tbl.to_pylist()[0]
    raw_messages = row.pop("messages", None) or []
    messages = _decode_messages(raw_messages)
    return row, messages


# -- Dataset listing (S3 + local) --


def list_s3(prefix: str) -> list[dict]:
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
                datasets.append({"name": name, "path": f"{bucket}/{base_slash}{name}"})
    return datasets


def is_lance(path: str) -> bool:
    return os.path.isdir(path) and os.path.isdir(os.path.join(path, "_versions"))


def list_local(prefix: str) -> list[dict]:
    if not os.path.isdir(prefix):
        return []
    entries = []
    for d in sorted(os.listdir(prefix)):
        full = os.path.join(prefix, d)
        if not os.path.isdir(full) or d.startswith(("_", ".")):
            continue
        entries.append({
            "name": d,
            "path": full,
            "kind": "lance" if is_lance(full) else "directory",
        })
    return entries


def list_datasets(prefix: str) -> tuple[str, list[dict]]:
    if not prefix:
        return "", []
    # Try local paths first
    if os.path.isdir(prefix):
        return prefix, list_local(prefix)
    absolute = f"/{prefix}"
    if os.path.isdir(absolute):
        return absolute, list_local(absolute)
    return prefix, list_s3(prefix)


# -- Stats --


def compute_stats(rows: list[dict]) -> dict:
    total = len(rows)
    ok = sum(1 for r in rows if r.get("correct") is True)
    error = sum(1 for r in rows if r.get("error"))
    wrong = sum(1 for r in rows if not r.get("error") and r.get("correct") is False)
    pending = total - ok - wrong - error
    return {
        "total": total,
        "ok": ok,
        "wrong": wrong,
        "error": error,
        "pending": pending,
        "accuracy": ok / total if total else None,
    }


def filter_by_status(rows: list[dict], status: str) -> list[dict]:
    if status in ("all", "", None):
        return rows
    checks = {
        "ok": lambda r: r.get("correct") is True,
        "error": lambda r: bool(r.get("error")),
        "wrong": lambda r: not r.get("error") and r.get("correct") is False,
        "pending": lambda r: not r.get("error") and r.get("correct") is None,
    }
    check = checks.get(status)
    if check is None:
        return rows
    return [r for r in rows if check(r)]
