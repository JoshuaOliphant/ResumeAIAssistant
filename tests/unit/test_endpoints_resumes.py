
def test_create_resume(client):
    payload = {"title": "Resume", "content": "Content"}
    response = client.post("/api/v1/resumes/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Resume"
    assert data["current_version"]["content"] == "Content"
