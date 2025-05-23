from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    versions = relationship(
        "ResumeVersion", back_populates="resume", cascade="all, delete-orphan"
    )
    user = relationship("User", back_populates="resumes")

    # This attribute is not stored in the database but will be populated
    # when a Resume object is returned in an API response
    current_version = None


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id = Column(String, primary_key=True, index=True)
    resume_id = Column(
        String, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    content = Column(Text, nullable=False)
    version_number = Column(Integer, nullable=False)
    _is_customized = Column(
        "is_customized", Integer, default=0, nullable=False
    )  # 0 = not customized, 1 = customized
    job_description_id = Column(
        String, ForeignKey("job_descriptions.id"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    resume = relationship("Resume", back_populates="versions")
    job_description = relationship("JobDescription", back_populates="resume_versions")

    @property
    def is_customized(self) -> bool:
        """Convert integer column to boolean for Pydantic schema."""
        return bool(self._is_customized)

    @is_customized.setter
    def is_customized(self, value: bool) -> None:
        """Convert boolean to integer for database storage."""
        self._is_customized = 1 if value else 0

