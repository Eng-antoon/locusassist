#!/usr/bin/env python3
"""
Test Orders Homepage Data Refresh
Tests that the orders homepage shows updated data immediately after edits
"""

import os
import sys
import json
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, Order
from app import create_app
from app.editing_routes import EditingService
from app.auth import LocusAuth

def test_orders_homepage_refresh():
    """Test that orders homepage shows updated data after edits"""

    app = create_app()
    editing_service = EditingService()
    locus_auth = LocusAuth({})

    with app.app_context():
        print("🔄 Testing Orders Homepage Data Refresh After Edits")
        print("=" * 60)

        # Step 1: Find a test order
        test_order = Order.query.first()
        if not test_order:
            print("❌ No orders found for testing")
            return False

        order_id = test_order.id
        original_status = test_order.order_status
        original_cancellation = test_order.cancellation_reason
        date_str = str(test_order.date)

        print(f"📋 Test Order: {order_id}")
        print(f"📋 Original Status: {original_status}")
        print(f"📋 Original Cancellation: {original_cancellation}")
        print(f"📋 Date: {date_str}")
        print()

        # Step 2: Make manual edits
        print("✏️  Making manual edits...")

        new_status = 'CANCELLED' if original_status != 'CANCELLED' else 'COMPLETED'
        new_cancellation = 'TEST MANUAL CANCELLATION REASON'

        edit_result = editing_service.update_order_data(
            order_id=order_id,
            update_data={
                'order_status': new_status,
                'cancellation_reason': new_cancellation
            },
            modified_by='test_homepage_refresh@example.com'
        )

        if not edit_result['success']:
            print(f"❌ Manual edit failed: {edit_result['error']}")
            return False

        print(f"✅ Manual edit successful: {edit_result['message']}")
        print(f"✅ Updated fields: {edit_result['updated_fields']}")

        # Step 3: Verify the database was updated
        db.session.refresh(test_order)
        print(f"📋 Database after edit - Status: {test_order.order_status}")
        print(f"📋 Database after edit - Cancellation: {test_order.cancellation_reason}")
        print()

        # Step 4: Test what the orders homepage would return (the original issue)
        print("🏠 Testing orders homepage data source...")

        # This simulates what happens when the orders homepage loads
        orders_data = locus_auth.get_orders(
            access_token="dummy_token",  # Not used for database query
            client_id="illa-frontdoor",
            date=date_str,
            fetch_all=True,
            force_refresh=False  # This should use database cache
        )

        if not orders_data or not orders_data.get('orders'):
            print("❌ No orders returned from homepage data source")
            return False

        # Find our test order in the results
        test_order_data = None
        for order_data in orders_data['orders']:
            if order_data.get('id') == order_id:
                test_order_data = order_data
                break

        if not test_order_data:
            print(f"❌ Test order {order_id} not found in homepage results")
            return False

        # Step 5: Verify the homepage shows the updated data
        homepage_status = test_order_data.get('orderStatus')
        homepage_cancellation = test_order_data.get('cancellation_reason')

        print(f"🏠 Homepage shows - Status: {homepage_status}")
        print(f"🏠 Homepage shows - Cancellation: {homepage_cancellation}")
        print()

        # Check if the edits are reflected
        status_correct = homepage_status == new_status
        cancellation_correct = homepage_cancellation == new_cancellation

        print("🎯 Results:")
        print(f"   Status Update: {'✅ CORRECT' if status_correct else '❌ STALE'}")
        print(f"   Cancellation Update: {'✅ CORRECT' if cancellation_correct else '❌ STALE'}")

        if not status_correct:
            print(f"      Expected: {new_status}, Got: {homepage_status}")
        if not cancellation_correct:
            print(f"      Expected: {new_cancellation}, Got: {homepage_cancellation}")

        # Step 6: Also check modification tracking info
        is_modified = test_order_data.get('is_modified', False)
        modified_fields = test_order_data.get('modified_fields', [])

        print(f"   Modification Tracking: {'✅ CORRECT' if is_modified else '❌ MISSING'}")
        print(f"   Modified Fields: {modified_fields}")

        # Final result
        all_correct = status_correct and cancellation_correct and is_modified

        print(f"\n🏁 ORDERS HOMEPAGE REFRESH TEST: {'✅ PASSED' if all_correct else '❌ FAILED'}")

        if not all_correct:
            print("\n🔧 Issues Found:")
            if not status_correct:
                print(f"   - Status not updated on homepage: expected '{new_status}', got '{homepage_status}'")
            if not cancellation_correct:
                print(f"   - Cancellation not updated on homepage: expected '{new_cancellation}', got '{homepage_cancellation}'")
            if not is_modified:
                print("   - Modification tracking not reflected on homepage")

        return all_correct

if __name__ == "__main__":
    success = test_orders_homepage_refresh()
    print(f"\n{'='*60}")
    print(f"ORDERS HOMEPAGE REFRESH: {'✅ PASSED' if success else '❌ FAILED'}")
    exit(0 if success else 1)