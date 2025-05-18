import sqlite3
import os
import sys
from pathlib import Path

def run_migration():
    """
    Add source_url and is_from_url columns to the job_descriptions table.
    """
    # Get the absolute path to the database file
    db_path = Path(__file__).parent / 'resume_app.db'
    
    print(f"Looking for database at: {db_path}")
    if not db_path.exists():
        print(f"Error: Database file not found at {db_path}")
        return False
    
    # Establish connection to the database
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the table exists
        table_exists = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='job_descriptions'"
        ).fetchone()
        
        if not table_exists:
            print("The job_descriptions table does not exist in the database.")
            return False
        
        # Check if columns already exist to avoid errors
        columns_info = cursor.execute("PRAGMA table_info(job_descriptions)").fetchall()
        column_names = [col[1] for col in columns_info]
        
        print(f"Existing columns: {column_names}")
        
        # Add source_url column if it doesn't exist
        if 'source_url' not in column_names:
            cursor.execute("ALTER TABLE job_descriptions ADD COLUMN source_url TEXT")
            print("Added source_url column to job_descriptions table")
        else:
            print("source_url column already exists in job_descriptions table")
        
        # Add is_from_url column if it doesn't exist
        if 'is_from_url' not in column_names:
            cursor.execute("ALTER TABLE job_descriptions ADD COLUMN is_from_url BOOLEAN NOT NULL DEFAULT 0")
            print("Added is_from_url column to job_descriptions table")
        else:
            print("is_from_url column already exists in job_descriptions table")
            
        conn.commit()
        print("Migration completed successfully")
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Migration failed: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)