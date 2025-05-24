
def test_export_markdown(client):
    create = client.post("/api/v1/resumes/", json={"title": "R", "content": "X"})
    resume_id = create.json()["id"]
    resp = client.get(f"/api/v1/export/resume/{resume_id}/markdown")
    assert resp.status_code == 200
    assert resp.text == "X"
