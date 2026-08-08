import uuid

from sqlalchemy.orm import Session

from app.db.models import Lead, LeadStatus
from app.db.session import SessionLocal
from app.llm.client import get_llm_client
from app.logging_config import get_pipeline_logger
from app.pipeline.classify import DEFAULT_CLASSIFY_PROMPT_VERSION, run_classify
from app.pipeline.enrich import run_enrich
from app.pipeline.errors import PipelineStageFailed
from app.pipeline.extract import run_extract
from app.pipeline.route import run_route

logger = get_pipeline_logger()


def run_pipeline(db: Session, lead_id: uuid.UUID, classify_prompt_version: str = DEFAULT_CLASSIFY_PROMPT_VERSION) -> None:
    """Runs extract -> classify -> enrich -> route for one lead, in order.

    Each stage function already records its own pipeline_stage_results row
    and advances lead.status. If a stage raises PipelineStageFailed, it has
    already marked the lead `failed` with a reason — we just stop here
    without crashing the rest of the batch. Any other, unexpected exception
    is also caught and recorded so one bad lead can never take down a batch
    upload of many.
    """
    lead = db.get(Lead, lead_id)
    if lead is None:
        logger.error("pipeline run requested for unknown lead", extra={"lead_id": str(lead_id)})
        return

    client = get_llm_client()

    try:
        profile = run_extract(db, lead, client)
        classification = run_classify(db, lead, client, profile, prompt_version=classify_prompt_version)
        run_enrich(db, lead, profile)
        run_route(db, lead, classification)
    except PipelineStageFailed as exc:
        logger.error(
            "pipeline run stopped: stage failed",
            extra={"lead_id": str(lead_id), "stage": exc.stage},
        )
    except Exception as exc:  # noqa: BLE001 - a single bad lead must never take down the batch
        db.rollback()
        lead = db.get(Lead, lead_id)
        if lead is not None:
            lead.status = LeadStatus.failed
            lead.error = f"unexpected pipeline error: {exc}"
            db.commit()
        logger.exception("pipeline run crashed unexpectedly", extra={"lead_id": str(lead_id)})


def run_pipeline_background(lead_id: uuid.UUID) -> None:
    """Entry point for FastAPI BackgroundTasks: owns its own DB session
    since it runs outside the request's session lifecycle."""
    db = SessionLocal()
    try:
        run_pipeline(db, lead_id)
    finally:
        db.close()
