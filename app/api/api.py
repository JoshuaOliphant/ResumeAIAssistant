from fastapi import FastAPI, APIRouter, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import sys
import logfire
from fastapi.responses import JSONResponse

from app.api.endpoints import resumes, jobs, ats, customize, cover_letter, export, auth, requirements, enhance_customize, progress
from app.core.config import settings
from app.db.session import Base, engine
from app.core.nltk_init import initialize_nltk
from app.core.logging import configure_logging

# Configure Logfire - this is just the basic configuration
# The main.py file will handle the full instrumentation setup
configure_logging()

# Initialize NLTK data properly
logfire.info("Initializing NLTK resources...")
initialize_nltk()
logfire.info("NLTK initialization complete")

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
        traceback=str(sys.exc_info())
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
    description="API for customizing resumes and generating cover letters",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Set up templates
templates = Jinja2Templates(directory="templates")

# Set up CORS
if settings.BACKEND_CORS_ORIGINS:
    logfire.info(
        "Setting up CORS middleware",
        origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Create API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(ats.router, prefix="/ats", tags=["ats"])
api_router.include_router(customize.router, prefix="/customize", tags=["customize"])
api_router.include_router(enhance_customize.router, prefix="/enhance-customize", tags=["enhanced-customize"])
api_router.include_router(cover_letter.router, prefix="/cover-letter", tags=["cover-letter"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
api_router.include_router(progress.router, prefix="/progress", tags=["progress"])
api_router.include_router(requirements.router, prefix="/requirements", tags=["requirements"])

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
    logfire.info("Root endpoint accessed", client_ip=request.client.host if request.client else None)
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logfire.info("Health check endpoint accessed")
    return {"message": "Resume Customization API is running"}
