import sqlite3
import os
import logfire

def run_migration():
    """
    Add source_url and is_from_url columns to the job_descriptions table.
    """
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resume_app.db')
    
    # Establish connection to the database
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist to avoid errors
        columns_info = cursor.execute("PRAGMA table_info(job_descriptions)").fetchall()
        column_names = [col[1] for col in columns_info]
        
        # Add source_url column if it doesn't exist
        if 'source_url' not in column_names:
            cursor.execute("ALTER TABLE job_descriptions ADD COLUMN source_url TEXT")
            logfire.info("Added source_url column to job_descriptions table")
        else:
            logfire.info("source_url column already exists in job_descriptions table")
        
        # Add is_from_url column if it doesn't exist
        if 'is_from_url' not in column_names:
            cursor.execute("ALTER TABLE job_descriptions ADD COLUMN is_from_url BOOLEAN NOT NULL DEFAULT 0")
            logfire.info("Added is_from_url column to job_descriptions table")
        else:
            logfire.info("is_from_url column already exists in job_descriptions table")
            
        conn.commit()
        logfire.info("Migration completed successfully")
        
    except Exception as e:
        if conn:
            conn.rollback()
        logfire.error(f"Migration failed: {str(e)}", error=str(e), traceback=logfire.format_exception(e))
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    run_migration()
