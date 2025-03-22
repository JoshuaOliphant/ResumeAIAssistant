"""
Database management script.
This script provides commands for managing the database.
"""
import argparse
import logging
import os
import sys
from alembic import command
from alembic.config import Config
from app.db.session import engine, Base
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables():
    """Create database tables directly using SQLAlchemy."""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to create tables: {str(e)}")
        return False

def drop_tables():
    """Drop all database tables."""
    try:
        logger.info("Dropping all database tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to drop tables: {str(e)}")
        return False

def create_migration(message):
    """Create a new migration."""
    try:
        logger.info(f"Creating migration: {message}")
        alembic_cfg = Config("alembic.ini")
        command.revision(alembic_cfg, message=message, autogenerate=True)
        logger.info("Migration created successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to create migration: {str(e)}")
        return False

def apply_migrations():
    """Apply all pending migrations."""
    try:
        logger.info("Applying migrations...")
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations applied successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to apply migrations: {str(e)}")
        return False

def rollback_migration(revision="head-1"):
    """Rollback to a previous migration."""
    try:
        logger.info(f"Rolling back to {revision}...")
        alembic_cfg = Config("alembic.ini")
        command.downgrade(alembic_cfg, revision)
        logger.info("Rollback completed successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to rollback: {str(e)}")
        return False

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Database management script")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Create tables command
    subparsers.add_parser("create_tables", help="Create database tables directly using SQLAlchemy")
    
    # Drop tables command
    subparsers.add_parser("drop_tables", help="Drop all database tables")
    
    # Create migration command
    create_migration_parser = subparsers.add_parser("create_migration", help="Create a new migration")
    create_migration_parser.add_argument("message", help="Migration message")
    
    # Apply migrations command
    subparsers.add_parser("apply_migrations", help="Apply all pending migrations")
    
    # Rollback migration command
    rollback_parser = subparsers.add_parser("rollback", help="Rollback to a previous migration")
    rollback_parser.add_argument("--revision", default="head-1", help="Revision to rollback to (default: head-1)")
    
    args = parser.parse_args()
    
    if args.command == "create_tables":
        create_tables()
    elif args.command == "drop_tables":
        drop_tables()
    elif args.command == "create_migration":
        create_migration(args.message)
    elif args.command == "apply_migrations":
        apply_migrations()
    elif args.command == "rollback":
        rollback_migration(args.revision)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()