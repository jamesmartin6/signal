from sqlalchemy.orm import Session

from app.db.models import Lead, LeadStatus, PipelineStage, PipelineStageResult
from app.llm.client import LLMCallResult, LLMClient, LLMOutputInvalidError, generate_structured
from app.logging_config import get_pipeline_logger
from app.pipeline.errors import PipelineStageFailed
from app.pipeline.prompts import classify_v1, classify_v2
from app.pipeline.schemas import ClassificationResult, ExtractedProfile

logger = get_pipeline_logger()

DEFAULT_CLASSIFY_PROMPT_VERSION = classify_v2.PROMPT_VERSION

_PROMPT_MODULES = {
    classify_v1.PROMPT_VERSION: classify_v1,
    classify_v2.PROMPT_VERSION: classify_v2,
}


def classify_profile(client: LLMClient, profile: ExtractedProfile, prompt_version: str) -> LLMCallResult:
    """Pure LLM call: ExtractedProfile -> validated ClassificationResult. No
    DB side effects, so it's reusable from the eval harness. May raise
    LLMOutputInvalidError."""
    module = _PROMPT_MODULES[prompt_version]
    system, user = module.build_prompt(profile)
    return generate_structured(client, system=system, user=user, schema=ClassificationResult)


def run_classify(
    db: Session,
    lead: Lead,
    client: LLMClient,
    profile: ExtractedProfile,
    prompt_version: str = DEFAULT_CLASSIFY_PROMPT_VERSION,
) -> ClassificationResult:
    lead.status = LeadStatus.classifying
    db.commit()

    module = _PROMPT_MODULES[prompt_version]
    system, user = module.build_prompt(profile)

    try:
        result = generate_structured(client, system=system, user=user, schema=ClassificationResult)
    except LLMOutputInvalidError as exc:
        db.add(
            PipelineStageResult(
                lead_id=lead.id,
                stage=PipelineStage.classify,
                prompt_version=prompt_version,
                input={"system": system, "user": user},
                output={"error": str(exc), "raw_response": exc.raw_text},
                model=exc.model,
                latency_ms=exc.latency_ms,
                success=False,
            )
        )
        lead.status = LeadStatus.failed
        lead.error = f"classify: {exc}"
        db.commit()
        logger.error(
            "pipeline stage failed",
            extra={
                "lead_id": str(lead.id),
                "stage": "classify",
                "prompt_version": prompt_version,
                "latency_ms": exc.latency_ms,
                "success": False,
            },
        )
        raise PipelineStageFailed("classify", str(exc)) from exc

    db.add(
        PipelineStageResult(
            lead_id=lead.id,
            stage=PipelineStage.classify,
            prompt_version=prompt_version,
            input={"system": system, "user": user},
            output=result.output.model_dump(),
            model=result.model,
            latency_ms=result.latency_ms,
            success=True,
        )
    )
    lead.status = LeadStatus.enriching
    db.commit()
    logger.info(
        "pipeline stage completed",
        extra={
            "lead_id": str(lead.id),
            "stage": "classify",
            "prompt_version": prompt_version,
            "latency_ms": result.latency_ms,
            "success": True,
            "attempts": result.attempts,
        },
    )
    return result.output
