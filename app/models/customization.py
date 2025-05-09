import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship

from app.db.session import Base


class CustomizationPlan(Base):
    """Model for storing resume customization plans"""
    __tablename__ = "customization_plans"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    resume_id = Column(String(36), ForeignKey("resumes.id"), nullable=False)
    job_description_id = Column(String(36), ForeignKey("job_descriptions.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    customization_strength = Column(Integer, nullable=False, default=2)
    
    # Store the plan as JSON
    summary = Column(Text, nullable=False)
    job_analysis = Column(Text, nullable=False)
    keywords_to_add = Column(JSON, nullable=False)
    formatting_suggestions = Column(JSON, nullable=False)
    recommendations = Column(JSON, nullable=False)
    
    # Store the raw evaluation results for reference
    evaluation_results = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    resume = relationship("Resume")
    job_description = relationship("JobDescription")
    user = relationship("User")