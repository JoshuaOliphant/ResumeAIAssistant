from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class CustomizationPlan(Base):
    __tablename__ = "customization_plans"

    id = Column(String, primary_key=True, index=True)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False)
    job_description_id = Column(String, ForeignKey("job_descriptions.id"), nullable=False)
    plan_content = Column(Text, nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    progress = Column(Integer, default=0)  # 0-100 percent complete
    
    # Relationships
    resume = relationship("Resume", back_populates="customization_plans")
    job_description = relationship("JobDescription", back_populates="customization_plans")