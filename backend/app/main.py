from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import func, select

from app.api.leads import router as leads_router
from app.config import get_settings
from app.db.models import Base, Lead, reset_lead_seq_counter
from app.db.session import SessionLocal, engine
from app.logging_config import configure_logging

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    # Zero-config convenience: for the default local SQLite database, make
    # sure tables exist without requiring `alembic upgrade head` first.
    # Postgres deployments (docker-compose) run migrations explicitly instead
    # so alembic stays the single source of truth there.
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)

    # The in-process lead-ordering counter always starts at 1; reseed it from
    # whatever's already persisted so a restart never hands out a seq value
    # that collides with an existing row.
    with SessionLocal() as session:
        max_seq = session.scalar(select(func.max(Lead.seq))) or 0
        reset_lead_seq_counter(max_seq + 1)

    yield


app = FastAPI(title="Signal", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(leads_router)

try:
    from app.api.evals import router as evals_router

    app.include_router(evals_router)
except ImportError:
    pass
