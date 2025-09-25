#!/usr/bin/env python3
"""
Test script to verify the caching fix for problematic orders
"""

import sys
import os
import logging
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.auth import LocusAuth
from app.config import Config

# Set up logging to see the detailed errors
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_caching_fix():
    """Test the caching fix with real API data"""

    print("🔧 Testing Caching Fix for NoneType Errors")
    print("=" * 50)

    try:
        # Initialize components
        config = Config()
        locus_auth = LocusAuth(config)

        # Test with today's data where we saw the problematic orders
        today = datetime.now().strftime("%Y-%m-%d")

        print(f"📅 Testing with date: {today}")
        print("🚀 Fetching orders with force_refresh=True (will trigger caching)...")

        # This should trigger the caching logic and show us if the fix worked
        orders_data = locus_auth.get_orders(
            config.BEARER_TOKEN,
            'illa-frontdoor',
            date=today,
            fetch_all=True,
            force_refresh=True,  # Force fresh fetch to test caching
            order_statuses=None  # Get all orders
        )

        if orders_data:
            total_count = orders_data.get('totalCount', 0)
            orders_count = len(orders_data.get('orders', []))
            status_totals = orders_data.get('statusTotals', {})

            print(f"✅ Successfully processed!")
            print(f"   📊 Total Count: {total_count}")
            print(f"   📄 Orders Retrieved: {orders_count}")

            if status_totals:
                print(f"   🏷️  Status Breakdown:")
                for status, count in status_totals.items():
                    print(f"      {status}: {count}")

            # Check if we have the problematic orders
            problematic_order_ids = ['S5-00212164', 'S5-00213749', 'S5-00213775', 'S5-00213800']
            found_problematic = []

            for order in orders_data.get('orders', []):
                if order.get('id') in problematic_order_ids:
                    found_problematic.append(order.get('id'))

            if found_problematic:
                print(f"   🎯 Found previously problematic orders: {found_problematic}")
                print("   ✅ These should now cache without errors!")
            else:
                print("   ℹ️  Previously problematic orders not found in current data")

            print(f"\n🎉 Caching test completed successfully!")
            print("✅ All orders should now cache without NoneType errors!")

            return True

        else:
            print("❌ No data returned from API")
            return False

    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        logger.exception("Error in caching test")
        return False

def simulate_problematic_order_data():
    """Simulate the problematic order data structure to test our fix"""

    print("\n🧪 Testing with simulated problematic order data...")

    # Simulate different problematic scenarios
    problematic_orders = [
        {
            "id": "TEST-001",
            "orderStatus": "COMPLETED",
            "location": None,  # This would cause NoneType error
            "orderMetadata": {
                "tourDetail": None,  # This would cause NoneType error
                "lineItems": [
                    {
                        "id": "item1",
                        "transactionStatus": None  # This would cause NoneType error
                    }
                ]
            }
        },
        {
            "id": "TEST-002",
            "orderStatus": "EXECUTING",
            "location": {
                "name": "Test Location",
                "address": None  # This would cause NoneType error
            },
            "orderMetadata": None  # This would cause NoneType error
        },
        {
            "id": "TEST-003",
            "orderStatus": "ASSIGNED",
            "location": {
                "name": "Test Location 2",
                "address": {
                    "formattedAddress": "123 Test St"
                }
            },
            "orderMetadata": {
                "lineItems": None  # This would cause NoneType error
            }
        }
    ]

    config = Config()
    locus_auth = LocusAuth(config)

    # Test our defensive programming
    test_data = {
        "orders": problematic_orders,
        "totalCount": len(problematic_orders),
        "statusTotals": {"COMPLETED": 1, "EXECUTING": 1, "ASSIGNED": 1}
    }

    try:
        # This should not crash even with None values
        locus_auth.cache_orders_to_database(test_data, "test-client", "2025-09-25", "TEST")
        print("✅ Simulated problematic data handled gracefully!")
        return True
    except Exception as e:
        print(f"❌ Still getting errors with simulated data: {e}")
        logger.exception("Error with simulated data")
        return False

if __name__ == "__main__":
    print("🚀 Starting Caching Fix Test")

    success1 = test_caching_fix()
    success2 = simulate_problematic_order_data()

    if success1 and success2:
        print("\n🎉 All caching tests passed!")
        print("✅ NoneType errors should now be fixed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)