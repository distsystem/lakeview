"""Pydantic response models — the API contract."""

from typing import Any

from pydantic import BaseModel


# -- App config --


class ConfigResponse(BaseModel):
    default_prefix: str


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
