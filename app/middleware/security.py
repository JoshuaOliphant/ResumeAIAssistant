from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Simple API key validation middleware."""

    async def dispatch(self, request: Request, call_next):
        if settings.API_AUTH_KEY:
            key = request.headers.get("X-API-Key")
            if key != settings.API_AUTH_KEY:
                return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
        return await call_next(request)
