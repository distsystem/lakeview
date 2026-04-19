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

from lakeview import formats, models, storage
from lakeview.plugins import registry

MAX_PREVIEW_BYTES = 5 * 1024 * 1024  # 5 MB cap on file previews

app = FastAPI(title="lakeview", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _open_or_404(db_path: str) -> tuple[formats.base.DatasetReader, str]:
    """Resolve path, detect format, open dataset — or raise 404."""
    db_path = db_path.rstrip("/")
    resolved = storage.resolve_dir(db_path)
    if resolved is None:
        raise HTTPException(404, f"dataset not found: {db_path}")
    kind = storage.detect_format(resolved)
    reader = formats.open_dataset(resolved, kind)
    if reader is None:
        raise HTTPException(404, f"dataset not found: {db_path}")
    return reader, kind


@app.get("/api/file/{path:path}")
def get_file(path: str) -> Response:
    """Serve raw file bytes from any storage backend, for preview in the frontend."""
    mime, _ = mimetypes.guess_type(path)
    media_type = mime or "application/octet-stream"
    try:
        result = storage.read_file(path, MAX_PREVIEW_BYTES)
    except ValueError as e:
        raise HTTPException(413, str(e)) from e
    if result is None:
        raise HTTPException(404, f"file not found: {path}")
    data, _ = result
    return Response(content=data, media_type=media_type)


# -- Dataset browsing --


@app.get("/api/datasets")
def get_datasets(prefix: str = "") -> models.DatasetListResponse:
    resolved, entries = storage.list_entries(prefix)
    datasets = []
    for e in entries:
        row_count = e.row_count
        if e.kind == "lance" and row_count is None:
            reader = formats.open_dataset(e.path, e.kind)
            row_count = reader.count_rows() if reader else None
        datasets.append(
            models.DatasetEntry(
                name=e.name,
                path=e.path,
                kind=e.kind,
                row_count=row_count,
                size=e.size,
            )
        )
    return models.DatasetListResponse(prefix=resolved, datasets=datasets)


# -- Dataset info (with plugin detection) --


@app.get("/api/d/{db_path:path}/info")
def get_info(db_path: str) -> models.DatasetInfoResponse:
    reader, _ = _open_or_404(db_path)
    plugin = registry.detect_plugin(reader.schema)
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


@app.get("/api/d/{db_path:path}/schema")
def get_schema(db_path: str) -> models.SchemaResponse:
    reader, _ = _open_or_404(db_path)
    columns = [
        models.ColumnInfo(name=f.name, type=str(f.type), nullable=f.nullable)
        for f in reader.schema
    ]
    return models.SchemaResponse(columns=columns)


# -- Generic rows --


@app.get("/api/d/{db_path:path}/rows")
def get_rows(
    db_path: str,
    offset: int = 0,
    limit: int = Query(default=50, le=200),
) -> models.GenericRowListResponse:
    reader, _ = _open_or_404(db_path)
    total = reader.count_rows()
    rows = reader.scan(offset, limit)
    return models.GenericRowListResponse(
        total=total,
        offset=offset,
        limit=limit,
        rows=rows,
    )


@app.get("/api/d/{db_path:path}/row/{offset}")
def get_row(db_path: str, offset: int) -> dict:
    reader, _ = _open_or_404(db_path)
    row = reader.get_row(offset)
    if row is None:
        raise HTTPException(404, f"row not found at offset {offset}")
    return row


# -- Plugin-enriched views --


@app.get("/api/d/{db_path:path}/view")
def get_view(
    db_path: str,
    offset: int = 0,
    limit: int = Query(default=50, le=200),
    filter: str = "all",
) -> models.PluginViewResponse:
    reader, _ = _open_or_404(db_path)
    plugin = registry.detect_plugin(reader.schema)
    if not plugin:
        raise HTTPException(404, "no plugin detected for this schema")

    # Load all rows (excluding heavy columns) for filtering + stats
    exclude = {"messages"}
    cols = [f.name for f in reader.schema if f.name not in exclude]
    all_rows = reader.scan(0, reader.count_rows(), columns=cols)
    for i, r in enumerate(all_rows):
        r["row_offset"] = i

    stats = plugin.summarize_rows(all_rows)
    filtered = plugin.filter_rows(all_rows, filter)
    page = filtered[offset : offset + limit]
    sidebar_rows = [
        plugin.sidebar_row(r) | {"row_offset": r["row_offset"]} for r in page
    ]

    return models.PluginViewResponse(
        total=len(filtered),
        offset=offset,
        limit=limit,
        rows=sidebar_rows,
        stats=stats,
        plugin=plugin.name,
    )


@app.get("/api/d/{db_path:path}/view/{key}")
def get_view_detail(db_path: str, key: str) -> models.PluginDetailResponse:
    reader, _ = _open_or_404(db_path)
    plugin = registry.detect_plugin(reader.schema)
    if not plugin:
        raise HTTPException(404, "no plugin detected for this schema")

    # Resolve key (plugin-specific: numeric offset or session_id)
    offset = getattr(
        plugin, "resolve_key", lambda r, k: int(k) if k.isdigit() else None
    )(reader, key)
    if offset is None:
        raise HTTPException(404, f"run not found: {key}")

    data = plugin.detail(reader, offset)
    if data is None:
        raise HTTPException(404, f"run not found at offset {offset}")

    return models.PluginDetailResponse(plugin=plugin.name, data=data)
