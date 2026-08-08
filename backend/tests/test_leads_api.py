import io

VALID_CSV = (
    b"name,company,bio_or_linkedin_url\n"
    b"Jane Doe,Acme Corp,Senior VP of Engineering at Acme Corp.\n"
    b"John Smith,Beta Inc,Backend engineer at Beta Inc.\n"
)


def _upload(client, content=VALID_CSV, filename="leads.csv"):
    return client.post(
        "/leads/upload",
        files={"file": (filename, io.BytesIO(content), "text/csv")},
    )


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_upload_creates_leads(client):
    resp = _upload(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 2
    assert body["skipped"] == 0
    assert len(body["lead_ids"]) == 2


def test_upload_bad_csv_returns_400(client):
    resp = _upload(client, content=b"name,company\nJane,Acme\n")
    assert resp.status_code == 400
    assert "missing required column" in resp.json()["detail"]


def test_upload_reports_skipped_rows(client):
    content = (
        b"name,company,bio_or_linkedin_url\n"
        b",Acme,Some bio\n"
        b"Jane Doe,Acme,A real bio\n"
    )
    resp = _upload(client, content=content)
    body = resp.json()
    assert body["created"] == 1
    assert body["skipped"] == 1
    assert body["skipped_rows"][0]["row_number"] == 2


def test_list_leads_after_upload(client):
    # TestClient runs BackgroundTasks to completion before the upload
    # response returns, so by the time we list leads the pipeline has
    # already run (against the simulated LLM client, no API key in tests).
    _upload(client)
    resp = client.get("/leads")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert body["items"][0]["status"] == "done"
    assert body["items"][0]["raw_input"]["name"] == "Jane Doe"


def test_list_leads_pagination(client):
    _upload(client)
    resp = client.get("/leads", params={"limit": 1, "offset": 1})
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 1
    assert body["items"][0]["raw_input"]["name"] == "John Smith"


def test_get_lead_detail(client):
    upload_resp = _upload(client)
    lead_id = upload_resp.json()["lead_ids"][0]
    resp = client.get(f"/leads/{lead_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == lead_id
    assert body["status"] == "done"
    assert [r["stage"] for r in body["stage_results"]] == ["extract", "classify", "enrich", "route"]


def test_get_lead_not_found(client):
    resp = client.get("/leads/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
