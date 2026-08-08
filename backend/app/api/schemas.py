import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models import LeadStatus, PipelineStage


class StageResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stage: PipelineStage
    prompt_version: str
    input: dict
    output: dict
    model: str
    latency_ms: int
    success: bool
    created_at: datetime


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    raw_input: dict
    status: LeadStatus
    error: str | None
    created_at: datetime
    updated_at: datetime


class LeadDetailOut(LeadOut):
    stage_results: list[StageResultOut]


class PaginatedLeads(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[LeadOut]


class SkippedRowOut(BaseModel):
    row_number: int
    reason: str


class UploadResponse(BaseModel):
    created: int
    skipped: int
    skipped_rows: list[SkippedRowOut]
    lead_ids: list[uuid.UUID]


class EvalRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prompt_version: str
    stage: PipelineStage
    total_cases: int
    passed_cases: int
    pass_rate: float
    created_at: datetime
