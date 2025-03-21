# Import all the models for Alembic to detect
from app.db.session import Base
from app.models.resume import Resume, ResumeVersion
from app.models.job import JobDescription
