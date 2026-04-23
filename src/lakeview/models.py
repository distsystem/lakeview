"""Pydantic response models — the API contract."""

from pydantic import BaseModel

from lakeview.plugins.agent_run.models import (
    AgentRunDetail,
    AgentRunSidebar,
    AgentRunStats,
)


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


# -- Plugin-enriched views --
#
# Today's envelope is hard-typed against the agent-run plugin because it's the
# only one. When a second plugin lands, either carve out per-plugin envelope
# types or switch to a generic ``rows: list[Any]`` (at the cost of schema
# specificity in the generated frontend types).


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
