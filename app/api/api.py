from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import resumes, jobs, ats, customize, cover_letter, export
from app.core.config import settings
from app.db.session import Base, engine

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Resume Customization API",
    description="API for customizing resumes and generating cover letters",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Set up CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
async def root():
    """Root endpoint for health checks"""
    return {"message": "Resume Customization API is running"}
