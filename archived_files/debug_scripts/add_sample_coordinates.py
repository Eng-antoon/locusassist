#!/usr/bin/env python3
"""
Add sample coordinate data to existing orders to demonstrate the functionality
"""

import logging
from app import create_app
from models import db, Order
from sqlalchemy import text
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_sample_coordinates():
    """Add sample coordinates to some existing orders"""
    try:
        app = create_app('development')

        with app.app_context():
            logger.info("🗺️ Adding sample coordinates to existing orders...")

            # Get some orders without coordinates from Egypt (based on country code)
            orders_without_coords = Order.query.filter(
                Order.location_country_code == 'EG',
                Order.location_latitude.is_(None),
                Order.location_longitude.is_(None)
            ).limit(10).all()

            if not orders_without_coords:
                logger.info("ℹ️ No orders found to add coordinates to")
                return True

            logger.info(f"📍 Found {len(orders_without_coords)} orders to add coordinates to")

            # Egypt coordinate ranges (approximate)
            # Cairo area: lat 29.5-30.5, lng 31.0-32.0
            # Alexandria: lat 31.0-31.5, lng 29.5-30.5
            # Other cities: broader range
            egypt_locations = [
                {"name": "Cairo area", "lat_range": (29.8, 30.3), "lng_range": (31.1, 31.5)},
                {"name": "Giza area", "lat_range": (29.9, 30.1), "lng_range": (31.0, 31.3)},
                {"name": "Alexandria area", "lat_range": (31.1, 31.3), "lng_range": (29.8, 30.2)},
                {"name": "Maadi area", "lat_range": (29.95, 30.05), "lng_range": (31.25, 31.35)},
                {"name": "Heliopolis area", "lat_range": (30.05, 30.15), "lng_range": (31.3, 31.4)}
            ]

            updated_count = 0
            for order in orders_without_coords:
                # Choose random location based on city name or random
                location_info = random.choice(egypt_locations)

                # Generate random coordinates within the range
                lat = round(random.uniform(*location_info["lat_range"]), 6)
                lng = round(random.uniform(*location_info["lng_range"]), 6)

                # Update the order
                order.location_latitude = lat
                order.location_longitude = lng

                logger.info(f"   📍 {order.id[:20]}... -> ({lat}, {lng}) [{location_info['name']}]")
                updated_count += 1

            # Commit changes
            db.session.commit()
            logger.info(f"✅ Successfully added coordinates to {updated_count} orders")

            # Verify the changes
            logger.info(f"\n🔍 Verifying coordinate addition...")
            with db.engine.connect() as conn:
                coord_result = conn.execute(text("""
                    SELECT COUNT(*) FROM orders
                    WHERE location_latitude IS NOT NULL AND location_longitude IS NOT NULL;
                """))
                coord_count = coord_result.fetchone()[0]
                logger.info(f"   Orders with coordinates: {coord_count}")

                # Show sample of added coordinates
                sample_result = conn.execute(text("""
                    SELECT id, location_name, location_city,
                           location_latitude, location_longitude
                    FROM orders
                    WHERE location_latitude IS NOT NULL
                    AND location_longitude IS NOT NULL
                    LIMIT 5;
                """))

                samples = sample_result.fetchall()
                logger.info(f"   Sample orders with coordinates:")
                for sample in samples:
                    logger.info(f"     - {sample[0][:25]}...: ({sample[3]}, {sample[4]}) - {sample[1] or 'N/A'}")

            logger.info(f"\n🎉 Sample coordinate addition completed!")
            return True

    except Exception as e:
        logger.error(f"❌ Error adding sample coordinates: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("🗺️ ADDING SAMPLE COORDINATES TO ORDERS")
    print("=" * 60)

    success = add_sample_coordinates()
    if success:
        print("\n🎉 Sample coordinates added successfully!")
        print("You can now see coordinate data in your PostgreSQL database!")
    else:
        print("\n❌ Failed to add sample coordinates!")