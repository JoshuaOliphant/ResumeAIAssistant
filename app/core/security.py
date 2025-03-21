import os
from datetime import datetime, timedelta
from typing import Any, Optional, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from jose import JWTError, jwt

from app.core.config import settings

# For future use when authentication is implemented
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_optional_api_key(api_key: str = Depends(API_KEY_HEADER)) -> Optional[str]:
    """
    Optional API key validation for future use
    """
    return api_key
