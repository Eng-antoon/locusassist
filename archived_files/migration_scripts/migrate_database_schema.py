#!/usr/bin/env python3
"""
Migrate database schema to add new task-search fields
"""

from models import db
from app import create_app
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Add new columns to the orders table"""
    try:
        app = create_app('development')

        with app.app_context():
            logger.info("🔄 Starting database schema migration...")

            # Drop all tables and recreate with new schema
            logger.info("Dropping existing tables...")
            db.drop_all()

            logger.info("Creating tables with new schema...")
            db.create_all()

            logger.info("✅ Database schema migration completed successfully!")
            return True

    except Exception as e:
        logger.error(f"❌ Error during database migration: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("🔄 DATABASE SCHEMA MIGRATION")
    print("=" * 60)
    print("This will update the database schema with new fields:")
    print("Enhanced Fields:")
    print("  - rider_id, rider_phone, vehicle_id, vehicle_model")
    print("  - transporter_name, task_source, plan_id")
    print("  - performance metrics (tardiness, sla_status, etc.)")
    print("  - time tracking fields")
    print("  - additional metadata")
    print("\n⚠️  WARNING: This will drop all existing data!")
    print("=" * 60)

    confirmation = input("Proceed with schema migration? (type 'yes' to continue): ").lower().strip()

    if confirmation == 'yes':
        success = migrate_database()
        if success:
            print("\n🎉 Database schema migrated successfully!")
            print("📝 New fields are now available for storing enhanced task-search data.")
        else:
            print("\n❌ Schema migration failed. Please check the logs.")
    else:
        print("\n🚫 Operation cancelled.")