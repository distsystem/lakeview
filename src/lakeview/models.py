"""Pydantic response models — the API contract."""

from typing import Any

from pydantic import BaseModel


# -- Roots --


class RootInfo(BaseModel):
    name: str  # short id used in URLs: "s3", "local", "polaris"
    uri: str  # absolute base the root resolves to (for display)
    kind: str = "storage"  # "storage" or "namespace"
    driver: str = ""  # "local" / "s3" for storage; "polaris" / ... for namespace


class RootsResponse(BaseModel):
    roots: list[RootInfo]
    default: str  # first-configured root name


# -- Dataset browsing --


class DatasetEntry(BaseModel):
    name: str
    path: str  # relative to the current root
    kind: (
        str  # "lance", "parquet", "delta", "iceberg", "directory", "file", "namespace"
    )
    row_count: int | None = None
    size: int | None = None  # bytes, only for "file"


class DatasetListResponse(BaseModel):
    root: str
    path: str  # relative prefix within the root
    datasets: list[DatasetEntry]


class ColumnInfo(BaseModel):
    name: str
    type: str
    nullable: bool
    is_blob: bool = False


class SchemaResponse(BaseModel):
    columns: list[ColumnInfo]


class DatasetInfoResponse(BaseModel):
    row_count: int
    columns: list[ColumnInfo]
    plugin: str | None = None
    filters: list[str] = []


class GenericRowListResponse(BaseModel):
    total: int
    offset: int
    limit: int
    rows: list[dict]


# -- Agent-run plugin outputs --


class AgentRunStats(BaseModel):
    total: int
    ok: int
    wrong: int
    error: int
    pending: int
    accuracy: float | None = None


class AgentRunSidebar(BaseModel):
    row_offset: int
    session_id: str | None = None
    correct: bool | None = None
    error: str | None = None
    output: Any | None = None
    metadata: Any | None = None


class AgentRunDetail(BaseModel):
    row: dict
    messages: list[dict]


# -- Plugin-enriched views --


class PluginViewResponse(BaseModel):
    total: int
    offset: int
    limit: int
    rows: list[AgentRunSidebar]
    stats: AgentRunStats | None = None
    plugin: str


class PluginDetailResponse(BaseModel):
    plugin: str
    data: AgentRunDetail
