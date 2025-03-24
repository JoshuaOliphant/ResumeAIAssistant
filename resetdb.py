"""
Script to recreate the database schema
"""
import os
import logging

from app.db.session import Base, engine
# Import all models to make sure they're registered with SQLAlchemy
from app.models import resume, user
# Try to import job_description if it exists
try:
    from app.models import job_description
except ImportError:
    print("Note: job_description model not found")
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_database():
    """
    Drop all tables and recreate them
    """
    logger.info("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    
    logger.info("Creating new tables...")
    Base.metadata.create_all(bind=engine)
    
    logger.info("Database reset complete!")

if __name__ == "__main__":
    # Check if --yes flag is passed
    import sys
    auto_yes = "--yes" in sys.argv
    
    if not auto_yes:
        # Ask for confirmation before resetting the database
        logger.warning("This will delete all data in the database.")
        try:
            user_input = input("Are you sure you want to reset the database? (y/N): ")
            if user_input.lower() != 'y':
                logger.info("Database reset canceled.")
                exit(0)
        except (EOFError, KeyboardInterrupt):
            logger.info("Database reset canceled.")
            exit(0)
    else:
        logger.info("Auto-confirming database reset due to --yes flag")
    
    reset_database()