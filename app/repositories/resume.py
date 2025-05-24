from typing import List, Optional
from uuid import uuid4

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.resume import Resume, ResumeVersion
from app.repositories.base import BaseRepository
from app.schemas.resume import ResumeCreate, ResumeUpdate, ResumeVersionCreate


class ResumeRepository(BaseRepository[Resume, ResumeCreate, ResumeUpdate]):
    """Repository for Resume model"""

    def __init__(self, db: Session):
        super().__init__(db, Resume)

    def get_with_current_version(self, resume_id: str) -> Optional[Resume]:
        """
        Get a resume by ID with its latest version.

        Args:
            resume_id: Resume ID

        Returns:
            Resume with latest version if found, None otherwise
        """
        resume = self.get(resume_id)
        if resume:
            # Attach the latest version
            latest_version = (
                self.db.query(ResumeVersion)
                .filter(ResumeVersion.resume_id == resume_id)
                .order_by(desc(ResumeVersion.version_number))
                .first()
            )
            resume.current_version = latest_version
        return resume

    def get_with_all_versions(self, resume_id: str) -> Optional[Resume]:
        """
        Get a resume by ID with all its versions.

        Args:
            resume_id: Resume ID

        Returns:
            Resume with all versions if found, None otherwise
        """
        resume = self.get(resume_id)
        if resume:
            # Eager load all versions
            resume.versions = (
                self.db.query(ResumeVersion)
                .filter(ResumeVersion.resume_id == resume_id)
                .order_by(desc(ResumeVersion.version_number))
                .all()
            )
        return resume

    def get_by_user(
        self, user_id: str, skip: int = 0, limit: int = 100
    ) -> List[Resume]:
        """
        Get all resumes for a user.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of resumes for the user
        """
        return self.get_multi(skip=skip, limit=limit, user_id=user_id)

    def create_version(
        self, resume_id: str, version_in: ResumeVersionCreate
    ) -> ResumeVersion:
        """
        Create a new version of a resume.

        Args:
            resume_id: Resume ID
            version_in: Version data

        Returns:
            Created resume version
        """
        # Get the current highest version number
        latest_version = (
            self.db.query(ResumeVersion)
            .filter(ResumeVersion.resume_id == resume_id)
            .order_by(desc(ResumeVersion.version_number))
            .first()
        )

        version_number = 1
        if latest_version:
            version_number = latest_version.version_number + 1

        # Create the new version
        version_data = version_in.dict()
        version_data["resume_id"] = resume_id
        version_data["version_number"] = version_number
        if "id" not in version_data:
            version_data["id"] = str(uuid4())

        db_version = ResumeVersion(**version_data)
        self.db.add(db_version)

        # Update the resume's updated_at timestamp
        resume = self.get(resume_id)
        if resume:
            self.db.add(resume)  # This triggers the onupdate for updated_at

        self.db.commit()
        self.db.refresh(db_version)
        return db_version

    def get_latest_version(self, resume_id: str) -> Optional[ResumeVersion]:
        """
        Get the latest version of a resume.

        Args:
            resume_id: Resume ID

        Returns:
            Latest resume version if found, None otherwise
        """
        return (
            self.db.query(ResumeVersion)
            .filter(ResumeVersion.resume_id == resume_id)
            .order_by(desc(ResumeVersion.version_number))
            .first()
        )

    def get_version(self, resume_id: str, version_id: str) -> Optional[ResumeVersion]:
        """
        Get a specific version of a resume.

        Args:
            resume_id: Resume ID
            version_id: Version ID

        Returns:
            Resume version if found, None otherwise
        """
        return (
            self.db.query(ResumeVersion)
            .filter(
                ResumeVersion.resume_id == resume_id, ResumeVersion.id == version_id
            )
            .first()
        )

