#!/usr/bin/env python3
"""
Test script to verify coordinate storage during refresh functionality
"""

from app import create_app
from app.config import DevelopmentConfig
from app.auth import LocusAuth
from models import db, Order
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_coordinate_refresh():
    """Test coordinate extraction during refresh"""
    try:
        app = create_app('development')
        config = DevelopmentConfig()

        with app.app_context():
            logger.info("🧪 Starting coordinate refresh test...")

            # Create auth instance
            auth = LocusAuth(config)

            # Test date (yesterday - more likely to have data)
            from datetime import timedelta
            test_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            logger.info(f"Testing with date: {test_date}")

            # Count orders with coordinates before refresh
            orders_before = Order.query.filter_by(date=datetime.strptime(test_date, "%Y-%m-%d").date()).count()
            orders_with_coords_before = Order.query.filter(
                Order.date == datetime.strptime(test_date, "%Y-%m-%d").date(),
                Order.location_latitude.isnot(None),
                Order.location_longitude.isnot(None)
            ).count()

            logger.info(f"📊 Before refresh: {orders_before} total orders, {orders_with_coords_before} with coordinates")

            # Perform refresh using smart merge (which calls the task-search API)
            logger.info("🔄 Performing refresh...")
            result = auth.refresh_orders_smart_merge(
                config.BEARER_TOKEN,
                'illa-frontdoor',
                date=test_date,
                fetch_all=True
            )

            if not result:
                logger.error("❌ Refresh failed")
                return False

            logger.info(f"✅ Refresh completed: {result.get('totalCount', 0)} orders")

            # Count orders with coordinates after refresh
            orders_after = Order.query.filter_by(date=datetime.strptime(test_date, "%Y-%m-%d").date()).count()
            orders_with_coords_after = Order.query.filter(
                Order.date == datetime.strptime(test_date, "%Y-%m-%d").date(),
                Order.location_latitude.isnot(None),
                Order.location_longitude.isnot(None)
            ).count()

            logger.info(f"📊 After refresh: {orders_after} total orders, {orders_with_coords_after} with coordinates")

            # Show some sample coordinates
            sample_orders = Order.query.filter(
                Order.date == datetime.strptime(test_date, "%Y-%m-%d").date(),
                Order.location_latitude.isnot(None),
                Order.location_longitude.isnot(None)
            ).limit(5).all()

            logger.info("📍 Sample coordinates:")
            for order in sample_orders:
                logger.info(f"  Order {order.id}: {order.location_latitude}, {order.location_longitude} - {order.location_city}")

            improvement = orders_with_coords_after - orders_with_coords_before
            logger.info(f"📈 Coordinate extraction improvement: +{improvement} orders now have coordinates")

            return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_coordinate_refresh()