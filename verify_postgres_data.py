#!/usr/bin/env python3
"""
Verify PostgreSQL database has coordinate data properly stored
"""

import logging
from app import create_app
from models import db, Order
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_postgres_data():
    """Verify PostgreSQL database structure and data"""
    try:
        app = create_app('development')

        with app.app_context():
            logger.info("🐘 VERIFYING POSTGRESQL DATABASE")
            logger.info("=" * 50)

            with db.engine.connect() as conn:
                # 1. Database connection info
                logger.info("📊 Database Information:")
                db_result = conn.execute(text("SELECT current_database(), current_user, version();"))
                db_info = db_result.fetchone()
                logger.info(f"   Database: {db_info[0]}")
                logger.info(f"   User: {db_info[1]}")
                logger.info(f"   Version: {db_info[2][:50]}...")

                # 2. Table structure verification
                logger.info(f"\n🏗️ Orders Table Structure:")
                structure_result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = 'orders'
                    AND column_name LIKE '%location%'
                    ORDER BY ordinal_position;
                """))

                columns = structure_result.fetchall()
                for col in columns:
                    logger.info(f"   - {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")

                # 3. Data counts
                logger.info(f"\n📈 Data Statistics:")

                # Total orders
                total_result = conn.execute(text("SELECT COUNT(*) FROM orders;"))
                total_count = total_result.fetchone()[0]
                logger.info(f"   Total orders: {total_count}")

                # Orders with location data
                location_result = conn.execute(text("""
                    SELECT COUNT(*) FROM orders
                    WHERE location_name IS NOT NULL OR location_address IS NOT NULL;
                """))
                location_count = location_result.fetchone()[0]
                logger.info(f"   Orders with location data: {location_count}")

                # Orders with coordinates
                coord_result = conn.execute(text("""
                    SELECT COUNT(*) FROM orders
                    WHERE location_latitude IS NOT NULL AND location_longitude IS NOT NULL;
                """))
                coord_count = coord_result.fetchone()[0]
                logger.info(f"   Orders with coordinates: {coord_count}")

                # 4. Sample coordinate data
                if coord_count > 0:
                    logger.info(f"\n🗺️ Sample Orders with Coordinates:")
                    sample_result = conn.execute(text("""
                        SELECT id, location_name, location_city,
                               location_latitude, location_longitude,
                               date
                        FROM orders
                        WHERE location_latitude IS NOT NULL
                        AND location_longitude IS NOT NULL
                        LIMIT 5;
                    """))

                    samples = sample_result.fetchall()
                    for sample in samples:
                        logger.info(f"   📍 {sample[0][:20]}...")
                        logger.info(f"      Location: {sample[1] or 'N/A'}")
                        logger.info(f"      City: {sample[2] or 'N/A'}")
                        logger.info(f"      Coordinates: ({sample[3]}, {sample[4]})")
                        logger.info(f"      Date: {sample[5]}")
                        logger.info("")

                # 5. Recent orders (to check if refresh worked)
                logger.info(f"📅 Recent Orders (last 3 days):")
                recent_result = conn.execute(text("""
                    SELECT date, COUNT(*) as count,
                           COUNT(CASE WHEN location_latitude IS NOT NULL
                                      AND location_longitude IS NOT NULL
                                      THEN 1 END) as with_coords
                    FROM orders
                    WHERE date >= CURRENT_DATE - INTERVAL '3 days'
                    GROUP BY date
                    ORDER BY date DESC;
                """))

                recent_data = recent_result.fetchall()
                if recent_data:
                    for row in recent_data:
                        logger.info(f"   {row[0]}: {row[1]} orders ({row[2]} with coordinates)")
                else:
                    logger.info("   No recent orders found")

                # 6. Database health check
                logger.info(f"\n🔍 Database Health Check:")

                # Check indexes
                index_result = conn.execute(text("""
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE tablename = 'orders'
                    AND indexname LIKE '%location%';
                """))
                indexes = index_result.fetchall()

                if indexes:
                    logger.info("   Location-related indexes:")
                    for idx in indexes:
                        logger.info(f"   - {idx[0]}")
                else:
                    logger.info("   No location-specific indexes found")

                # 7. Coordinate data quality check
                if coord_count > 0:
                    logger.info(f"\n🎯 Coordinate Data Quality:")

                    # Check for valid coordinate ranges
                    quality_result = conn.execute(text("""
                        SELECT
                            COUNT(*) as total_coords,
                            COUNT(CASE WHEN location_latitude BETWEEN -90 AND 90
                                       AND location_longitude BETWEEN -180 AND 180
                                       THEN 1 END) as valid_coords,
                            MIN(location_latitude) as min_lat,
                            MAX(location_latitude) as max_lat,
                            MIN(location_longitude) as min_lng,
                            MAX(location_longitude) as max_lng
                        FROM orders
                        WHERE location_latitude IS NOT NULL
                        AND location_longitude IS NOT NULL;
                    """))

                    quality = quality_result.fetchone()
                    logger.info(f"   Total coordinates: {quality[0]}")
                    logger.info(f"   Valid coordinates: {quality[1]}")
                    logger.info(f"   Latitude range: {quality[2]:.4f} to {quality[3]:.4f}")
                    logger.info(f"   Longitude range: {quality[4]:.4f} to {quality[5]:.4f}")

            logger.info(f"\n✅ PostgreSQL verification completed!")

            # Summary
            logger.info(f"\n📋 SUMMARY:")
            logger.info(f"   ✅ Connected to PostgreSQL database: {db_info[0]}")
            logger.info(f"   ✅ Coordinate columns exist and are accessible")
            logger.info(f"   ✅ Total orders in database: {total_count}")
            logger.info(f"   ✅ Orders with coordinates: {coord_count}")

            if coord_count > 0:
                logger.info(f"   🎉 COORDINATE STORAGE IS WORKING!")
            else:
                logger.info(f"   ℹ️ No coordinate data yet (refresh orders to populate)")

            return True

    except Exception as e:
        logger.error(f"❌ Error verifying PostgreSQL data: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == '__main__':
    print("=" * 70)
    print("🐘 POSTGRESQL DATABASE VERIFICATION")
    print("=" * 70)

    success = verify_postgres_data()
    if success:
        print("\n🎉 PostgreSQL verification completed successfully!")
    else:
        print("\n❌ PostgreSQL verification failed!")