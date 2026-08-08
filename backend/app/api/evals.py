from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import EvalRunOut
from app.db.models import EvalRun
from app.db.session import get_db

router = APIRouter(prefix="/evals", tags=["evals"])


@router.get("", response_model=list[EvalRunOut])
def list_eval_runs(db: Session = Depends(get_db)) -> list[EvalRunOut]:
    runs = db.scalars(select(EvalRun).order_by(EvalRun.created_at.asc())).all()
    return [EvalRunOut.model_validate(run) for run in runs]
