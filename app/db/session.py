from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.config import settings

# Configure SQLAlchemy with SQLite
engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False},  # SQLite-specific option
    # Modified connection pooling settings appropriate for SQLite
    poolclass=QueuePool,
    pool_pre_ping=True,
    pool_size=5
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
