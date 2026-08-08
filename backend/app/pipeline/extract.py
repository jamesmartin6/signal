from sqlalchemy.orm import Session

from app.db.models import Lead, LeadStatus, PipelineStage, PipelineStageResult
from app.llm.client import LLMClient, LLMOutputInvalidError, generate_structured
from app.logging_config import get_pipeline_logger
from app.pipeline.errors import PipelineStageFailed
from app.pipeline.prompts.extract_v1 import PROMPT_VERSION, build_prompt
from app.pipeline.schemas import ExtractedProfile

logger = get_pipeline_logger()


def run_extract(db: Session, lead: Lead, client: LLMClient) -> ExtractedProfile:
    lead.status = LeadStatus.extracting
    db.commit()

    system, user = build_prompt(lead.raw_input)

    try:
        result = generate_structured(client, system=system, user=user, schema=ExtractedProfile)
    except LLMOutputInvalidError as exc:
        db.add(
            PipelineStageResult(
                lead_id=lead.id,
                stage=PipelineStage.extract,
                prompt_version=PROMPT_VERSION,
                input={"system": system, "user": user},
                output={"error": str(exc), "raw_response": exc.raw_text},
                model=exc.model,
                latency_ms=exc.latency_ms,
                success=False,
            )
        )
        lead.status = LeadStatus.failed
        lead.error = f"extract: {exc}"
        db.commit()
        logger.error(
            "pipeline stage failed",
            extra={
                "lead_id": str(lead.id),
                "stage": "extract",
                "prompt_version": PROMPT_VERSION,
                "latency_ms": exc.latency_ms,
                "success": False,
            },
        )
        raise PipelineStageFailed("extract", str(exc)) from exc

    db.add(
        PipelineStageResult(
            lead_id=lead.id,
            stage=PipelineStage.extract,
            prompt_version=PROMPT_VERSION,
            input={"system": system, "user": user},
            output=result.output.model_dump(),
            model=result.model,
            latency_ms=result.latency_ms,
            success=True,
        )
    )
    lead.status = LeadStatus.classifying
    db.commit()
    logger.info(
        "pipeline stage completed",
        extra={
            "lead_id": str(lead.id),
            "stage": "extract",
            "prompt_version": PROMPT_VERSION,
            "latency_ms": result.latency_ms,
            "success": True,
            "attempts": result.attempts,
        },
    )
    return result.output
