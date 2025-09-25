#!/usr/bin/env python3
"""
Clean all database tables for a fresh start
"""

from models import db, Order, OrderLineItem, ValidationResult, DashboardStats, Tour
from app import create_app
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_all_tables():
    """Clean all data from all tables"""
    try:
        app = create_app('development')

        with app.app_context():
            logger.info("🧹 Starting database cleanup...")

            # Delete all records from tables (order matters due to foreign keys)
            logger.info("Deleting ValidationResult records...")
            ValidationResult.query.delete()

            logger.info("Deleting OrderLineItem records...")
            OrderLineItem.query.delete()

            logger.info("Deleting Order records...")
            Order.query.delete()

            logger.info("Deleting Tour records...")
            Tour.query.delete()

            logger.info("Deleting DashboardStats records...")
            DashboardStats.query.delete()

            # Commit the changes
            db.session.commit()

            # Verify cleanup
            order_count = Order.query.count()
            line_item_count = OrderLineItem.query.count()
            validation_count = ValidationResult.query.count()
            tour_count = Tour.query.count()
            stats_count = DashboardStats.query.count()

            logger.info(f"✅ Database cleanup completed!")
            logger.info(f"📊 Remaining records:")
            logger.info(f"   - Orders: {order_count}")
            logger.info(f"   - Line Items: {line_item_count}")
            logger.info(f"   - Validations: {validation_count}")
            logger.info(f"   - Tours: {tour_count}")
            logger.info(f"   - Dashboard Stats: {stats_count}")

            if order_count == 0 and line_item_count == 0 and validation_count == 0:
                logger.info("🎉 All tables cleaned successfully! Ready for fresh start.")
                return True
            else:
                logger.warning("⚠️  Some records may still exist.")
                return False

    except Exception as e:
        logger.error(f"❌ Error during database cleanup: {e}")
        db.session.rollback()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("🗑️  DATABASE CLEANUP UTILITY")
    print("=" * 60)
    print("This will delete ALL data from all tables!")
    print("Tables to be cleaned:")
    print("  - orders")
    print("  - order_line_items")
    print("  - validation_results")
    print("  - tours")
    print("  - dashboard_stats")
    print("=" * 60)

    confirmation = input("Are you sure you want to proceed? (type 'yes' to continue): ").lower().strip()

    if confirmation == 'yes':
        success = clean_all_tables()
        if success:
            print("\n🎉 Database cleaned successfully! You can now test with fresh data.")
        else:
            print("\n❌ Database cleanup failed. Please check the logs.")
    else:
        print("\n🚫 Operation cancelled.")