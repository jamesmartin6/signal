from app.db.models import EvalRun
from app.evals.run_eval import load_cases, run_eval


def test_eval_cases_file_has_enough_cases_with_variety():
    cases = load_cases()
    assert len(cases) >= 20
    categories = {c["expected_category"] for c in cases}
    assert categories == {"decision_maker", "technical", "not_relevant"}


def test_classify_v2_beats_v1_on_the_eval_set(db_session):
    v1 = run_eval("classify_v1", verbose=False)
    v2 = run_eval("classify_v2", verbose=False)

    assert v1["total_cases"] == v2["total_cases"]
    # This is the whole point of v2: it must strictly improve on v1, not
    # just differ, because every case the two versions disagree on was
    # deliberately chosen to be a case v1 gets wrong and v2 gets right.
    assert v2["pass_rate"] > v1["pass_rate"]

    rows = db_session.query(EvalRun).order_by(EvalRun.created_at.asc()).all()
    assert len(rows) == 2
    assert {r.prompt_version for r in rows} == {"classify_v1", "classify_v2"}


def test_v1_specifically_fails_the_senior_ic_edge_cases(db_session):
    result = run_eval("classify_v1", verbose=False)
    failed_bios = {d["bio"] for d in result["details"] if not d["passed"]}
    assert any("Principal Software Engineer" in bio for bio in failed_bios)


def test_v2_fixes_the_senior_ic_edge_cases(db_session):
    result = run_eval("classify_v2", verbose=False)
    for detail in result["details"]:
        if "Principal Software Engineer" in detail["bio"] or "Staff Engineer" in detail["bio"]:
            assert detail["passed"], detail
