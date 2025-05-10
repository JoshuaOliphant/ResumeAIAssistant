import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class Resume(Base):
    """Model for storing resume information"""

    __tablename__ = "resumes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    user_id = Column(
        String(36), ForeignKey("users.id"), nullable=True
    )  # Allow null for existing data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    versions = relationship(
        "ResumeVersion", back_populates="resume", cascade="all, delete-orphan"
    )
    user = relationship("User", back_populates="resumes")


class ResumeVersion(Base):
    """Model for storing resume versions for version history"""

    __tablename__ = "resume_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    resume_id = Column(String(36), ForeignKey("resumes.id"), nullable=False)
    content = Column(Text, nullable=False)
    version_number = Column(Integer, nullable=False)
    is_customized = Column(
        Integer, default=0, nullable=False
    )  # 0 = original, 1 = customized
    job_description_id = Column(
        String(36), ForeignKey("job_descriptions.id"), nullable=True
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    resume = relationship("Resume", back_populates="versions")
    job_description = relationship("JobDescription")
