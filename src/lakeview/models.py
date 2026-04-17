"""Pydantic response models — the API contract.

Generic models only. Plugin-specific data is returned as opaque dicts.
"""

from pydantic import BaseModel


# -- Dataset browsing --


class DatasetEntry(BaseModel):
    name: str
    path: str
    kind: str  # "lance", "parquet", "delta", "iceberg", "directory", "file"
    row_count: int | None = None
    size: int | None = None  # bytes, only for "file"


class DatasetListResponse(BaseModel):
    prefix: str
    datasets: list[DatasetEntry]


class ColumnInfo(BaseModel):
    name: str
    type: str
    nullable: bool


class SchemaResponse(BaseModel):
    columns: list[ColumnInfo]


# -- Dataset info (with plugin detection) --


class DatasetInfoResponse(BaseModel):
    row_count: int
    columns: list[ColumnInfo]
    plugin: str | None = None
    filters: list[str] = []


# -- Generic rows --


class GenericRowListResponse(BaseModel):
    total: int
    offset: int
    limit: int
    rows: list[dict]


# -- Plugin-enriched views --


class PluginViewResponse(BaseModel):
    total: int
    offset: int
    limit: int
    rows: list[dict]
    stats: dict | None = None
    plugin: str


class PluginDetailResponse(BaseModel):
    plugin: str
    data: dict
