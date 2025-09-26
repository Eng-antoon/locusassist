#!/usr/bin/env python3
"""
Database migration script to add location coordinate columns to orders table
"""

import logging
from app import create_app
from models import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_coordinate_columns():
    """Add latitude and longitude columns to the orders table"""
    try:
        app = create_app('development')

        with app.app_context():
            logger.info("🗃️ Adding location coordinate columns to orders table...")

            # Create the new columns using text() for raw SQL
            from sqlalchemy import text

            logger.info("Creating location_latitude column...")
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE orders ADD COLUMN location_latitude FLOAT;'))
                conn.commit()

            logger.info("Creating location_longitude column...")
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE orders ADD COLUMN location_longitude FLOAT;'))
                conn.commit()

            logger.info("✅ Successfully added coordinate columns to orders table!")
            logger.info("   - location_latitude (FLOAT)")
            logger.info("   - location_longitude (FLOAT)")

            # Test the changes
            logger.info("🧪 Testing new columns...")
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'orders'
                    AND column_name IN ('location_latitude', 'location_longitude')
                    ORDER BY column_name;
                """))

            columns = result.fetchall()
            if columns:
                logger.info("New columns confirmed:")
                for col in columns:
                    logger.info(f"   - {col[0]}: {col[1]} (nullable: {col[2]})")
            else:
                logger.error("❌ Could not find the new columns!")
                return False

    except Exception as e:
        logger.error(f"❌ Error adding coordinate columns: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

    return True

if __name__ == '__main__':
    print("=" * 60)
    print("🗃️ DATABASE MIGRATION: ADD COORDINATE COLUMNS")
    print("=" * 60)

    success = add_coordinate_columns()
    if success:
        print("\n🎉 Database migration completed successfully!")
        print("The orders table now has location_latitude and location_longitude columns.")
    else:
        print("\n❌ Database migration failed!")