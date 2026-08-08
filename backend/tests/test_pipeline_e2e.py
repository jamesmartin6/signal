"""Integration test: the full extract -> classify -> enrich -> route chain,
run for real (against the simulated LLM client, since no ANTHROPIC_API_KEY
is set in the test environment) rather than with mocks. This is the
automated version of the Phase 3 definition of done."""

from app.db.models import Lead, LeadStatus, PipelineStage
from app.pipeline.runner import run_pipeline

SAMPLE_LEADS = [
    {
        "name": "Jane Doe",
        "company": "Acme Corp",
        "bio_or_linkedin_url": "Jane Doe, Senior Vice President of Engineering at Acme Corp, fintech infrastructure.",
    },
    {
        "name": "John Smith",
        "company": "Beta Inc",
        "bio_or_linkedin_url": "John Smith is a Software Engineer at Beta Inc working on backend systems.",
    },
    {
        "name": "Maria Garcia",
        "company": "Delta Co",
        "bio_or_linkedin_url": "Maria Garcia, Marketing Intern at Delta Co, focused on campaigns.",
    },
]


def test_full_pipeline_run_on_three_leads(db_session):
    leads = []
    for raw in SAMPLE_LEADS:
        lead = Lead(raw_input=raw, status=LeadStatus.pending)
        db_session.add(lead)
        leads.append(lead)
    db_session.commit()
    for lead in leads:
        db_session.refresh(lead)

    for lead in leads:
        run_pipeline(db_session, lead.id)

    for lead in leads:
        db_session.refresh(lead)
        assert lead.status == LeadStatus.done, lead.error
        stages = [r.stage for r in lead.stage_results]
        assert stages == [
            PipelineStage.extract,
            PipelineStage.classify,
            PipelineStage.enrich,
            PipelineStage.route,
        ]
        assert all(r.success for r in lead.stage_results)

    # Spot-check the actual routing outcomes make sense for these bios.
    exec_lead, engineer_lead, intern_lead = leads
    exec_route = exec_lead.stage_results[-1].output
    engineer_route = engineer_lead.stage_results[-1].output
    intern_route = intern_lead.stage_results[-1].output

    assert exec_route["queue"] in {"decision_maker_queue", "needs_review"}
    assert engineer_route["queue"] in {"technical_queue", "needs_review"}
    assert intern_route["queue"] in {"discard", "needs_review"}


def test_unknown_lead_id_is_a_noop(db_session):
    import uuid

    run_pipeline(db_session, uuid.uuid4())  # should not raise
