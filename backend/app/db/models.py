import enum
import itertools
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Wall-clock timestamps aren't fine-grained enough to order rows created in
# the same batch (e.g. every lead from one CSV upload) — on this platform
# multiple inserts can land in the same microsecond and tie-break randomly
# on UUID. This process-local monotonic counter gives a stable "arrival
# order" independent of clock resolution. It must be reseeded from the DB's
# current max(seq) on every process start (see reset_lead_seq_counter) so a
# restart against a persisted database doesn't hand out colliding values.
_lead_seq_counter = itertools.count(1)


def reset_lead_seq_counter(start: int) -> None:
    global _lead_seq_counter
    _lead_seq_counter = itertools.count(start)


class Base(DeclarativeBase):
    pass


class LeadStatus(str, enum.Enum):
    pending = "pending"
    extracting = "extracting"
    classifying = "classifying"
    enriching = "enriching"
    routing = "routing"
    done = "done"
    failed = "failed"


class PipelineStage(str, enum.Enum):
    extract = "extract"
    classify = "classify"
    enrich = "enrich"
    route = "route"


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    seq: Mapped[int] = mapped_column(Integer, default=lambda: next(_lead_seq_counter), unique=True, nullable=False)
    raw_input: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, name="lead_status"), default=LeadStatus.pending, nullable=False
    )
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    stage_results: Mapped[list["PipelineStageResult"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan", order_by="PipelineStageResult.created_at"
    )


class PipelineStageResult(Base):
    __tablename__ = "pipeline_stage_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    stage: Mapped[PipelineStage] = mapped_column(Enum(PipelineStage, name="pipeline_stage"), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)
    input: Mapped[dict] = mapped_column(JSON, nullable=False)
    output: Mapped[dict] = mapped_column(JSON, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    success: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    lead: Mapped["Lead"] = relationship(back_populates="stage_results")


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)
    stage: Mapped[PipelineStage] = mapped_column(Enum(PipelineStage, name="eval_stage"), nullable=False)
    total_cases: Mapped[int] = mapped_column(Integer, nullable=False)
    passed_cases: Mapped[int] = mapped_column(Integer, nullable=False)
    pass_rate: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
