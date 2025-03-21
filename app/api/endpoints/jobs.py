import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.job import JobDescription
from app.schemas.job import (
    JobDescriptionCreate,
    JobDescriptionCreateFromUrl,
    JobDescription as JobDescriptionSchema,
    JobDescriptionUpdate
)
from app.services.job_scraper import scrape_job_description

router = APIRouter()


@router.post("/", response_model=JobDescriptionSchema, status_code=status.HTTP_201_CREATED)
def create_job_description(
    job: JobDescriptionCreate,
    db: Session = Depends(get_db)
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
        is_from_url=False
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    return db_job


@router.post("/from-url", response_model=JobDescriptionSchema, status_code=status.HTTP_201_CREATED)
async def create_job_description_from_url(
    job: JobDescriptionCreateFromUrl,
    db: Session = Depends(get_db)
):
    """
    Create a new job description from URL.
    
    - **url**: URL to fetch job description from
    - **title**: Optional job title (will attempt to extract from URL if not provided)
    - **company**: Optional company name (will attempt to extract from URL if not provided)
    """
    try:
        # Use the service to scrape job description
        scraped_data = await scrape_job_description(job.url)
        
        title = job.title or scraped_data.get("title", "Untitled Job")
        company = job.company or scraped_data.get("company", None)
        description = scraped_data.get("description", "")
        
        if not description:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract job description from URL"
            )
        
        db_job = JobDescription(
            id=str(uuid.uuid4()),
            title=title,
            company=company,
            description=description,
            source_url=job.url,
            is_from_url=True
        )
        db.add(db_job)
        db.commit()
        db.refresh(db_job)
        
        return db_job
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error scraping job description: {str(e)}"
        )


@router.get("/", response_model=List[JobDescriptionSchema])
def get_job_descriptions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all job descriptions.
    """
    jobs = db.query(JobDescription).offset(skip).limit(limit).all()
    return jobs


@router.get("/{job_id}", response_model=JobDescriptionSchema)
def get_job_description(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific job description by ID.
    """
    job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job description not found")
    return job


@router.put("/{job_id}", response_model=JobDescriptionSchema)
def update_job_description(
    job_id: str,
    job_update: JobDescriptionUpdate,
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
):
    """
    Delete a job description.
    """
    db_job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not db_job:
        raise HTTPException(status_code=404, detail="Job description not found")
    
    db.delete(db_job)
    db.commit()
    
    return None
