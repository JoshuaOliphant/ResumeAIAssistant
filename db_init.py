"""
Database initialization script.
This script will create the initial database tables and run migrations.
"""
import os
import sys
from alembic import command
from alembic.config import Config
from app.db.session import engine, Base
from app.core.config import settings

def init_db():
    """Initialize the database with tables and initial migration."""
    try:
        print("Initializing database...")
        
        # Create tables directly with SQLAlchemy
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully.")
        
        # Run Alembic migrations to track schema changes
        print("Running Alembic migrations...")
        alembic_cfg = Config("alembic.ini")
        
        # Create an initial migration
        # Skip if versions already exist
        versions_dir = os.path.join("migrations", "versions")
        if not os.listdir(versions_dir) or not any(f.endswith('.py') for f in os.listdir(versions_dir)):
            command.revision(alembic_cfg, 
                          message="Initial database schema", 
                          autogenerate=True)
            print("Initial migration created.")
        
        # Apply migrations
        command.upgrade(alembic_cfg, "head")
        print("Alembic migrations applied successfully.")
        
        print("Database initialization completed successfully!")
        return True
    except Exception as e:
        print(f"Database initialization failed: {str(e)}", file=sys.stderr)
        return False

if __name__ == "__main__":
    init_db()