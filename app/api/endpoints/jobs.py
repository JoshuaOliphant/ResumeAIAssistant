import time
import uuid
from typing import List
from datetime import datetime

import logfire
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.logging import log_function_call
from app.core.security import get_optional_current_user
from app.db.session import get_db
from app.models.job import JobDescription
from app.models.user import User
from app.schemas.job import JobDescription as JobDescriptionSchema
from app.schemas.job import (
    JobDescriptionCreate,
    JobDescriptionCreateFromUrl,
    JobDescriptionUpdate,
)
from app.services.job_scraper import scrape_job_description

router = APIRouter()


@router.post(
    "/", response_model=JobDescriptionSchema, status_code=status.HTTP_201_CREATED
)
def create_job_description(
    job: JobDescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user),
):
    """
    Create a new job description from text.

    - **title**: Title of the job
    - **company**: Optional company name
    - **description**: Job description text
    """
    db_job = JobDescription(
        id=str(uuid.uuid4()),
        title=job.title,
        company=job.company,
        description=job.description,
        user_id=current_user.id if current_user else None,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    db_job.is_from_url = False
    db.add(db_job)
    db.commit()
    db.refresh(db_job)

    return db_job


@router.post(
    "/from-url",
    response_model=JobDescriptionSchema,
    status_code=status.HTTP_201_CREATED,
)
@log_function_call
async def create_job_description_from_url(
    job: JobDescriptionCreateFromUrl,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user),
    request: Request = None,
):
    """
    Create a new job description from URL.

    - **url**: URL to fetch job description from
    - **title**: Optional job title (will attempt to extract from URL if not provided)
    - **company**: Optional company name (will attempt to extract from URL if not provided)
    """
    # Start timer for performance tracking
    start_time = time.time()

    # Create a request ID for tracking this specific request
    request_id = str(uuid.uuid4())

    # Create a span in OpenTelemetry for tracing
    with logfire.span("create_job_from_url_operation") as span:
        span.set_attribute("url", job.url)
        span.set_attribute("has_title", job.title is not None)
        span.set_attribute("has_company", job.company is not None)
        span.set_attribute("request_id", request_id)
        span.set_attribute("user_id", current_user.id if current_user else "anonymous")

        # Log operation start
        logfire.info(
            "Starting job import from URL",
            url=job.url,
            has_title=job.title is not None,
            has_company=job.company is not None,
            user_id=current_user.id if current_user else "anonymous",
            request_id=request_id,
        )

        try:
            # Use the service to scrape job description
            logfire.info(
                "Calling job scraper service", url=job.url, request_id=request_id
            )
            scraped_data = await scrape_job_description(job.url)

            # Log successful scraping
            logfire.info(
                "Scraping successful",
                url=job.url,
                title=scraped_data.get("title"),
                company=scraped_data.get("company"),
                description_length=len(scraped_data.get("description", "")),
                request_id=request_id,
            )

            title = job.title or scraped_data.get("title", "Untitled Job")
            company = job.company or scraped_data.get("company", None)
            description = scraped_data.get("description", "")

            if not description:
                logfire.warning(
                    "Empty description extracted from URL",
                    url=job.url,
                    request_id=request_id,
                )
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Could not extract job description from URL",
                )

            # Create database record
            job_id = str(uuid.uuid4())
            logfire.info(
                "Creating job record in database",
                job_id=job_id,
                title=title,
                company=company,
                description_length=len(description),
                url=job.url,
                request_id=request_id,
            )

            db_job = JobDescription(
                id=job_id,
                title=title,
                company=company,
                description=description,
                user_id=current_user.id if current_user else None,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            db_job.source_url = job.url
            db_job.is_from_url = True
            db.add(db_job)
            db.commit()
            db.refresh(db_job)

            # Calculate elapsed time
            elapsed_time = time.time() - start_time

            # Log success
            logfire.info(
                "Job import from URL completed successfully",
                job_id=job_id,
                url=job.url,
                title=title,
                company=company,
                description_length=len(description),
                duration_seconds=round(elapsed_time, 2),
                request_id=request_id,
            )

            return db_job

        except HTTPException as he:
            # Calculate elapsed time
            elapsed_time = time.time() - start_time

            # Log HTTP exception
            logfire.error(
                "HTTP exception during job import from URL",
                url=job.url,
                status_code=he.status_code,
                detail=he.detail,
                duration_seconds=round(elapsed_time, 2),
                request_id=request_id,
            )

            # Re-raise to return proper status code
            raise he

        except Exception as e:
            # Calculate elapsed time
            elapsed_time = time.time() - start_time

            # Log error details
            logfire.error(
                "Error during job import from URL",
                url=job.url,
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=round(elapsed_time, 2),
                traceback=logfire.format_exception(e),
                request_id=request_id,
            )

            # Return appropriate error response
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error scraping job description: {str(e)}",
            )


@router.get("/", response_model=List[JobDescriptionSchema])
def get_job_descriptions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user),
):
    """
    Get all job descriptions. If user is authenticated, only returns their job descriptions.
    """
    # If user is authenticated, filter by user_id
    if current_user:
        jobs = (
            db.query(JobDescription)
            .filter(JobDescription.user_id == current_user.id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    else:
        # For unauthenticated users, just show public jobs (those with null user_id)
        jobs = (
            db.query(JobDescription)
            .filter(JobDescription.user_id.is_(None))
            .offset(skip)
            .limit(limit)
            .all()
        )

    return jobs


@router.get("/{job_id}", response_model=JobDescriptionSchema)
def get_job_description(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user),
):
    """
    Get a specific job description by ID.
    """
    job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job description not found")

    # Check ownership if user is authenticated and the job belongs to a user
    if current_user and job.user_id and job.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this job description"
        )

    return job


@router.put("/{job_id}", response_model=JobDescriptionSchema)
def update_job_description(
    job_id: str,
    job_update: JobDescriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user),
):
    """
    Update a job description.

    - **title**: Optional new title
    - **company**: Optional new company name
    - **description**: Optional new description
    """
    db_job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job description not found")

    # Check ownership if user is authenticated
    if current_user and db_job.user_id and db_job.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to update this job description"
        )

    if job_update.title is not None:
        db_job.title = job_update.title
    if job_update.company is not None:
        db_job.company = job_update.company
    if job_update.description is not None:
        db_job.description = job_update.description

    db.commit()
    db.refresh(db_job)

    return db_job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job_description(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user),
):
    """
    Delete a job description.
    """
    db_job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job description not found")

    # Check ownership if user is authenticated
    if current_user and db_job.user_id and db_job.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this job description"
        )

    db.delete(db_job)
    db.commit()

    return None
