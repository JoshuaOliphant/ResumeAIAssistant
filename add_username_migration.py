"""
Migration script to add the username field to existing users.
Run this script to update the database schema.
"""

import os
import sys
import uuid
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

def run_migration():
    """Run the migration to add username field to users table"""
    try:
        # Check if the username column exists
        check_column = """
        PRAGMA table_info(users);
        """
        columns = db.execute(text(check_column)).fetchall()
        username_exists = any(col[1] == 'username' for col in columns)
        
        if not username_exists:
            print("Adding username column to users table...")
            
            # Add the username column
            add_column = """
            ALTER TABLE users ADD COLUMN username TEXT;
            """
            db.execute(text(add_column))
            db.commit()
            
            # Generate default usernames for existing users
            users = db.execute(text("SELECT id, email FROM users")).fetchall()
            for user in users:
                user_id, email = user
                # Create a username from the email (part before @)
                default_username = email.split('@')[0] + str(uuid.uuid4())[:8]
                
                # Update the user with the default username
                update_user = f"""
                UPDATE users SET username = '{default_username}' WHERE id = '{user_id}';
                """
                db.execute(text(update_user))
            
            # Make the username column NOT NULL and UNIQUE
            create_unique_index = """
            CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users(username);
            """
            db.execute(text(create_unique_index))
            
            db.commit()
            print("Migration completed successfully!")
        else:
            print("Username column already exists. No migration needed.")
    except Exception as e:
        db.rollback()
        print(f"Migration failed: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
