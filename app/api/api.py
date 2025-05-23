import sys
from pathlib import Path

import logfire
from fastapi import APIRouter, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.endpoints import (
    auth,
    claude_code,  # Main Claude Code endpoints for resume customization
    export,
    jobs,
    requirements,
    resumes,
    websockets,  # Progress tracking endpoints
)
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import Base, engine

# Configure Logfire - this is just the basic configuration
# The main.py file will handle the full instrumentation setup
configure_logging()

# Create database tables
try:
    # Create all tables defined in models
    Base.metadata.create_all(bind=engine)
    logfire.info("Successfully initialized SQLite database")
except Exception as e:
    logfire.error(
        "Failed to initialize SQLite database",
        error=str(e),
        error_type=type(e).__name__,
        traceback=str(sys.exc_info()),
    )
    sys.exit(1)

# Create directories for static files and templates if they don't exist
static_dir = Path("./static")
templates_dir = Path("./templates")

static_dir.mkdir(exist_ok=True)
templates_dir.mkdir(exist_ok=True)

# Create FastAPI application
# The actual Logfire instrumentation will be done in main.py
app = FastAPI(
    title="Resume Customization API",
    description="API for customizing resumes and generating cover letters using Claude Code",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    # Increased timeout limits to support longer customization operations (30 minutes)
    default_response_class=JSONResponse,
    # Add more parameters for timeout handling
)

# Set up templates
templates = Jinja2Templates(directory="templates")

# Set up CORS
if settings.BACKEND_CORS_ORIGINS:
    print(f"Setting up CORS with origins: {settings.BACKEND_CORS_ORIGINS}")
    logfire.info(
        "Setting up CORS middleware",
        origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
else:
    print("WARNING: No CORS origins configured!")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Create API router
api_router = APIRouter()

# Include only the Claude Code workflow endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
api_router.include_router(
    requirements.router, prefix="/requirements", tags=["requirements"]
)

# Include WebSocket and Claude Code endpoints
api_router.include_router(
    websockets.router, prefix="/progress", tags=["progress"]
)  # Progress tracking endpoints
api_router.include_router(
    claude_code.router, tags=["claude-code"]
)  # Primary resume customization

# Add the API router to the FastAPI application
app.include_router(api_router, prefix=settings.API_V1_STR)


# Exception handler for global error logging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logfire.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.get("/")
async def root(request: Request):
    """Root endpoint for the resume customization application"""
    logfire.info(
        "Root endpoint accessed",
        client_ip=request.client.host if request.client else None,
    )
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logfire.info("Health check endpoint accessed")
    return {"message": "Resume Customization API is running"}
