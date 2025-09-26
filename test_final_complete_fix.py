#!/usr/bin/env python3
"""
Final Complete Fix Test
Tests the complete fix for stale data issue
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
from app.filters import filter_service

def test_complete_fix():
    """Test the complete fix for stale data issues"""

    app = create_app()
    editing_service = EditingService()

    with app.app_context():
        print("🚀 Final Complete Fix Test")
        print("=" * 50)

        # Find an order to test with
        test_order = Order.query.first()
        if not test_order:
            print("❌ No orders found for testing")
            return False

        order_id = test_order.id
        original_status = test_order.order_status
        date_str = str(test_order.date)

        print(f"📋 Test Order: {order_id}")
        print(f"📋 Original Status: {original_status}")
        print(f"📋 Date: {date_str}")
        print()

        # Step 1: Make manual edit
        print("✏️  Making manual edit...")

        new_status = 'CANCELLED' if original_status != 'CANCELLED' else 'COMPLETED'
        edit_result = editing_service.update_order_data(
            order_id=order_id,
            update_data={
                'order_status': new_status,
                'cancellation_reason': 'Final test cancellation'
            },
            modified_by='test_final@example.com'
        )

        if not edit_result['success']:
            print(f"❌ Edit failed: {edit_result['error']}")
            return False

        print(f"✅ Edit successful - status changed to {new_status}")

        # Step 2: Verify database has the new data
        db.session.refresh(test_order)
        db_status = test_order.order_status
        print(f"📋 Database status: {db_status}")

        database_correct = db_status == new_status

        # Step 3: Test filter service with status filter (this is what matters for UI)
        print(f"\n🔍 Testing filter service with {new_status} status filter...")

        status_filters = {
            'date_from': date_str,
            'date_to': date_str,
            'order_status': [new_status],
            'page': 1,
            'per_page': 500  # Large number to ensure we get our order
        }

        status_result = filter_service.apply_filters(status_filters)

        if not status_result.get('success'):
            print(f"❌ Status filter failed: {status_result}")
            return False

        # Check if our order is in the filtered results
        status_orders = status_result.get('orders', [])
        found_in_status_filter = False
        order_data_in_filter = None

        for order in status_orders:
            if order.get('id') == order_id:
                found_in_status_filter = True
                order_data_in_filter = order
                break

        print(f"   Found in {new_status} filter: {'✅' if found_in_status_filter else '❌'}")

        if found_in_status_filter and order_data_in_filter:
            filter_status = order_data_in_filter.get('order_status')
            filter_cancellation = order_data_in_filter.get('cancellation_reason')

            print(f"   Status in filter results: {filter_status}")
            print(f"   Cancellation in filter results: {filter_cancellation}")

            filter_data_correct = (filter_status == new_status and
                                 filter_cancellation == 'Final test cancellation')
        else:
            filter_data_correct = False

        # Step 4: Test filter service with original status (should NOT find the order)
        print(f"\n🔍 Testing filter service with {original_status} status filter...")

        original_filters = {
            'date_from': date_str,
            'date_to': date_str,
            'order_status': [original_status],
            'page': 1,
            'per_page': 500
        }

        original_result = filter_service.apply_filters(original_filters)

        if original_result.get('success'):
            original_orders = original_result.get('orders', [])
            found_in_original_filter = any(order.get('id') == order_id for order in original_orders)
            print(f"   Found in {original_status} filter: {'❌ INCORRECTLY' if found_in_original_filter else '✅ CORRECTLY EXCLUDED'}")
        else:
            print(f"   Original status filter failed: {original_result}")
            found_in_original_filter = True  # Assume bad if filter failed

        # Step 5: Test all orders filter (should include our order with new status)
        print(f"\n🔍 Testing filter service with ALL orders...")

        all_filters = {
            'date_from': date_str,
            'date_to': date_str,
            'page': 1,
            'per_page': 500
        }

        all_result = filter_service.apply_filters(all_filters)

        if all_result.get('success'):
            all_orders = all_result.get('orders', [])
            found_in_all = False
            all_order_data = None

            for order in all_orders:
                if order.get('id') == order_id:
                    found_in_all = True
                    all_order_data = order
                    break

            print(f"   Found in ALL orders: {'✅' if found_in_all else '❌'}")

            if found_in_all and all_order_data:
                all_status = all_order_data.get('order_status')
                print(f"   Status in ALL orders: {all_status}")
                all_data_correct = all_status == new_status
            else:
                all_data_correct = False
        else:
            print(f"   ALL orders filter failed: {all_result}")
            all_data_correct = False

        # Final results
        all_tests_passed = (database_correct and
                           found_in_status_filter and
                           filter_data_correct and
                           not found_in_original_filter and
                           found_in_all and
                           all_data_correct)

        print(f"\n🎯 COMPLETE FIX TEST RESULTS:")
        print(f"   Database Update: {'✅ PASS' if database_correct else '❌ FAIL'}")
        print(f"   Status Filter Inclusion: {'✅ PASS' if found_in_status_filter else '❌ FAIL'}")
        print(f"   Filter Data Accuracy: {'✅ PASS' if filter_data_correct else '❌ FAIL'}")
        print(f"   Original Status Exclusion: {'✅ PASS' if not found_in_original_filter else '❌ FAIL'}")
        print(f"   All Orders Inclusion: {'✅ PASS' if found_in_all else '❌ FAIL'}")
        print(f"   All Orders Data Accuracy: {'✅ PASS' if all_data_correct else '❌ FAIL'}")

        print(f"\n🏁 COMPLETE FIX TEST: {'✅ ALL PASSED' if all_tests_passed else '❌ SOME FAILED'}")

        return all_tests_passed

if __name__ == "__main__":
    success = test_complete_fix()
    print(f"\n{'='*50}")
    print(f"COMPLETE FIX: {'✅ SUCCESS' if success else '❌ FAILED'}")
    exit(0 if success else 1)