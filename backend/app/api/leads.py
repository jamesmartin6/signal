import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas import LeadDetailOut, LeadOut, PaginatedLeads, SkippedRowOut, UploadResponse
from app.db.models import Lead, LeadStatus
from app.db.session import get_db
from app.ingest import CSVValidationError, parse_leads_csv

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("/upload", response_model=UploadResponse)
async def upload_leads(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> UploadResponse:
    content = await file.read()
    try:
        parsed = parse_leads_csv(content)
    except CSVValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    leads = [
        Lead(
            raw_input={
                "name": row.name,
                "company": row.company,
                "bio_or_linkedin_url": row.bio_or_linkedin_url,
            },
            status=LeadStatus.pending,
        )
        for row in parsed.rows
    ]
    db.add_all(leads)
    db.commit()
    for lead in leads:
        db.refresh(lead)

    # Deferred import: the pipeline runner is wired up in Phase 3.
    try:
        from app.pipeline.runner import run_pipeline_background

        for lead in leads:
            background_tasks.add_task(run_pipeline_background, lead.id)
    except ImportError:
        pass

    return UploadResponse(
        created=len(leads),
        skipped=len(parsed.skipped),
        skipped_rows=[SkippedRowOut(row_number=s.row_number, reason=s.reason) for s in parsed.skipped],
        lead_ids=[lead.id for lead in leads],
    )


@router.get("", response_model=PaginatedLeads)
def list_leads(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> PaginatedLeads:
    total = db.scalar(select(func.count()).select_from(Lead)) or 0
    leads = db.scalars(select(Lead).order_by(Lead.seq.asc()).limit(limit).offset(offset)).all()
    return PaginatedLeads(
        total=total,
        limit=limit,
        offset=offset,
        items=[LeadOut.model_validate(lead) for lead in leads],
    )


@router.get("/{lead_id}", response_model=LeadDetailOut)
def get_lead(lead_id: uuid.UUID, db: Session = Depends(get_db)) -> LeadDetailOut:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadDetailOut.model_validate(lead)
