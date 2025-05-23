from datetime import timedelta, datetime

from jose import jwt

from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings


def test_verify_password():
    plain = "secret-password"
    hashed = get_password_hash(plain)
    assert verify_password(plain, hashed)
    assert not verify_password("wrong", hashed)


def test_create_access_token_encodes_payload_and_expiration():
    data = {"sub": "test@example.com", "user_id": "user123"}
    delta = timedelta(minutes=1)
    time_before = datetime.utcnow()
    token = create_access_token(data, expires_delta=delta)

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

    assert payload["sub"] == data["sub"]
    assert payload["user_id"] == data["user_id"]

    exp = datetime.utcfromtimestamp(payload["exp"])
    expected_exp = time_before + delta
    assert abs((exp - expected_exp).total_seconds()) < 2


