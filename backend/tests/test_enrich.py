from app.pipeline.enrich import enrich_profile
from app.pipeline.schemas import ExtractedProfile


def test_enrich_passes_through_known_industry():
    profile = ExtractedProfile(title="VP of Engineering", company="Acme Corp", seniority="exec", industry="fintech")
    result = enrich_profile(profile)
    assert result.industry == "fintech"
    assert result.industry_source == "extracted"
    assert result.company_domain == "acme.com"
    assert result.company_size_bucket in {"startup", "smb", "mid_market", "enterprise"}


def test_enrich_fills_in_missing_industry_deterministically():
    profile = ExtractedProfile(title="Marketing Intern", company="Delta Co", seniority="junior", industry=None)
    result1 = enrich_profile(profile)
    result2 = enrich_profile(profile)
    assert result1.industry is not None
    assert result1.industry_source == "lookup_fallback"
    assert result1.industry == result2.industry  # deterministic, not random


def test_enrich_domain_strips_legal_suffixes():
    profile = ExtractedProfile(title="Engineer", company="Beta Inc", seniority="mid", industry="saas")
    result = enrich_profile(profile)
    assert result.company_domain == "beta.com"


def test_enrich_is_deterministic_across_calls():
    profile = ExtractedProfile(title="Engineer", company="CloudNine Systems", seniority="mid", industry=None)
    result1 = enrich_profile(profile)
    result2 = enrich_profile(profile)
    assert result1 == result2
