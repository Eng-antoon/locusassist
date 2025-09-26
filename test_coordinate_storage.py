#!/usr/bin/env python3
"""
Test script to verify coordinate storage in PostgreSQL database
"""

import logging
from app import create_app
from models import db, Order
from datetime import datetime, timedelta
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_coordinate_storage():
    """Test that coordinates are being stored in PostgreSQL"""
    try:
        app = create_app('development')

        with app.app_context():
            logger.info("🐘 Testing PostgreSQL coordinate storage...")

            # Test 1: Check if new columns exist
            logger.info("\n1️⃣ Checking if coordinate columns exist in database...")

            from sqlalchemy import text
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
                logger.info("✅ Coordinate columns found:")
                for col in columns:
                    logger.info(f"   - {col[0]}: {col[1]} (nullable: {col[2]})")
            else:
                logger.error("❌ Coordinate columns not found!")
                return False

            # Test 2: Test inserting sample data with coordinates
            logger.info("\n2️⃣ Testing coordinate data insertion...")

            # Create test order data with coordinates
            test_order_data = {
                'id': 'TEST_ORDER_COORDS_001',
                'orderStatus': 'COMPLETED',
                'date': '2025-09-25',
                'location': {
                    'name': 'Test Location with Coordinates',
                    'address': {
                        'formattedAddress': 'Test Address, Cairo, Egypt',
                        'city': 'Cairo',
                        'countryCode': 'EG'
                    },
                    'latLng': {
                        'lat': 30.0444,  # Cairo latitude
                        'lng': 31.2357   # Cairo longitude
                    }
                }
            }

            # Store using our updated function
            from app.routes import store_order_from_api_data
            yesterday = datetime.now() - timedelta(days=1)
            date_str = yesterday.strftime("%Y-%m-%d")

            try:
                store_order_from_api_data(test_order_data, date_str)
                logger.info("✅ Test order with coordinates stored successfully")
            except Exception as e:
                logger.error(f"❌ Failed to store test order: {e}")
                return False

            # Test 3: Verify the coordinates were actually stored
            logger.info("\n3️⃣ Verifying coordinates were stored...")

            test_order = Order.query.filter_by(id='TEST_ORDER_COORDS_001').first()
            if test_order:
                logger.info("✅ Test order found in database:")
                logger.info(f"   - Order ID: {test_order.id}")
                logger.info(f"   - Location Name: {test_order.location_name}")
                logger.info(f"   - Location Address: {test_order.location_address}")
                logger.info(f"   - Location City: {test_order.location_city}")
                logger.info(f"   - 📍 Latitude: {test_order.location_latitude}")
                logger.info(f"   - 📍 Longitude: {test_order.location_longitude}")

                if test_order.location_latitude is not None and test_order.location_longitude is not None:
                    logger.info("✅ COORDINATES SUCCESSFULLY STORED! 🎉")
                else:
                    logger.error("❌ Coordinates are NULL in database")
                    return False
            else:
                logger.error("❌ Test order not found in database")
                return False

            # Test 4: Check existing orders for coordinates
            logger.info("\n4️⃣ Checking existing orders for coordinate data...")

            orders_with_coords = Order.query.filter(
                Order.location_latitude.isnot(None),
                Order.location_longitude.isnot(None)
            ).limit(5).all()

            if orders_with_coords:
                logger.info(f"✅ Found {len(orders_with_coords)} existing orders with coordinates:")
                for order in orders_with_coords:
                    logger.info(f"   - {order.id}: ({order.location_latitude}, {order.location_longitude})")
            else:
                logger.info("ℹ️ No existing orders have coordinate data yet")
                logger.info("   (This is expected if you haven't refreshed orders since the update)")

            # Test 5: Database connection and table info
            logger.info("\n5️⃣ Database connection and table information...")

            with db.engine.connect() as conn:
                # Check database name
                db_result = conn.execute(text("SELECT current_database();"))
                db_name = db_result.fetchone()[0]
                logger.info(f"   Connected to database: {db_name}")

                # Count total orders
                count_result = conn.execute(text("SELECT COUNT(*) FROM orders;"))
                total_orders = count_result.fetchone()[0]
                logger.info(f"   Total orders in database: {total_orders}")

                # Count orders with coordinates
                coord_result = conn.execute(text("""
                    SELECT COUNT(*) FROM orders
                    WHERE location_latitude IS NOT NULL
                    AND location_longitude IS NOT NULL;
                """))
                orders_with_coords_count = coord_result.fetchone()[0]
                logger.info(f"   Orders with coordinates: {orders_with_coords_count}")

            # Cleanup test data
            logger.info("\n6️⃣ Cleaning up test data...")
            if test_order:
                db.session.delete(test_order)
                db.session.commit()
                logger.info("✅ Test order cleaned up")

            logger.info("\n✅ PostgreSQL coordinate storage test completed successfully!")
            return True

    except Exception as e:
        logger.error(f"❌ Error during coordinate storage test: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def refresh_orders_to_populate_coordinates():
    """Refresh a small batch of orders to populate coordinates"""
    try:
        app = create_app('development')

        with app.app_context():
            from app.config import DevelopmentConfig
            from app.auth import LocusAuth

            config = DevelopmentConfig()
            auth = LocusAuth(config)

            # Use yesterday's date for orders with data
            yesterday = datetime.now() - timedelta(days=1)
            date = yesterday.strftime("%Y-%m-%d")

            logger.info(f"\n🔄 Refreshing orders for {date} to populate coordinates...")

            # This will fetch fresh data and update the database with coordinates
            orders_data = auth.refresh_orders_smart_merge(
                access_token=config.BEARER_TOKEN,
                client_id="illa-frontdoor",
                team_id="101",
                date=date,
                fetch_all=False,  # Just get first page for testing
                order_statuses=None
            )

            if orders_data and orders_data.get('orders'):
                logger.info(f"✅ Refreshed {len(orders_data['orders'])} orders")

                # Check if any now have coordinates
                orders_with_coords = Order.query.filter(
                    Order.date == datetime.strptime(date, "%Y-%m-%d").date(),
                    Order.location_latitude.isnot(None),
                    Order.location_longitude.isnot(None)
                ).limit(5).all()

                if orders_with_coords:
                    logger.info(f"🗺️ Found {len(orders_with_coords)} orders with coordinates after refresh:")
                    for order in orders_with_coords:
                        logger.info(f"   - {order.id}: ({order.location_latitude}, {order.location_longitude}) - {order.location_name}")
                else:
                    logger.info("ℹ️ No coordinates found in refreshed orders (may not be available in API response)")

                return True
            else:
                logger.error("❌ No orders returned from refresh")
                return False

    except Exception as e:
        logger.error(f"❌ Error refreshing orders: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == '__main__':
    print("=" * 70)
    print("🐘 POSTGRESQL COORDINATE STORAGE TEST")
    print("=" * 70)

    # Test coordinate storage functionality
    storage_success = test_coordinate_storage()

    if storage_success:
        print("\n" + "=" * 70)
        print("🔄 REFRESHING ORDERS TO POPULATE COORDINATES")
        print("=" * 70)

        # Try to refresh orders to populate coordinates
        refresh_success = refresh_orders_to_populate_coordinates()

        if refresh_success:
            print("\n🎉 All tests completed successfully!")
            print("The coordinate storage system is working and connected to PostgreSQL!")
        else:
            print("\n⚠️ Storage test passed but refresh failed (possibly due to expired token)")
    else:
        print("\n❌ Coordinate storage test failed!")