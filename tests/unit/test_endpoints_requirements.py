
def test_extract_requirements_from_content_invalid(client):
    resp = client.post("/api/v1/requirements/extract-from-content", json={})
    assert resp.status_code == 422
