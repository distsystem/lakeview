"""FastAPI app — typed REST API for Lance datasets.

Run:
    pixi run dev
    # or:
    uvicorn lakeview.app:app --host 0.0.0.0 --port 8766 --reload

Sample queries against sample-data/ (symlinked from agent/output):
    curl localhost:8766/api/datasets?prefix=sample-data
    curl localhost:8766/api/d/sample-data/kaggle.lance/rows?limit=5
    curl localhost:8766/api/d/sample-data/kaggle.lance/runs/0
    curl localhost:8766/api/d/sample-data/kaggle.lance/schema
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from lakeview import lance_io, models

app = FastAPI(title="lakeview", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# -- Dataset browsing --


@app.get("/api/datasets")
def get_datasets(prefix: str = "") -> models.DatasetListResponse:
    resolved, raw = lance_io.list_datasets(prefix)
    datasets = []
    for d in raw:
        kind = d.get("kind", "directory")
        row_count = None
        if kind == "lance":
            ds = lance_io.open_dataset(d["path"])
            row_count = ds.count_rows() if ds else None
        datasets.append(
            models.DatasetEntry(
                name=d["name"],
                path=d["path"],
                kind=kind,
                row_count=row_count,
            )
        )
    return models.DatasetListResponse(prefix=resolved, datasets=datasets)


@app.get("/api/d/{db_path:path}/schema")
def get_schema(db_path: str) -> models.SchemaResponse:
    ds = lance_io.open_dataset(db_path.rstrip("/"))
    if ds is None:
        raise HTTPException(404, f"dataset not found: {db_path}")
    columns = [
        models.ColumnInfo(
            name=f.name,
            type=str(f.type),
            nullable=f.nullable,
        )
        for f in ds.schema
    ]
    return models.SchemaResponse(columns=columns)


# -- Row listing --


@app.get("/api/d/{db_path:path}/rows")
def get_rows(
    db_path: str,
    offset: int = 0,
    limit: int = Query(default=50, le=200),
    status: str = "all",
) -> models.RowListResponse:
    db_path = db_path.rstrip("/")
    ds = lance_io.open_dataset(db_path)
    if ds is None:
        raise HTTPException(404, f"dataset not found: {db_path}")

    all_rows = lance_io.list_all_rows(ds, db_path)
    stats = lance_io.compute_stats(all_rows)
    filtered = lance_io.filter_by_status(all_rows, status)

    page = filtered[offset : offset + limit]
    rows = [
        models.RowSummary(
            row_offset=r.get("row_offset", 0),
            session_id=r.get("session_id"),
            output=r.get("output"),
            error=r.get("error"),
            metadata=r.get("metadata"),
            correct=r.get("correct"),
        )
        for r in page
    ]
    return models.RowListResponse(
        total=len(filtered),
        offset=offset,
        limit=limit,
        rows=rows,
        stats=models.Stats(**stats),
    )


# -- Run detail --


@app.get("/api/d/{db_path:path}/runs/{key}")
def get_run(db_path: str, key: str) -> models.RunDetailResponse:
    db_path = db_path.rstrip("/")
    ds = lance_io.open_dataset(db_path)
    if ds is None:
        raise HTTPException(404, f"dataset not found: {db_path}")

    loaded = lance_io.load_run(ds, key, db_path)
    if loaded is None:
        raise HTTPException(404, f"run not found: {key}")

    row_dict, messages = loaded
    row = models.RowSummary(
        row_offset=0,
        session_id=row_dict.get("session_id"),
        output=row_dict.get("output"),
        error=row_dict.get("error"),
        metadata=row_dict.get("metadata"),
        correct=row_dict.get("correct"),
    )
    return models.RunDetailResponse(row=row, messages=messages)
