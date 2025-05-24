
def test_create_job(client):
    payload = {"title": "Engineer", "company": "Acme", "description": "Build"}
    response = client.post("/api/v1/jobs/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Engineer"
    assert data["description"] == "Build"
