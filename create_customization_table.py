"""
Create the customization_plans table in the database.
Run this script manually to create the missing table.
"""
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the Base and models
from app.db.session import Base
from app.models.customization import CustomizationPlan

# Database configuration
DATABASE_URL = "sqlite:///./resume_app.db"
engine = create_engine(DATABASE_URL)

def create_tables():
    print("Creating customization_plans table...")
    # Create the customization_plans table only
    CustomizationPlan.__table__.create(engine, checkfirst=True)
    print("Table created successfully!")

if __name__ == "__main__":
    create_tables()