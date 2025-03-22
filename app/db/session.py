from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Configure SQLAlchemy with PostgreSQL
engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,  # Verify connection is active
    pool_recycle=300,    # Recycle connections after 5 minutes
    pool_size=10,        # Connection pool size
    max_overflow=20      # Allow up to 20 additional connections
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
