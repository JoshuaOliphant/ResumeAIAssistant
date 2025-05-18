from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="job_descriptions")
    resume_versions = relationship("ResumeVersion", back_populates="job_description")
    customization_plans = relationship("CustomizationPlan", back_populates="job_description", cascade="all, delete-orphan")