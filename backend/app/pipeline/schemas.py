from typing import Literal

from pydantic import BaseModel, Field


class ExtractedProfile(BaseModel):
    title: str
    company: str
    seniority: Literal["junior", "mid", "senior", "exec"]
    industry: str | None = None


class ClassificationResult(BaseModel):
    category: Literal["decision_maker", "technical", "not_relevant"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class EnrichmentResult(BaseModel):
    company_domain: str
    company_size_bucket: Literal["startup", "smb", "mid_market", "enterprise"]
    industry: str | None
    industry_source: Literal["extracted", "lookup_fallback"]


class RouteResult(BaseModel):
    queue: Literal["decision_maker_queue", "technical_queue", "needs_review", "discard"]
    reason: str
