#!/usr/bin/env python3
"""
Test Orders Status Filtering After Edits
Tests that status filtering on the orders homepage works correctly after edits
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

def test_orders_status_filtering():
    """Test that status filtering works correctly after edits"""

    app = create_app()
    editing_service = EditingService()
    locus_auth = LocusAuth({})

    with app.app_context():
        print("🔍 Testing Orders Status Filtering After Edits")
        print("=" * 60)

        # Step 1: Find a test order that's not cancelled
        test_order = Order.query.filter(Order.order_status != 'CANCELLED').first()
        if not test_order:
            print("❌ No non-cancelled orders found for testing")
            return False

        order_id = test_order.id
        original_status = test_order.order_status
        date_str = str(test_order.date)

        print(f"📋 Test Order: {order_id}")
        print(f"📋 Original Status: {original_status}")
        print(f"📋 Date: {date_str}")
        print()

        # Step 2: Edit order to CANCELLED status
        print("✏️  Changing order status to CANCELLED...")

        edit_result = editing_service.update_order_data(
            order_id=order_id,
            update_data={
                'order_status': 'CANCELLED',
                'cancellation_reason': 'Test status filtering'
            },
            modified_by='test_status_filter@example.com'
        )

        if not edit_result['success']:
            print(f"❌ Status edit failed: {edit_result['error']}")
            return False

        print(f"✅ Status changed to CANCELLED")

        # Step 3: Test filtering by original status (should NOT include our order)
        print(f"\n🔍 Testing filter by original status: {original_status}")

        original_status_orders = locus_auth.get_orders(
            access_token="dummy_token",
            client_id="illa-frontdoor",
            date=date_str,
            fetch_all=True,
            force_refresh=False,
            order_statuses=[original_status]
        )

        # Our order should NOT be in these results
        test_order_in_original = False
        if original_status_orders and original_status_orders.get('orders'):
            for order_data in original_status_orders['orders']:
                if order_data.get('id') == order_id:
                    test_order_in_original = True
                    break

        print(f"   Order in {original_status} results: {'❌ INCORRECTLY INCLUDED' if test_order_in_original else '✅ CORRECTLY EXCLUDED'}")

        # Step 4: Test filtering by CANCELLED status (should include our order)
        print(f"\n🔍 Testing filter by new status: CANCELLED")

        cancelled_orders = locus_auth.get_orders(
            access_token="dummy_token",
            client_id="illa-frontdoor",
            date=date_str,
            fetch_all=True,
            force_refresh=False,
            order_statuses=['CANCELLED']
        )

        # Our order should be in these results
        test_order_in_cancelled = False
        cancelled_order_data = None
        if cancelled_orders and cancelled_orders.get('orders'):
            for order_data in cancelled_orders['orders']:
                if order_data.get('id') == order_id:
                    test_order_in_cancelled = True
                    cancelled_order_data = order_data
                    break

        print(f"   Order in CANCELLED results: {'✅ CORRECTLY INCLUDED' if test_order_in_cancelled else '❌ INCORRECTLY EXCLUDED'}")

        # Step 5: Verify the order data is correct in the filtered results
        if test_order_in_cancelled and cancelled_order_data:
            status_in_results = cancelled_order_data.get('orderStatus')
            cancellation_in_results = cancelled_order_data.get('cancellation_reason')

            print(f"   Status in results: {status_in_results} ({'✅' if status_in_results == 'CANCELLED' else '❌'})")
            print(f"   Cancellation in results: {cancellation_in_results} ({'✅' if cancellation_in_results == 'Test status filtering' else '❌'})")

            data_correct = (status_in_results == 'CANCELLED' and
                          cancellation_in_results == 'Test status filtering')
        else:
            data_correct = False

        # Step 6: Test ALL status filter (should include our order)
        print(f"\n🔍 Testing filter by ALL statuses")

        all_orders = locus_auth.get_orders(
            access_token="dummy_token",
            client_id="illa-frontdoor",
            date=date_str,
            fetch_all=True,
            force_refresh=False,
            order_statuses=None  # All statuses
        )

        # Our order should be in these results
        test_order_in_all = False
        if all_orders and all_orders.get('orders'):
            for order_data in all_orders['orders']:
                if order_data.get('id') == order_id:
                    test_order_in_all = True
                    break

        print(f"   Order in ALL results: {'✅ CORRECTLY INCLUDED' if test_order_in_all else '❌ INCORRECTLY EXCLUDED'}")

        # Final results
        all_tests_passed = (
            not test_order_in_original and  # Should be excluded from original status
            test_order_in_cancelled and     # Should be included in cancelled
            data_correct and                # Data should be correct
            test_order_in_all              # Should be included in all
        )

        print(f"\n🎯 STATUS FILTERING TESTS:")
        print(f"   Exclusion from old status: {'✅ PASS' if not test_order_in_original else '❌ FAIL'}")
        print(f"   Inclusion in new status: {'✅ PASS' if test_order_in_cancelled else '❌ FAIL'}")
        print(f"   Data correctness: {'✅ PASS' if data_correct else '❌ FAIL'}")
        print(f"   Inclusion in all statuses: {'✅ PASS' if test_order_in_all else '❌ FAIL'}")

        print(f"\n🏁 STATUS FILTERING TEST: {'✅ PASSED' if all_tests_passed else '❌ FAILED'}")

        return all_tests_passed

if __name__ == "__main__":
    success = test_orders_status_filtering()
    print(f"\n{'='*60}")
    print(f"STATUS FILTERING: {'✅ PASSED' if success else '❌ FAILED'}")
    exit(0 if success else 1)