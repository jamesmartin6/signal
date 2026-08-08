"""Optional integration test that hits the real Anthropic API.

Skipped by default (and therefore in CI) unless both RUN_REAL_LLM_TESTS=1
and ANTHROPIC_API_KEY are set, per the build plan's testing requirements:
unit tests use a mocked/simulated client; this is the one real-API check,
opt-in only, so CI stays fast, deterministic, and free.
"""

import os

import pytest

from app.db.models import Lead, LeadStatus
from app.llm.client import AnthropicLLMClient
from app.pipeline.extract import run_extract

pytestmark = pytest.mark.skipif(
    not (os.environ.get("RUN_REAL_LLM_TESTS") and os.environ.get("ANTHROPIC_API_KEY")),
    reason="set RUN_REAL_LLM_TESTS=1 and ANTHROPIC_API_KEY to run real-API integration tests",
)


def test_real_extraction_on_a_couple_of_bios(db_session):
    client = AnthropicLLMClient(os.environ["ANTHROPIC_API_KEY"], "claude-sonnet-4-5")

    bios = [
        "Priya Patel, Chief Marketing Officer at Northwind Retail, a national apparel chain.",
        "Tom Becker is a Data Engineer at Lumen Analytics building ETL pipelines.",
    ]
    for bio in bios:
        lead = Lead(raw_input={"name": "", "company": "", "bio_or_linkedin_url": bio}, status=LeadStatus.pending)
        db_session.add(lead)
        db_session.commit()
        db_session.refresh(lead)

        profile = run_extract(db_session, lead, client)

        assert profile.title
        assert profile.company
        assert profile.seniority in {"junior", "mid", "senior", "exec"}
        assert lead.status == LeadStatus.classifying
