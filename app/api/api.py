from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from pathlib import Path
import sys
import logging

from app.api.endpoints import resumes, jobs, ats, customize, cover_letter, export, auth
from app.core.config import settings
from app.db.session import Base, engine
from app.core.nltk_init import initialize_nltk

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize NLTK data properly
logger.info("Initializing NLTK resources...")
initialize_nltk()
logger.info("NLTK initialization complete")

# Create database tables
try:
    # Create all tables defined in models
    Base.metadata.create_all(bind=engine)
    logger.info("Successfully initialized SQLite database")
except Exception as e:
    logger.error(f"Failed to initialize SQLite database: {str(e)}")
    sys.exit(1)

# Create directories for static files and templates if they don't exist
static_dir = Path("./static")
templates_dir = Path("./templates")

static_dir.mkdir(exist_ok=True)
templates_dir.mkdir(exist_ok=True)

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
api_router.include_router(cover_letter.router, prefix="/cover-letter", tags=["cover-letter"])
api_router.include_router(export.router, prefix="/export", tags=["export"])

# Add the API router to the FastAPI application
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root(request: Request):
    """Root endpoint for the resume customization application"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"message": "Resume Customization API is running"}
