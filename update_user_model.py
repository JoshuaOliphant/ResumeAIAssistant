"""
Script to update the User model in the database with is_superuser field.
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

def update_user_model():
    """Update the User model in the database"""
    try:
        # Check if the is_superuser column exists
        check_column = text("PRAGMA table_info(users);")
        columns = db.execute(check_column).fetchall()
        
        superuser_exists = any(col[1] == 'is_superuser' for col in columns)
        
        if not superuser_exists:
            print("Adding is_superuser column to users table...")
            
            # Add the is_superuser column
            add_column = text("ALTER TABLE users ADD COLUMN is_superuser BOOLEAN DEFAULT 0;")
            db.execute(add_column)
            db.commit()
            
            print("Column 'is_superuser' added successfully!")
        else:
            print("Column 'is_superuser' already exists. No migration needed.")
            
        # Create a test user with the updated schema
        test_user_email = "test@example.com"
        test_user_username = "testuser"
        
        # Check if test user exists
        check_user = text("SELECT id FROM users WHERE email = :email")
        existing_user = db.execute(check_user, {"email": test_user_email}).fetchone()
        
        if existing_user:
            print(f"Test user already exists with ID: {existing_user[0]}")
        else:
            from app.core.security import get_password_hash
            import uuid
            
            # Create the test user
            user_id = str(uuid.uuid4())
            
            insert_user = text(
                """
                INSERT INTO users 
                (id, email, username, full_name, hashed_password, is_active, is_superuser) 
                VALUES (:id, :email, :username, :full_name, :hashed_password, :is_active, :is_superuser)
                """
            )
            
            db.execute(insert_user, {
                "id": user_id,
                "email": test_user_email,
                "username": test_user_username,
                "full_name": "Test User",
                "hashed_password": get_password_hash("testpassword"),
                "is_active": True,
                "is_superuser": False
            })
            
            db.commit()
            
            print(f"Test user created successfully with ID: {user_id}")
            print(f"Username: {test_user_username}")
            print(f"Email: {test_user_email}")
            print(f"Password: testpassword")
    except Exception as e:
        db.rollback()
        print(f"Error updating user model: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    update_user_model()
