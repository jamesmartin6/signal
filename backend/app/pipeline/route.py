"""Routing stage — pure business logic, no LLM call."""

from sqlalchemy.orm import Session

from app.db.models import Lead, LeadStatus, PipelineStage, PipelineStageResult
from app.logging_config import get_pipeline_logger
from app.pipeline.schemas import ClassificationResult, RouteResult

logger = get_pipeline_logger()

PROMPT_VERSION = "route_v1"  # no LLM involved; versioned for consistency with other stage records
MODEL_NAME = "rules-based"

CONFIDENCE_REVIEW_THRESHOLD = 0.6

_QUEUE_BY_CATEGORY = {
    "decision_maker": "decision_maker_queue",
    "technical": "technical_queue",
    "not_relevant": "discard",
}


def route_lead(classification: ClassificationResult) -> RouteResult:
    if classification.confidence < CONFIDENCE_REVIEW_THRESHOLD:
        return RouteResult(
            queue="needs_review",
            reason=f"confidence {classification.confidence:.2f} below {CONFIDENCE_REVIEW_THRESHOLD} threshold",
        )
    queue = _QUEUE_BY_CATEGORY[classification.category]
    return RouteResult(
        queue=queue,
        reason=f"category={classification.category}, confidence={classification.confidence:.2f}",
    )


def run_route(db: Session, lead: Lead, classification: ClassificationResult) -> RouteResult:
    lead.status = LeadStatus.routing
    db.commit()

    result = route_lead(classification)

    db.add(
        PipelineStageResult(
            lead_id=lead.id,
            stage=PipelineStage.route,
            prompt_version=PROMPT_VERSION,
            input=classification.model_dump(),
            output=result.model_dump(),
            model=MODEL_NAME,
            latency_ms=0,
            success=True,
        )
    )
    lead.status = LeadStatus.done
    db.commit()
    logger.info(
        "pipeline stage completed",
        extra={
            "lead_id": str(lead.id),
            "stage": "route",
            "prompt_version": PROMPT_VERSION,
            "latency_ms": 0,
            "success": True,
        },
    )
    return result
