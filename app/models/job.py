import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class JobDescription(Base):
    """Model for storing job description information"""

    __tablename__ = "job_descriptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=True)
    source_url = Column(String(512), nullable=True)
    description = Column(Text, nullable=False)
    is_from_url = Column(Boolean, default=False)
    user_id = Column(
        String(36), ForeignKey("users.id"), nullable=True
    )  # Allow null for existing data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="job_descriptions")
