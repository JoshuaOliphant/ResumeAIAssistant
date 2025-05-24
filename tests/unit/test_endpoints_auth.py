
def test_login_invalid_credentials(client):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "nouser", "password": "wrong"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 401
