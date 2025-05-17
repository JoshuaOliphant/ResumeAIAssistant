from typing import List, Optional
from sqlalchemy.orm import Session

from app.repositories.base import BaseRepository
from app.models.job import JobDescription
from app.schemas.job import JobDescriptionCreate, JobDescriptionUpdate


class JobRepository(BaseRepository[JobDescription, JobDescriptionCreate, JobDescriptionUpdate]):
    """Repository for JobDescription model"""
    
    def __init__(self, db: Session):
        super().__init__(db, JobDescription)
    
    def get_user_jobs(self, user_id: str, skip: int = 0, limit: int = 100) -> List[JobDescription]:
        """
        Get all job descriptions for a user.
        
        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of job descriptions for the user
        """
        return self.get_multi(skip=skip, limit=limit, user_id=user_id)
    
    def get_public_jobs(self, skip: int = 0, limit: int = 100) -> List[JobDescription]:
        """
        Get all public job descriptions (those with no user_id).
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of public job descriptions
        """
        return (
            self.db.query(self.model)
            .filter(self.model.user_id.is_(None))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create_from_url(self, obj_in: dict, user_id: Optional[str] = None) -> JobDescription:
        """
        Create a job description from a URL.
        
        Args:
            obj_in: Job description data 
            user_id: Optional user ID
            
        Returns:
            Created job description
        """
        db_obj = JobDescription(
            id=obj_in.get("id"),
            title=obj_in.get("title"),
            company=obj_in.get("company"),
            description=obj_in.get("description"),
            source_url=obj_in.get("url"),
            is_from_url=True,
            user_id=user_id
        )
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def check_user_access(self, job_id: str, user_id: str) -> bool:
        """
        Check if a user has access to a job description.
        
        Args:
            job_id: Job description ID
            user_id: User ID
            
        Returns:
            True if the user has access, False otherwise
        """
        job = self.get(job_id)
        if not job:
            return False
        
        # Public jobs are accessible to all
        if job.user_id is None:
            return True
        
        # User-owned jobs are only accessible to that user
        return str(job.user_id) == user_id
