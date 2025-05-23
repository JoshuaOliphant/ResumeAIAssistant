import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_optional_current_user
from app.db.session import get_db
from app.models.job import JobDescription
from app.models.user import User
from app.schemas.job import JobDescription as JobDescriptionSchema
from app.schemas.job import (
    JobDescriptionCreate,
    JobDescriptionUpdate,
)

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
        updated_at=datetime.now(),
    )

    db_job.is_from_url = False
    db.add(db_job)
    db.commit()
    db.refresh(db_job)

    return db_job


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

