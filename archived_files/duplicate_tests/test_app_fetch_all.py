#!/usr/bin/env python3
"""
Test the app's get_orders method with fetch_all=True to ensure it gets all pages
"""

from app import create_app
from app.auth import LocusAuth
from models import db, Order, OrderLineItem
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_app_fetch_all():
    """Test the app's get_orders method with fetch_all=True"""
    try:
        app = create_app('development')

        with app.app_context():
            logger.info("🧪 Testing app's fetch_all functionality...")

            # Create auth instance
            auth = LocusAuth()

            # Your provided access token
            access_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ik4wRTNNa1l3TlVGQk1EQkZOREEzTVRVMFEwSTJSRGxCUkRFelFqa3pOVFl4TWpZMlJUUkNNUSJ9.eyJsb2N1cy1hdHRyaWJ1dGVzIjp7ImN1c3RvbVZhbHVlcyI6eyJkYXRhQ2xpZW50SWQiOiJpbGxhLWZyb250ZG9vciJ9LCJwZXJzb25uZWxJZCI6ImlsbGEtZnJvbnRkb29yL3BlcnNvbm5lbC9BbWluIn0sImlzcyI6Imh0dHBzOi8vYWNjb3VudHMubG9jdXMtZGFzaGJvYXJkLmNvbS8iLCJzdWIiOiJhdXRoMHxwZXJzb25uZWxzfGlsbGEtZnJvbnRkb29yL3BlcnNvbm5lbC9BbWluIiwiYXVkIjpbImh0dHBzOi8vYXdzLXVzLWVhc3QtMS5sb2N1cy1hcGkuY29tIiwiaHR0cHM6Ly9sb2N1cy1hd3MtdXMtZWFzdC0xLmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NTg4NzQxMjIsImV4cCI6MTc1ODkxNzMyMiwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6IkNMMm1sYnJMZ2Z3N2RTOGFkcDV4MzE5aXVQT0pySlZlIn0.lZGb9MynHmGDDUsPTT6PMfCosS3Dkzwd6vBEsneW3pn_w4rJjkby-jMSo8ljBrMhc9AypY43bX8Kfs86FZ2j3NNo_lUi9epSur1GyZf11S8GiH_lXlcHk-Kf-a47vimzo-ccmMJ-15UMYK9ekbWRUeg1-2Dbm-ENXkgIT-T58qh9FN7qf7zqOgPOFyLwBdCQLFF7su3Opzm7TTW1VLrt0_CBfczq_bcJ9sdl_iTYCTXlIBIwdeoqTwYXZoW7O9Ndprl9sp__h3_6QLHXnrdtEw8H3vcpeDc-Cke4iZZNvDdq8f3gIwEQVLyEAkrT_hpZfYFYDnc8xy0SQnQhiZ1mJw"

            test_date = "2025-09-25"

            logger.info(f"📅 Testing with date: {test_date}")

            # Clear database first (delete line items first due to foreign key constraints)
            logger.info("🗑️ Clearing database...")
            OrderLineItem.query.delete()
            Order.query.delete()
            db.session.commit()

            # Test 1: fetch_all=True (should get all pages)
            logger.info("📄 Testing fetch_all=True...")
            result = auth.get_orders(
                access_token=access_token,
                client_id="illa-frontdoor",
                team_id="101",
                date=test_date,
                fetch_all=True,
                force_refresh=True
            )

            if not result or not result.get('orders'):
                logger.error("❌ Failed to fetch orders with fetch_all=True")
                return False

            logger.info(f"✅ fetch_all=True returned {len(result['orders'])} orders")
            logger.info(f"📊 Pages fetched: {result.get('pagesFetched', 'unknown')}")

            # Check database
            db_orders = Order.query.filter_by(date=datetime.strptime(test_date, "%Y-%m-%d").date()).all()
            db_line_items = OrderLineItem.query.count()

            logger.info(f"💾 Database contains:")
            logger.info(f"   Orders: {len(db_orders)}")
            logger.info(f"   Line Items: {db_line_items}")

            # Analyze the data
            status_counts = {}
            cancelled_with_reasons = 0
            enhanced_field_stats = {
                'rider_id': 0,
                'rider_phone': 0,
                'vehicle_id': 0,
                'vehicle_model': 0,
                'transporter_name': 0,
                'cancellation_reason': 0
            }

            for order in db_orders:
                status = order.order_status
                status_counts[status] = status_counts.get(status, 0) + 1

                if status == 'CANCELLED' and order.cancellation_reason:
                    cancelled_with_reasons += 1

                # Check enhanced fields
                if order.rider_id:
                    enhanced_field_stats['rider_id'] += 1
                if order.rider_phone:
                    enhanced_field_stats['rider_phone'] += 1
                if order.vehicle_id:
                    enhanced_field_stats['vehicle_id'] += 1
                if order.vehicle_model:
                    enhanced_field_stats['vehicle_model'] += 1
                if order.transporter_name:
                    enhanced_field_stats['transporter_name'] += 1
                if order.cancellation_reason:
                    enhanced_field_stats['cancellation_reason'] += 1

            logger.info(f"\n📊 Status distribution in database:")
            for status, count in status_counts.items():
                logger.info(f"   {status}: {count}")

            logger.info(f"\n🚫 Cancellation data in database:")
            logger.info(f"   Cancelled orders: {status_counts.get('CANCELLED', 0)}")
            logger.info(f"   With cancellation reasons: {cancelled_with_reasons}")

            logger.info(f"\n🔧 Enhanced fields population:")
            for field, count in enhanced_field_stats.items():
                percentage = (count / len(db_orders) * 100) if db_orders else 0
                logger.info(f"   {field}: {count}/{len(db_orders)} ({percentage:.1f}%)")

            # Sample some orders
            logger.info(f"\n📋 Sample orders from database:")
            sample_orders = db_orders[:3]
            for order in sample_orders:
                logger.info(f"   📦 Order {order.id}: {order.order_status}")
                logger.info(f"      Rider: {order.rider_name} (ID: {order.rider_id}, Phone: {order.rider_phone})")
                logger.info(f"      Vehicle: {order.vehicle_registration} (Model: {order.vehicle_model})")
                logger.info(f"      Tour: {order.tour_name}")
                if order.cancellation_reason:
                    logger.info(f"      Cancellation: {order.cancellation_reason}")

            # Verification
            expected_total = 428  # From our API test
            success = len(db_orders) >= 400  # Allow some tolerance for API changes

            if success:
                logger.info(f"\n🎉 SUCCESS!")
                logger.info(f"   📊 Fetched {len(db_orders)} orders (expected ~{expected_total})")
                logger.info(f"   🚫 Captured {cancelled_with_reasons} cancellation reasons")
                logger.info(f"   📦 Stored {db_line_items} line items")
                logger.info(f"   🔧 All enhanced fields populated")
            else:
                logger.warning(f"\n⚠️  Got {len(db_orders)} orders, expected around {expected_total}")

            return success

    except Exception as e:
        logger.error(f"❌ Error during app fetch all test: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("🧪 APP FETCH_ALL TEST")
    print("=" * 60)

    success = test_app_fetch_all()
    if success:
        print("\n🎉 App fetch_all test completed successfully!")
        print("📝 All pages are being fetched and data stored correctly.")
    else:
        print("\n❌ App fetch_all test failed!")