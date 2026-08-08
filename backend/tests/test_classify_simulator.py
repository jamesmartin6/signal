"""Pins down the exact edge case that motivated classify_v2: a senior
individual contributor (title carries technical keywords, seniority is
senior/exec) should be "technical", not "decision_maker". v1 gets this
wrong because it checks seniority before role function; v2 fixes it."""

from app.llm.classify_simulator import classify_v1, classify_v2

PRINCIPAL_ENGINEER = {
    "title": "Principal Software Engineer",
    "company": "Gamma Systems",
    "seniority": "senior",
    "industry": "saas",
}

VP_ENGINEERING = {
    "title": "VP of Engineering",
    "company": "Acme Corp",
    "seniority": "exec",
    "industry": "fintech",
}


def test_v1_misclassifies_senior_ic_as_decision_maker():
    result = classify_v1(PRINCIPAL_ENGINEER)
    assert result["category"] == "decision_maker"  # the known v1 bug


def test_v2_correctly_classifies_senior_ic_as_technical():
    result = classify_v2(PRINCIPAL_ENGINEER)
    assert result["category"] == "technical"


def test_both_versions_agree_on_unambiguous_decision_maker():
    assert classify_v1(VP_ENGINEERING)["category"] == "decision_maker"
    assert classify_v2(VP_ENGINEERING)["category"] == "decision_maker"
