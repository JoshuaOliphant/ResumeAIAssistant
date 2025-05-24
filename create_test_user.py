"""
Script to create a test user for authentication testing.
"""

import os
import sys
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the necessary modules
from app.core.config import settings
from app.core.security import get_password_hash

# Create an engine and session
engine = create_engine(str(settings.DATABASE_URL))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def create_test_user():
    """Create a test user for authentication testing"""
    try:
        # Check if test user already exists using raw SQL
        check_user = text("SELECT id FROM users WHERE email = 'test@example.com'")
        existing_user = db.execute(check_user).fetchone()
        
        if existing_user:
            print(f"Test user already exists with ID: {existing_user[0]}")
            return
        
        # Create a new test user with raw SQL
        user_id = str(uuid.uuid4())
        hashed_pw = get_password_hash("testpassword")
        
        insert_user = text(
            "INSERT INTO users (id, email, username, full_name, hashed_password, is_active, is_superuser) "
            "VALUES (:id, :email, :username, :full_name, :hashed_password, :is_active, :is_superuser)"
        )
        
        db.execute(insert_user, {
            "id": user_id,
            "email": "test@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "hashed_password": hashed_pw,
            "is_active": True,
            "is_superuser": False
        })
        
        db.commit()
        
        print(f"Test user created successfully with ID: {user_id}")
        print("Username: testuser")
        print("Email: test@example.com")
        print("Password: testpassword")
    except Exception as e:
        db.rollback()
        print(f"Failed to create test user: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user()
