import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_optional_current_user
from app.db.session import get_db
from app.models.resume import Resume, ResumeVersion
from app.models.user import User
from app.schemas.resume import Resume as ResumeSchema
from app.schemas.resume import (
    ResumeCreate,
    ResumeDetail,
    ResumeDiffResponse,
    ResumeUpdate,
    ResumeVersionCreate,
    HtmlDiffResponse,
)
from app.schemas.resume import ResumeVersion as ResumeVersionSchema
from app.services.diff_service import (
    generate_resume_diff,
    get_diff_statistics,
    DiffGenerator,
)

router = APIRouter()


@router.post("/", response_model=ResumeSchema, status_code=status.HTTP_201_CREATED)
def create_resume(
    resume: ResumeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user),
):
    """
    Create a new resume.

    - **title**: Title of the resume
    - **content**: Content of the resume in Markdown format
    """
    # Create the resume object with timestamps
    from datetime import datetime
    from sqlalchemy.sql import func
    
    now = datetime.utcnow()
    
    db_resume = Resume(
        id=str(uuid.uuid4()),
        title=resume.title,
        user_id=current_user.id if current_user else None,
        created_at=now,
        updated_at=now,
    )
    db.add(db_resume)
    db.flush()

    # Create the initial version with timestamp
    db_version = ResumeVersion(
        id=str(uuid.uuid4()),
        resume_id=db_resume.id,
        content=resume.content,
        version_number=1,
        is_customized=0,
        created_at=now,
    )
    db.add(db_version)
    db.commit()
    db.refresh(db_resume)
    db.refresh(db_version)

    # Return the resume with its current version
    # Add current_version attribute for response
    setattr(db_resume, "current_version", db_version)

    return db_resume


