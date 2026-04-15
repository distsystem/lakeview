"""Pydantic response models — the API contract.

These models define the JSON shapes that the frontend consumes.
TypeScript types are generated from the OpenAPI spec that FastAPI
builds from these models.
"""

import datetime

from pydantic import BaseModel


# -- Dataset browsing --


class DatasetEntry(BaseModel):
    name: str
    path: str
    kind: str  # "lance" or "directory"
    row_count: int | None = None


class DatasetListResponse(BaseModel):
    prefix: str
    datasets: list[DatasetEntry]


class ColumnInfo(BaseModel):
    name: str
    type: str
    nullable: bool


class SchemaResponse(BaseModel):
    columns: list[ColumnInfo]


# -- Row listing --


class Stats(BaseModel):
    total: int
    ok: int
    wrong: int
    error: int
    pending: int
    accuracy: float | None = None


class RowSummary(BaseModel):
    row_offset: int
    session_id: str | None = None
    output: dict | None = None
    error: str | None = None
    metadata: dict | None = None
    correct: bool | None = None


class RowListResponse(BaseModel):
    total: int
    offset: int
    limit: int
    rows: list[RowSummary]
    stats: Stats


# -- Run detail --


class PartRecord(BaseModel):
    part_kind: str
    content: str | None = None
    tool_name: str | None = None
    tool_call_id: str | None = None
    args: dict | str | None = None
    provider_details: dict | str | None = None
    timestamp: str | None = None


class MessageRecord(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    kind: str
    timestamp: str | datetime.datetime | None = None
    run_id: str | None = None
    parts: list[PartRecord] = []
    instructions: str | None = None
    model_name: str | None = None
    finish_reason: str | None = None
    provider_response_id: str | None = None
    usage: dict | None = None
    metadata: dict | None = None


class RunDetailResponse(BaseModel):
    row: RowSummary
    messages: list[dict]
