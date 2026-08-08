import pytest

from app.db.models import Lead, LeadStatus, PipelineStage
from app.pipeline.errors import PipelineStageFailed
from app.pipeline.classify import run_classify
from app.pipeline.schemas import ExtractedProfile
from tests.fakes import FakeLLMClient

VALID_JSON = '{"category": "decision_maker", "confidence": 0.9, "reasoning": "VP-level title."}'
INVALID_JSON = "I cannot classify this."
INVALID_SCHEMA_JSON = '{"category": "not_a_real_category", "confidence": 0.9, "reasoning": "x"}'


def make_lead(db_session) -> Lead:
    lead = Lead(
        raw_input={"name": "Jane Doe", "company": "Acme Corp", "bio_or_linkedin_url": "VP of Engineering."},
        status=LeadStatus.classifying,
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)
    return lead


def make_profile() -> ExtractedProfile:
    return ExtractedProfile(title="VP of Engineering", company="Acme Corp", seniority="exec", industry="fintech")


def test_valid_response_on_first_try(db_session):
    lead = make_lead(db_session)
    client = FakeLLMClient([VALID_JSON])

    result = run_classify(db_session, lead, client, make_profile(), prompt_version="classify_v1")

    assert result.category == "decision_maker"
    assert lead.status == LeadStatus.enriching
    assert len(client.calls) == 1

    results = [r for r in lead.stage_results if r.stage == PipelineStage.classify]
    assert len(results) == 1
    assert results[0].success is True
    assert results[0].prompt_version == "classify_v1"


def test_invalid_then_valid_on_retry(db_session):
    lead = make_lead(db_session)
    client = FakeLLMClient([INVALID_JSON, VALID_JSON])

    result = run_classify(db_session, lead, client, make_profile(), prompt_version="classify_v2")

    assert result.category == "decision_maker"
    assert len(client.calls) == 2
    assert lead.status == LeadStatus.enriching


def test_invalid_twice_marks_lead_failed(db_session):
    lead = make_lead(db_session)
    client = FakeLLMClient([INVALID_JSON, INVALID_SCHEMA_JSON])

    with pytest.raises(PipelineStageFailed):
        run_classify(db_session, lead, client, make_profile(), prompt_version="classify_v2")

    assert lead.status == LeadStatus.failed
    assert lead.error is not None


def test_unknown_prompt_version_raises_key_error(db_session):
    lead = make_lead(db_session)
    client = FakeLLMClient([VALID_JSON])

    with pytest.raises(KeyError):
        run_classify(db_session, lead, client, make_profile(), prompt_version="classify_v99")
