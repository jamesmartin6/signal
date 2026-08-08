from app.evals.run_eval import run_eval


def test_evals_endpoint_empty_by_default(client):
    resp = client.get("/evals")
    assert resp.status_code == 200
    assert resp.json() == []


def test_evals_endpoint_returns_runs_in_order(client):
    run_eval("classify_v1", verbose=False)
    run_eval("classify_v2", verbose=False)

    resp = client.get("/evals")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["prompt_version"] == "classify_v1"
    assert body[1]["prompt_version"] == "classify_v2"
    assert body[1]["pass_rate"] > body[0]["pass_rate"]