@router.get("/", response_model=List[ResumeSchema])
def get_resumes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user),
):
    """
    Get all resumes. If user is authenticated, only returns their resumes.
    """
    # If user is authenticated, filter by user_id
    if current_user:
        resumes = (
            db.query(Resume)
            .filter(Resume.user_id == current_user.id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    else:
        # For unauthenticated users, just show public resumes (those with null user_id)
        resumes = (
            db.query(Resume)
            .filter(Resume.user_id.is_(None))
            .offset(skip)
            .limit(limit)
            .all()
        )

    # For each resume, get its latest version
    for resume in resumes:
        # Ensure timestamps are set
        from datetime import datetime
        
        if resume.created_at is None:
            resume.created_at = datetime.utcnow()
        if resume.updated_at is None:
            resume.updated_at = datetime.utcnow()
        
        latest_version = (
            db.query(ResumeVersion)
            .filter(ResumeVersion.resume_id == resume.id)
            .order_by(ResumeVersion.version_number.desc())
            .first()
        )
        
        # Ensure version timestamp is set
        if latest_version and latest_version.created_at is None:
            latest_version.created_at = datetime.utcnow()

        # Set the current_version attribute
        setattr(resume, "current_version", latest_version)

    return resumes


@router.get("/{resume_id}", response_model=ResumeDetail)
def get_resume(
    resume_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user),
):
    """
    Get a specific resume by ID with all its versions.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Check ownership if user is authenticated and the resume belongs to a user
    if current_user and resume.user_id and resume.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this resume"
        )
        
    # Ensure timestamps are set
    from datetime import datetime
    
    if resume.created_at is None:
        resume.created_at = datetime.utcnow()
        db.commit()
    if resume.updated_at is None:
        resume.updated_at = datetime.utcnow()
        db.commit()

    # Get all versions
    versions = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.resume_id == resume_id)
        .order_by(ResumeVersion.version_number.desc())
        .all()
    )
    
    # Set created_at for all versions if needed
    for version in versions:
        if version.created_at is None:
            version.created_at = datetime.utcnow()
            db.commit()

    # Set the versions attribute
    setattr(resume, "versions", versions)

    # Set the current_version attribute (latest version)
    if versions:
        setattr(resume, "current_version", versions[0])
    else:
        setattr(resume, "current_version", None)

    return resume


@router.put("/{resume_id}", response_model=ResumeSchema)
def update_resume(
    resume_id: str,
    resume_update: ResumeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user),
):
    """
    Update a resume.

    - **title**: Optional new title for the resume
    - **content**: Optional new content for the resume
    """
    db_resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not db_resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Check ownership if user is authenticated
    if current_user and db_resume.user_id and db_resume.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to update this resume"
        )

    # Update the title if provided
    if resume_update.title:
        db_resume.title = resume_update.title

    # Create a new version if content is provided
    if resume_update.content:
        # Get the latest version number
        latest_version = (
            db.query(ResumeVersion)
            .filter(ResumeVersion.resume_id == resume_id)
            .order_by(ResumeVersion.version_number.desc())
            .first()
        )

        new_version_number = latest_version.version_number + 1 if latest_version else 1

        # Create new version
        db_version = ResumeVersion(
            id=str(uuid.uuid4()),
            resume_id=resume_id,
            content=resume_update.content,
            version_number=new_version_number,
            is_customized=0,
        )
        db.add(db_version)

    db.commit()
    db.refresh(db_resume)

    # Get the latest version
    latest_version = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.resume_id == resume_id)
        .order_by(ResumeVersion.version_number.desc())
        .first()
    )

    # Set the current_version attribute
    setattr(db_resume, "current_version", latest_version)

    return db_resume


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(
    resume_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user),
):
    """
    Delete a resume.
    """
    db_resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not db_resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Check ownership if user is authenticated
    if current_user and db_resume.user_id and db_resume.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this resume"
        )

    db.delete(db_resume)
    db.commit()

    return None


@router.post("/{resume_id}/versions", response_model=ResumeVersionSchema)
def create_resume_version(
    resume_id: str,
    version: ResumeVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user),
):
    """
    Create a new version for a resume.

    - **content**: Content of the resume version
    - **is_customized**: Whether this version is customized
    - **job_description_id**: Optional job description ID if this is a customized version
    """
    db_resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not db_resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Check ownership if user is authenticated and the resume belongs to a user
    if current_user and db_resume.user_id and db_resume.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to create versions for this resume"
        )

    # Get the latest version number
    latest_version = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.resume_id == resume_id)
        .order_by(ResumeVersion.version_number.desc())
        .first()
    )

    new_version_number = latest_version.version_number + 1 if latest_version else 1

    # Create new version
    db_version = ResumeVersion(
        id=str(uuid.uuid4()),
        resume_id=resume_id,
        content=version.content,
        version_number=new_version_number,
        is_customized=1 if version.is_customized else 0,
        job_description_id=version.job_description_id,
    )
    db.add(db_version)
    db.commit()
    db.refresh(db_version)

    return db_version


@router.get("/{resume_id}/versions", response_model=List[ResumeVersionSchema])
def get_resume_versions(
    resume_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user),
):
    """
    Get all versions of a resume.
    """
    db_resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not db_resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Check ownership if user is authenticated and the resume belongs to a user
    if current_user and db_resume.user_id and db_resume.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access versions of this resume"
        )

    versions = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.resume_id == resume_id)
        .order_by(ResumeVersion.version_number.desc())
        .all()
    )

    return versions


@router.get("/{resume_id}/versions/{version_id}", response_model=ResumeVersionSchema)
def get_resume_version(
    resume_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user),
):
    """
    Get a specific version of a resume.
    """
    # First check if the resume exists and check ownership
    db_resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not db_resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Check ownership if user is authenticated and the resume belongs to a user
    if current_user and db_resume.user_id and db_resume.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access versions of this resume"
        )

    db_version = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.resume_id == resume_id, ResumeVersion.id == version_id)
        .first()
    )

    if not db_version:
        raise HTTPException(status_code=404, detail="Resume version not found")

    return db_version


@router.get(
    "/{resume_id}/versions/{version_id}/diff", response_model=ResumeDiffResponse
)
def get_resume_version_diff(
    resume_id: str,
    version_id: str,
    original_version_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user),
):
    """
    Get a diff view comparing a customized resume version with its original version.

    - **resume_id**: ID of the resume
    - **version_id**: ID of the customized version to compare
    - **original_version_id**: Optional ID of the original version to compare against.
                             If not provided, will use the previous version.
    """
    # Verify the resume exists
    db_resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not db_resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Check ownership if user is authenticated and the resume belongs to a user
    if current_user and db_resume.user_id and db_resume.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this resume's diff view"
        )

    # Get the customized version
    customized_version = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.resume_id == resume_id, ResumeVersion.id == version_id)
        .first()
    )

    if not customized_version:
        raise HTTPException(status_code=404, detail="Resume version not found")

    # If this is not a customized version, return an error
    if not customized_version.is_customized:
        raise HTTPException(
            status_code=400,
            detail="Diff view is only available for customized resume versions",
        )

    # Get the original version
    if original_version_id:
        # Use the specified original version
        original_version = (
            db.query(ResumeVersion)
            .filter(
                ResumeVersion.resume_id == resume_id,
                ResumeVersion.id == original_version_id,
            )
            .first()
        )

        if not original_version:
            raise HTTPException(
                status_code=404, detail="Original resume version not found"
            )
    else:
        # Find the most recent non-customized version before this one
        original_version = (
            db.query(ResumeVersion)
            .filter(
                ResumeVersion.resume_id == resume_id,
                ResumeVersion.version_number < customized_version.version_number,
                ResumeVersion.is_customized == 0,
            )
            .order_by(ResumeVersion.version_number.desc())
            .first()
        )

        if not original_version:
            # If no previous non-customized version found, try to find any previous version
            original_version = (
                db.query(ResumeVersion)
                .filter(
                    ResumeVersion.resume_id == resume_id,
                    ResumeVersion.version_number < customized_version.version_number,
                )
                .order_by(ResumeVersion.version_number.desc())
                .first()
            )

            if not original_version:
                raise HTTPException(
                    status_code=404,
                    detail="No previous version found to compare against",
                )

    # Generate the diff content
    diff_content = generate_resume_diff(
        original_version.content, customized_version.content
    )

    # Get diff statistics
    diff_stats = get_diff_statistics(
        original_version.content, customized_version.content
    )

    # Get section-level analysis
    from app.services.diff_service import analyze_section_changes

    section_analysis = analyze_section_changes(
        original_version.content, customized_version.content
    )

    # Return the diff response
    return ResumeDiffResponse(
        id=resume_id,
        title=db_resume.title,
        original_content=original_version.content,
        customized_content=customized_version.content,
        diff_content=diff_content,
        diff_statistics=diff_stats,
        section_analysis=section_analysis,
        is_diff_view=True,
    )


@router.get("/{resume_id}/diff", response_model=HtmlDiffResponse)
def compare_resume_versions(
    resume_id: str,
    source_version_id: str,
    target_version_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user),
):
    """Return an HTML diff between two resume versions."""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if current_user and resume.user_id and resume.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this resume")

    source_version = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.resume_id == resume_id, ResumeVersion.id == source_version_id)
        .first()
    )
    target_version = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.resume_id == resume_id, ResumeVersion.id == target_version_id)
        .first()
    )

    if not source_version or not target_version:
        raise HTTPException(status_code=404, detail="Resume version not found")

    diff_html = DiffGenerator().html_diff_view(
        source_version.content, target_version.content
    )
    return HtmlDiffResponse(diff_html=diff_html)
