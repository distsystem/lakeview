"""FastAPI app — generic datalake frontend with plugin-enriched views.

Run:
    pixi run dev
    # or:
    uvicorn lakeview.app:app --host 0.0.0.0 --port 8766 --reload
"""

import mimetypes

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from lakeview import core, models, plugins, readers, roots  # noqa: F401

_ = readers  # importing registers LanceReader via side effect

MAX_PREVIEW_BYTES = 5 * 1024 * 1024  # 5 MB cap on file previews

app = FastAPI(title="lakeview", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/roots")
def get_roots() -> models.RootsResponse:
    items = [
        models.RootInfo(name=b.name, uri=b.uri, kind=b.kind, driver=b.driver)
        for b in roots.list_backends()
    ]
    return models.RootsResponse(
        roots=items,
        default=items[0].name if items else "",
    )


def _backend_or_404(root: str):
    backend = roots.get_backend(root)
    if backend is None:
        raise HTTPException(404, f"unknown root: {root}")
    return backend


def _open_or_404(root: str, path: str) -> core.DatasetReader:
    reader = _backend_or_404(root).open_dataset(path.rstrip("/"))
    if reader is None:
        raise HTTPException(404, f"dataset not found: {root}/{path}")
    return reader


@app.get("/api/file/{root}/{path:path}")
def get_file(root: str, path: str) -> Response:
    mime, _ = mimetypes.guess_type(path)
    try:
        result = _backend_or_404(root).read_file(path, MAX_PREVIEW_BYTES)
    except ValueError as e:
        raise HTTPException(413, str(e)) from e
    if result is None:
        raise HTTPException(404, f"file not found: {root}/{path}")
    data, _ = result
    return Response(content=data, media_type=mime or "application/octet-stream")


# -- Dataset browsing --


@app.get("/api/datasets")
def get_datasets(root: str, path: str = "") -> models.DatasetListResponse:
    entries = _backend_or_404(root).list_entries(path)
    return models.DatasetListResponse(root=root, path=path, datasets=entries)


# -- Dataset info (with plugin detection) --


def _column_infos(reader: core.DatasetReader) -> list[models.ColumnInfo]:
    return [
        models.ColumnInfo(
            name=f.name,
            type=str(f.type),
            nullable=f.nullable,
            is_blob=reader.is_blob_column(f),
        )
        for f in reader.schema
    ]


@app.get("/api/d/{root}/{path:path}/info")
def get_info(root: str, path: str) -> models.DatasetInfoResponse:
    reader = _open_or_404(root, path)
    plugin = plugins.detect_plugin(reader.schema)
    return models.DatasetInfoResponse(
        row_count=reader.count_rows(),
        columns=_column_infos(reader),
        plugin=plugin.name if plugin else None,
        filters=plugin.available_filters() if plugin else [],
    )


@app.get("/api/d/{root}/{path:path}/schema")
def get_schema(root: str, path: str) -> models.SchemaResponse:
    reader = _open_or_404(root, path)
    return models.SchemaResponse(columns=_column_infos(reader))


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


@app.get("/api/d/{root}/{path:path}/blob/{offset}/{column}")
def get_blob(root: str, path: str, offset: int, column: str) -> Response:
    """Stream one cell's raw bytes with a detected Content-Type.

    Covers v1 / v2 Lance blob columns and plain binary columns. Non-binary
    columns 404.
    """
    reader = _open_or_404(root, path)
    try:
        result = reader.read_blob(offset, column)
    except Exception as e:
        raise HTTPException(404, f"blob not available: {e}") from e
    if result is None:
        raise HTTPException(404, f"blob not found: {column}@{offset}")
    data, uri = result
    mime = core.detect_mime(data[:2048], uri)
    return Response(
        content=data,
        media_type=mime,
        headers={"Cache-Control": "public, max-age=3600"},
    )


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
