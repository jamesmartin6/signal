"""Enrichment stage — no LLM call and no external data vendor. Per the build
plan, this stage is about the pipeline shape, not real data integration: it
fills in a company domain guess and a size bucket via deterministic rules,
and backfills industry from a small lookup table when extraction couldn't
infer one from the bio."""

import hashlib
import re

from sqlalchemy.orm import Session

from app.db.models import Lead, LeadStatus, PipelineStage, PipelineStageResult
from app.llm.simulator import INDUSTRY_KEYWORDS
from app.logging_config import get_pipeline_logger
from app.pipeline.schemas import EnrichmentResult, ExtractedProfile

logger = get_pipeline_logger()

PROMPT_VERSION = "enrich_v1"  # no LLM involved; versioned for consistency with other stage records
MODEL_NAME = "rules-based"

_LEGAL_SUFFIXES_RE = re.compile(r"\b(incorporated|inc|corporation|corp|llc|ltd|company|co)\b\.?", re.IGNORECASE)
_SIZE_BUCKETS = ["startup", "smb", "mid_market", "enterprise"]
_FALLBACK_INDUSTRIES = [label for label, _ in INDUSTRY_KEYWORDS]


def _slugify_company(company: str) -> str:
    cleaned = _LEGAL_SUFFIXES_RE.sub("", company)
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "", cleaned)
    return cleaned.lower() or "company"


def _stable_index(key: str, n: int) -> int:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest, 16) % n


def enrich_profile(profile: ExtractedProfile) -> EnrichmentResult:
    domain = f"{_slugify_company(profile.company)}.com"
    size_bucket = _SIZE_BUCKETS[_stable_index(profile.company, len(_SIZE_BUCKETS))]

    if profile.industry:
        return EnrichmentResult(
            company_domain=domain,
            company_size_bucket=size_bucket,
            industry=profile.industry,
            industry_source="extracted",
        )

    fallback_industry = _FALLBACK_INDUSTRIES[_stable_index(profile.company, len(_FALLBACK_INDUSTRIES))]
    return EnrichmentResult(
        company_domain=domain,
        company_size_bucket=size_bucket,
        industry=fallback_industry,
        industry_source="lookup_fallback",
    )


def run_enrich(db: Session, lead: Lead, profile: ExtractedProfile) -> EnrichmentResult:
    lead.status = LeadStatus.enriching
    db.commit()

    result = enrich_profile(profile)

    db.add(
        PipelineStageResult(
            lead_id=lead.id,
            stage=PipelineStage.enrich,
            prompt_version=PROMPT_VERSION,
            input=profile.model_dump(),
            output=result.model_dump(),
            model=MODEL_NAME,
            latency_ms=0,
            success=True,
        )
    )
    lead.status = LeadStatus.routing
    db.commit()
    logger.info(
        "pipeline stage completed",
        extra={
            "lead_id": str(lead.id),
            "stage": "enrich",
            "prompt_version": PROMPT_VERSION,
            "latency_ms": 0,
            "success": True,
        },
    )
    return result
