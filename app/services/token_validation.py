from jose import JWTError, jwt

from app.core.config import settings


def validate_token(token: str, customization_id: str) -> bool:
    """Return True if the JWT is valid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return bool(payload.get("user_id"))
    except JWTError:
        return False
