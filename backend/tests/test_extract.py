import pytest

from app.db.models import Lead, LeadStatus, PipelineStage
from app.pipeline.errors import PipelineStageFailed
from app.pipeline.extract import run_extract
from tests.fakes import FakeLLMClient

VALID_JSON = '{"title": "VP of Engineering", "company": "Acme Corp", "seniority": "exec", "industry": "fintech"}'
INVALID_JSON = "sorry, I cannot help with that"
INVALID_SCHEMA_JSON = '{"title": "VP of Engineering", "seniority": "not_a_real_level"}'


def make_lead(db_session) -> Lead:
    lead = Lead(
        raw_input={
            "name": "Jane Doe",
            "company": "Acme Corp",
            "bio_or_linkedin_url": "VP of Engineering at Acme Corp, fintech.",
        },
        status=LeadStatus.pending,
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)
    return lead


def test_valid_response_on_first_try(db_session):
    lead = make_lead(db_session)
    client = FakeLLMClient([VALID_JSON])

    profile = run_extract(db_session, lead, client)

    assert profile.title == "VP of Engineering"
    assert profile.seniority == "exec"
    assert lead.status == LeadStatus.classifying
    assert len(client.calls) == 1

    results = lead.stage_results
    assert len(results) == 1
    assert results[0].stage == PipelineStage.extract
    assert results[0].success is True
    assert results[0].output["title"] == "VP of Engineering"


def test_invalid_then_valid_on_retry(db_session):
    lead = make_lead(db_session)
    client = FakeLLMClient([INVALID_JSON, VALID_JSON])

    profile = run_extract(db_session, lead, client)

    assert profile.company == "Acme Corp"
    assert lead.status == LeadStatus.classifying
    assert len(client.calls) == 2
    # The retry prompt should reference the failure so the model can self-correct.
    assert "previous response" in client.calls[1][1].lower()

    results = lead.stage_results
    assert len(results) == 1
    assert results[0].success is True


def test_invalid_twice_marks_lead_failed(db_session):
    lead = make_lead(db_session)
    client = FakeLLMClient([INVALID_JSON, INVALID_SCHEMA_JSON])

    with pytest.raises(PipelineStageFailed):
        run_extract(db_session, lead, client)

    assert lead.status == LeadStatus.failed
    assert lead.error is not None
    assert len(client.calls) == 2

    results = lead.stage_results
    assert len(results) == 1
    assert results[0].success is False
    assert results[0].output["raw_response"] == INVALID_SCHEMA_JSON
