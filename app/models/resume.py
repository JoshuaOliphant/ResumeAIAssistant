from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship

from app.db.session import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    versions = relationship("ResumeVersion", back_populates="resume", cascade="all, delete-orphan")
    user = relationship("User", back_populates="resumes")
    
    # This attribute is not stored in the database but will be populated
    # when a Resume object is returned in an API response
    # current_version = None


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id = Column(String, primary_key=True, index=True)
    resume_id = Column(String, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    version_number = Column(Integer, nullable=False)
    is_customized = Column(Integer, default=0, nullable=False)  # 0 = not customized, 1 = customized
    job_description_id = Column(String, ForeignKey("job_descriptions.id"), nullable=True)
    
    # Relationships
    resume = relationship("Resume", back_populates="versions")
    job_description = relationship("JobDescription", back_populates="resume_versions")