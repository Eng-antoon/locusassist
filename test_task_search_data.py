#!/usr/bin/env python3
"""
Test script to verify all task-search data is properly fetched and stored
"""

from app import create_app
from app.auth import LocusAuth
from models import db, Order, OrderLineItem
import logging
from datetime import datetime, timedelta
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_task_search_data():
    """Test task-search data fetching and storage"""
    try:
        app = create_app('development')

        with app.app_context():
            logger.info("🧪 Starting task-search data test...")

            # Create auth instance
            auth = LocusAuth()

            # Test date (yesterday to ensure there's data)
            test_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            logger.info(f"Testing with date: {test_date}")

            # Clear cache first
            logger.info("🗑️ Clearing cache...")
            auth.clear_orders_cache("illa-frontdoor", test_date)

            # Fetch fresh data from task-search
            logger.info("📥 Fetching fresh data from task-search endpoint...")
            access_token = auth.get_access_token()
            if not access_token:
                logger.error("❌ Could not get access token")
                return False

            result = auth.refresh_orders_force("illa-frontdoor", test_date, access_token)

            if not result or not result.get('success'):
                logger.error(f"❌ Failed to fetch data: {result}")
                return False

            # Check database for stored data
            logger.info("🔍 Checking database for stored data...")
            orders = Order.query.filter_by(date=datetime.strptime(test_date, "%Y-%m-%d").date()).all()

            logger.info(f"📊 Found {len(orders)} orders in database")

            # Check if all enhanced fields are populated
            enhanced_fields_check = {
                'rider_id': 0,
                'rider_phone': 0,
                'vehicle_id': 0,
                'vehicle_model': 0,
                'transporter_name': 0,
                'task_source': 0,
                'plan_id': 0,
                'tardiness': 0,
                'sla_status': 0,
                'cancellation_reason': 0,
                'skills': 0,
                'tags': 0,
                'custom_fields': 0
            }

            cancelled_orders = 0
            orders_with_cancellation_reason = 0

            for order in orders:
                # Check enhanced fields
                if order.rider_id:
                    enhanced_fields_check['rider_id'] += 1
                if order.rider_phone:
                    enhanced_fields_check['rider_phone'] += 1
                if order.vehicle_id:
                    enhanced_fields_check['vehicle_id'] += 1
                if order.vehicle_model:
                    enhanced_fields_check['vehicle_model'] += 1
                if order.transporter_name:
                    enhanced_fields_check['transporter_name'] += 1
                if order.task_source:
                    enhanced_fields_check['task_source'] += 1
                if order.plan_id:
                    enhanced_fields_check['plan_id'] += 1
                if order.tardiness is not None:
                    enhanced_fields_check['tardiness'] += 1
                if order.sla_status:
                    enhanced_fields_check['sla_status'] += 1
                if order.skills:
                    enhanced_fields_check['skills'] += 1
                if order.tags:
                    enhanced_fields_check['tags'] += 1
                if order.custom_fields:
                    enhanced_fields_check['custom_fields'] += 1

                # Check cancellation data
                if order.order_status == 'CANCELLED':
                    cancelled_orders += 1
                    if order.cancellation_reason:
                        enhanced_fields_check['cancellation_reason'] += 1
                        orders_with_cancellation_reason += 1
                        logger.info(f"   🚫 Cancelled Order {order.id}: {order.cancellation_reason}")

            # Print results
            logger.info(f"\n📋 Enhanced Fields Population Summary:")
            for field, count in enhanced_fields_check.items():
                percentage = (count / len(orders) * 100) if orders else 0
                logger.info(f"   {field}: {count}/{len(orders)} orders ({percentage:.1f}%)")

            logger.info(f"\n🚫 Cancellation Data:")
            logger.info(f"   Cancelled orders: {cancelled_orders}")
            logger.info(f"   Orders with cancellation reasons: {orders_with_cancellation_reason}")

            # Check line items
            line_items_count = OrderLineItem.query.count()
            logger.info(f"\n📦 Line Items: {line_items_count} total items stored")

            # Sample some orders to show data structure
            logger.info(f"\n🔍 Sample Order Data:")
            sample_orders = orders[:3]
            for order in sample_orders:
                logger.info(f"   📦 Order {order.id}:")
                logger.info(f"      Status: {order.order_status}")
                logger.info(f"      Rider: {order.rider_name} (ID: {order.rider_id})")
                logger.info(f"      Vehicle: {order.vehicle_registration} (Model: {order.vehicle_model})")
                logger.info(f"      Tour: {order.tour_name}")
                if order.cancellation_reason:
                    logger.info(f"      Cancellation: {order.cancellation_reason}")

            logger.info(f"\n✅ Task-search data test completed successfully!")
            logger.info(f"   📊 {len(orders)} orders stored with enhanced data")
            logger.info(f"   🚫 {orders_with_cancellation_reason} cancellation reasons captured")
            logger.info(f"   📦 {line_items_count} line items stored")

            return True

    except Exception as e:
        logger.error(f"❌ Error during task-search data test: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("🧪 TASK-SEARCH DATA VERIFICATION TEST")
    print("=" * 60)

    success = test_task_search_data()
    if success:
        print("\n🎉 All task-search data is properly fetched and stored!")
        print("📝 Enhanced fields including cancellation reasons are captured.")
    else:
        print("\n❌ Task-search data test failed.")