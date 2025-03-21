from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from pathlib import Path
import sys

from app.api.endpoints import resumes, jobs, ats, customize, cover_letter, export
from app.core.config import settings
from app.db.session import Base, engine
from app.core.nltk_init import initialize_nltk

# Initialize NLTK data properly
print("Initializing NLTK resources...", file=sys.stderr)
initialize_nltk()
print("NLTK initialization complete", file=sys.stderr)

# Create database tables
Base.metadata.create_all(bind=engine)

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
