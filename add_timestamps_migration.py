#!/usr/bin/env python

"""
Migration script to add timestamp columns to Resume and ResumeVersion tables.
This script also updates existing records with current timestamps.
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, Column, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Get the project directory
project_dir = os.path.dirname(os.path.abspath(__file__))

# Database path
db_path = os.path.join(project_dir, "resume_app.db")
DATABASE_URL = f"sqlite:///{db_path}"

# Create engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Run the migration
def run_migration():
    """Add timestamp columns to Resume and ResumeVersion tables."""
    session = SessionLocal()
    
    try:
        # Check if columns already exist in Resume table
        resume_has_created_at = False
        resume_has_updated_at = False
        version_has_created_at = False
        
        # Get table info for Resume
        resume_columns = session.execute(text("PRAGMA table_info(resumes)")).fetchall()
        for col in resume_columns:
            if col[1] == 'created_at':
                resume_has_created_at = True
            if col[1] == 'updated_at':
                resume_has_updated_at = True
        
        # Get table info for ResumeVersion
        version_columns = session.execute(text("PRAGMA table_info(resume_versions)")).fetchall()
        for col in version_columns:
            if col[1] == 'created_at':
                version_has_created_at = True
        
        # Add columns if they don't exist
        if not resume_has_created_at:
            session.execute(text("ALTER TABLE resumes ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
            print("Added created_at column to Resume table")
        
        if not resume_has_updated_at:
            session.execute(text("ALTER TABLE resumes ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
            print("Added updated_at column to Resume table")
        
        if not version_has_created_at:
            session.execute(text("ALTER TABLE resume_versions ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
            print("Added created_at column to ResumeVersion table")
        
        # Update existing records with current timestamps for all columns
        # Note: SQLite doesn't support ON UPDATE for timestamps, so we need to update manually
        now = datetime.utcnow()
        
        # Update Resume records if needed
        if resume_has_created_at or resume_has_updated_at:
            update_statement = "UPDATE resumes SET "
            update_clauses = []
            
            if resume_has_created_at:
                update_clauses.append("created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
            if resume_has_updated_at:
                update_clauses.append("updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
            
            if update_clauses:
                for clause in update_clauses:
                    session.execute(text(f"UPDATE resumes SET {clause}"))
                print("Updated existing Resume records with timestamps")
        
        # Update ResumeVersion records if needed
        if version_has_created_at:
            session.execute(text("UPDATE resume_versions SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
            print("Updated existing ResumeVersion records with timestamps")
        
        # Commit the changes
        session.commit()
        print("Migration completed successfully")
        
    except Exception as e:
        session.rollback()
        print(f"Error during migration: {str(e)}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    print("Starting migration to add timestamp columns...")
    run_migration()
    print("Migration completed")
