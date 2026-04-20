"""FastAPI app — generic datalake frontend with plugin-enriched views.

Run:
    pixi run dev
    # or:
    uvicorn lakeview.app:app --host 0.0.0.0 --port 8766 --reload
"""

import mimetypes
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from lakeview import formats, models, plugins, storage

MAX_PREVIEW_BYTES = 5 * 1024 * 1024  # 5 MB cap on file previews
# obstore/lance release the GIL during I/O, so threads parallelize effectively.
_DATASET_PROBE_WORKERS = 32

app = FastAPI(title="lakeview", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/roots")
def get_roots() -> models.RootsResponse:
    items = [models.RootInfo(name=n, uri=u) for n, u in storage.roots().items()]
    return models.RootsResponse(
        roots=items,
        default=items[0].name if items else "",
    )


def _open_or_404(root: str, path: str) -> formats.DatasetReader:
    uri = storage.resolve(root, path.rstrip("/"))
    if uri is None:
        raise HTTPException(404, f"unknown root: {root}")
    reader = formats.open_dataset(uri, "lance")
    if reader is None:
        raise HTTPException(404, f"dataset not found: {root}/{path}")
    return reader


@app.get("/api/file/{root}/{path:path}")
def get_file(root: str, path: str) -> Response:
    """Serve raw file bytes from any root, for preview in the frontend."""
    mime, _ = mimetypes.guess_type(path)
    media_type = mime or "application/octet-stream"
    try:
        result = storage.read_file(root, path, MAX_PREVIEW_BYTES)
    except ValueError as e:
        raise HTTPException(413, str(e)) from e
    if result is None:
        raise HTTPException(404, f"file not found: {root}/{path}")
    data, _ = result
    return Response(content=data, media_type=media_type)


# -- Dataset browsing --


@app.get("/api/datasets")
def get_datasets(root: str, path: str = "") -> models.DatasetListResponse:
    entries = storage.list_entries(root, path)
    dir_entries = [e for e in entries if e.kind == "directory"]
    if dir_entries:
        parent_store = storage.open_store(root, path)

        def upgrade(entry: models.DatasetEntry) -> None:
            p = storage.Probe(parent_store, entry.name)
            cls = formats.detect(p)
            if cls is None:
                return
            uri = storage.resolve(root, entry.path)
            reader = cls.open(uri) if uri else None
            if reader is None:
                return
            entry.kind = cls.KIND
            entry.row_count = reader.count_rows()

        with ThreadPoolExecutor(max_workers=_DATASET_PROBE_WORKERS) as pool:
            list(pool.map(upgrade, dir_entries))
    return models.DatasetListResponse(root=root, path=path, datasets=entries)


# -- Dataset info (with plugin detection) --


@app.get("/api/d/{root}/{path:path}/info")
def get_info(root: str, path: str) -> models.DatasetInfoResponse:
    reader = _open_or_404(root, path)
    plugin = plugins.detect_plugin(reader.schema)
    columns = [
        models.ColumnInfo(name=f.name, type=str(f.type), nullable=f.nullable)
        for f in reader.schema
    ]
    return models.DatasetInfoResponse(
        row_count=reader.count_rows(),
        columns=columns,
        plugin=plugin.name if plugin else None,
        filters=plugin.available_filters() if plugin else [],
    )


@app.get("/api/d/{root}/{path:path}/schema")
def get_schema(root: str, path: str) -> models.SchemaResponse:
    reader = _open_or_404(root, path)
    columns = [
        models.ColumnInfo(name=f.name, type=str(f.type), nullable=f.nullable)
        for f in reader.schema
    ]
    return models.SchemaResponse(columns=columns)


# -- Generic rows --


@app.get("/api/d/{root}/{path:path}/rows")
def get_rows(
    root: str,
    path: str,
    offset: int = 0,
    limit: int = Query(default=50, le=200),
) -> models.GenericRowListResponse:
    reader = _open_or_404(root, path)
    total = reader.count_rows()
    rows = reader.scan(offset, limit)
    return models.GenericRowListResponse(
        total=total,
        offset=offset,
        limit=limit,
        rows=rows,
    )


@app.get("/api/d/{root}/{path:path}/row/{offset}")
def get_row(root: str, path: str, offset: int) -> dict:
    reader = _open_or_404(root, path)
    row = reader.get_row(offset)
    if row is None:
        raise HTTPException(404, f"row not found at offset {offset}")
    return row


# -- Plugin-enriched views --


@app.get("/api/d/{root}/{path:path}/view")
def get_view(
    root: str,
    path: str,
    offset: int = 0,
    limit: int = Query(default=50, le=200),
    filter: str = "all",
) -> models.PluginViewResponse:
    reader = _open_or_404(root, path)
    plugin = plugins.detect_plugin(reader.schema)
    if not plugin:
        raise HTTPException(404, "no plugin detected for this schema")
    stats, total, rows = plugin.view(reader, filter, offset, limit)
    return models.PluginViewResponse(
        total=total,
        offset=offset,
        limit=limit,
        rows=rows,
        stats=stats,
        plugin=plugin.name,
    )


@app.get("/api/d/{root}/{path:path}/view/{key}")
def get_view_detail(root: str, path: str, key: str) -> models.PluginDetailResponse:
    reader = _open_or_404(root, path)
    plugin = plugins.detect_plugin(reader.schema)
    if not plugin:
        raise HTTPException(404, "no plugin detected for this schema")
    data = plugin.detail(reader, key)
    if data is None:
        raise HTTPException(404, f"run not found: {key}")
    return models.PluginDetailResponse(plugin=plugin.name, data=data)
