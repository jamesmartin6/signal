from app.llm.simulator import extract_title_company, infer_industry, infer_seniority


def test_extract_title_company_comma_separated():
    bio = (
        "Jane Doe, Senior Vice President of Engineering at Acme Corp, "
        "leading a 40-person team building fintech infrastructure."
    )
    title, company = extract_title_company(bio)
    assert title == "Senior Vice President of Engineering"
    assert company == "Acme Corp"


def test_extract_title_company_is_a_pattern():
    bio = "John Smith is a Software Engineer at Beta Inc working on backend systems."
    title, company = extract_title_company(bio)
    assert title == "Software Engineer"
    assert company == "Beta Inc"


def test_extract_title_company_em_dash():
    bio = "Maria Garcia — Marketing Intern at Delta Co, focused on social campaigns."
    title, company = extract_title_company(bio)
    assert title == "Marketing Intern"
    assert company == "Delta Co"


def test_extract_title_company_no_match_falls_back_to_unknown():
    bio = "A person who does things sometimes."
    title, company = extract_title_company(bio)
    assert title == "Unknown"
    assert company == "Unknown"


def test_infer_seniority_exec_keywords():
    assert infer_seniority("Chief Technology Officer", "") == "exec"
    assert infer_seniority("VP of Sales", "") == "exec"
    assert infer_seniority("Founder", "") == "exec"


def test_infer_seniority_senior_keywords():
    assert infer_seniority("Senior Software Engineer", "") == "senior"
    assert infer_seniority("Principal Architect", "") == "senior"


def test_infer_seniority_junior_keywords():
    assert infer_seniority("Marketing Intern", "") == "junior"
    assert infer_seniority("Junior Analyst", "") == "junior"


def test_infer_seniority_defaults_to_mid():
    assert infer_seniority("Software Engineer", "") == "mid"


def test_infer_industry_matches_keyword():
    assert infer_industry("Works in fintech infrastructure.") == "fintech"
    assert infer_industry("A healthcare technology startup.") == "healthcare"


def test_infer_industry_none_when_no_match():
    assert infer_industry("Does some general business stuff.") is None
