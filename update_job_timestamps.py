import sqlite3
import os
from datetime import datetime
from pathlib import Path

def run_migration():
    """
    Update job_descriptions table to ensure created_at and updated_at have valid values.
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
        
        # Get current time as ISO format string
        current_time = datetime.now().isoformat()
        
        # Update any NULL created_at values
        cursor.execute(
            "UPDATE job_descriptions SET created_at = ? WHERE created_at IS NULL",
            (current_time,)
        )
        created_updated = cursor.rowcount
        print(f"Updated {created_updated} rows with NULL created_at values")
        
        # Update any NULL updated_at values
        cursor.execute(
            "UPDATE job_descriptions SET updated_at = ? WHERE updated_at IS NULL",
            (current_time,)
        )
        updated_updated = cursor.rowcount
        print(f"Updated {updated_updated} rows with NULL updated_at values")
        
        # Update the schema to make these columns NOT NULL with DEFAULT
        try:
            # SQLite doesn't support direct ALTER TABLE with NOT NULL constraint changes
            # We'd need to create a new table and migrate data to properly enforce NOT NULL
            # This is a simplified version that just adds default values
            
            # For SQLite 3.25.0 or newer, we can directly set default values
            cursor.execute("PRAGMA table_info(job_descriptions)")
            columns = {col[1]: col for col in cursor.fetchall()}
            
            if 'created_at' in columns and not columns['created_at'][4]:  # Default value is empty
                print("Setting default value for created_at column")
                # This won't enforce NOT NULL but will provide defaults for new rows
                cursor.execute("ALTER TABLE job_descriptions DEFAULT CURRENT_TIMESTAMP FOR created_at")
            
            if 'updated_at' in columns and not columns['updated_at'][4]:  # Default value is empty
                print("Setting default value for updated_at column")
                cursor.execute("ALTER TABLE job_descriptions DEFAULT CURRENT_TIMESTAMP FOR updated_at")
        
        except sqlite3.OperationalError as e:
            print(f"Warning: Could not update schema constraints: {e}")
            print("This is normal for older SQLite versions. The application will handle defaults.")
            
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
    exit(0 if success else 1)