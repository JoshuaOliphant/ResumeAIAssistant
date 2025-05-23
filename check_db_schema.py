"""
Script to check the database schema.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the database URL
from app.core.config import settings

# Create an engine and session
engine = create_engine(str(settings.DATABASE_URL))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def check_schema():
    """Check the database schema"""
    try:
        # List all tables
        tables_query = text("SELECT name FROM sqlite_master WHERE type='table';")
        tables = db.execute(tables_query).fetchall()
        
        print("Tables in the database:")
        for table in tables:
            print(f"- {table[0]}")
            
            # Get schema for each table
            schema_query = text(f"PRAGMA table_info({table[0]});")
            columns = db.execute(schema_query).fetchall()
            
            print("  Columns:")
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                not_null = "NOT NULL" if col[3] else "NULL"
                pk = "PRIMARY KEY" if col[5] else ""
                print(f"  - {col_name} ({col_type}) {not_null} {pk}")
            
            print()
    except Exception as e:
        print(f"Error checking schema: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    check_schema()
