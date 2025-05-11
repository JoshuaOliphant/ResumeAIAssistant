import os
from datetime import datetime, timedelta
from typing import Any, Optional, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

# For backward compatibility
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 token setup
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False  # Don't auto-raise exceptions for unauthorized
)

# Token expiration settings
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> Optional[Any]:
    """
    Get the current authenticated user from token
    """
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        if email is None or user_id is None:
            return None
        
        # Import here to avoid circular imports
        from app.models.user import User
        
        user = db.query(User).filter(User.id == user_id).first()
        if user is None or not user.is_active:
            return None
        
        return user
    except JWTError:
        return None


def get_optional_current_user(
    current_user: Optional[Any] = Depends(get_current_user)
) -> Optional[Any]:
    """
    Get the current user if authenticated, None otherwise
    For endpoints that can work with or without authentication
    """
    return current_user


def get_current_user_required(
    current_user: Optional[Any] = Depends(get_current_user)
) -> Any:
    """
    Get the current user, raising an exception if not authenticated
    For endpoints that require authentication
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


def get_current_active_superuser(
    current_user: Any = Depends(get_current_user_required)
) -> Any:
    """
    Get the current user, raising an exception if not a superuser
    For endpoints that require superuser permissions
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


def get_optional_api_key(api_key: str = Depends(API_KEY_HEADER)) -> Optional[str]:
    """
    Optional API key validation for backward compatibility
    """
    return api_key
