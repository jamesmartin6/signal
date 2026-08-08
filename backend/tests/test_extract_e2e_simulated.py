"""End-to-end extraction check against the real (simulated) LLM client — no
mocking. This is the automated version of the build plan's Phase 2
definition of done: "given 5 sample bios, extraction produces valid
ExtractedProfile JSON for at least 4/5 without retry."
"""

from app.db.models import Lead, LeadStatus
from app.llm.simulator import SimulatedLLMClient
from app.pipeline.extract import run_extract

SAMPLE_BIOS = [
    (
        "Jane Doe, Senior Vice President of Engineering at Acme Corp, leading a "
        "40-person team building fintech infrastructure.",
        "exec",
        "fintech",
    ),
    (
        "John Smith is a Software Engineer at Beta Inc working on backend systems "
        "for their e-commerce platform.",
        "mid",
        "e-commerce",
    ),
    ("Maria Garcia, Marketing Intern at Delta Co, focused on social media campaigns.", "junior", None),
    (
        "Dr. Alex Chen, Chief Technology Officer and co-founder at NovaHealth, a "
        "healthcare technology startup.",
        "exec",
        "healthcare",
    ),
    (
        "Sam Lee is a Senior DevOps Engineer at CloudNine Systems, specializing in "
        "cybersecurity for cloud infrastructure.",
        "senior",
        "cybersecurity",
    ),
]


def test_five_sample_bios_extract_correctly_without_retry(db_session):
    client = SimulatedLLMClient()
    first_attempt_successes = 0

    for bio, expected_seniority, expected_industry in SAMPLE_BIOS:
        lead = Lead(raw_input={"name": "", "company": "", "bio_or_linkedin_url": bio}, status=LeadStatus.pending)
        db_session.add(lead)
        db_session.commit()
        db_session.refresh(lead)

        profile = run_extract(db_session, lead, client)

        assert lead.status == LeadStatus.classifying
        if lead.stage_results[-1].success:
            first_attempt_successes += 1

        assert profile.seniority == expected_seniority
        assert profile.industry == expected_industry

    assert first_attempt_successes >= 4
