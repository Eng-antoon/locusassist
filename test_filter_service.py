#!/usr/bin/env python3
"""
Test Filter Service
Tests the filter service that the frontend actually uses
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

def test_filter_service():
    """Test the filter service that the frontend uses"""

    app = create_app()
    editing_service = EditingService()

    with app.app_context():
        print("🔍 Testing Filter Service (Real Frontend Data Source)")
        print("=" * 60)

        # Step 1: Find a test order
        test_order = Order.query.filter(Order.order_status != 'CANCELLED').first()
        if not test_order:
            print("❌ No suitable orders found for testing")
            return False

        order_id = test_order.id
        original_status = test_order.order_status
        date_str = str(test_order.date)

        print(f"📋 Test Order: {order_id}")
        print(f"📋 Original Status: {original_status}")
        print(f"📋 Date: {date_str}")
        print()

        # Step 2: Test filter service BEFORE editing
        print("🔍 Testing filter service BEFORE editing...")

        filters_before = {
            'date_from': date_str,
            'date_to': date_str,
            'page': 1,
            'per_page': 100
        }

        result_before = filter_service.apply_filters(filters_before)

        if not result_before.get('success'):
            print(f"❌ Filter service failed: {result_before}")
            return False

        orders_before = result_before.get('orders', [])
        test_order_before = None

        for order in orders_before:
            if order.get('id') == order_id:
                test_order_before = order
                break

        if not test_order_before:
            print(f"❌ Test order not found in filter results before editing")
            return False

        print(f"✅ Filter service found order - Status: {test_order_before.get('order_status')}")
        print()

        # Step 3: Make manual edit
        print("✏️  Making manual edit...")

        edit_result = editing_service.update_order_data(
            order_id=order_id,
            update_data={
                'order_status': 'CANCELLED',
                'cancellation_reason': 'Filter Service Test Cancellation'
            },
            modified_by='test_filter_service@example.com'
        )

        if not edit_result['success']:
            print(f"❌ Edit failed: {edit_result['error']}")
            return False

        print(f"✅ Edit successful - status changed to CANCELLED")

        # Step 4: Check database directly
        db.session.refresh(test_order)
        print(f"📋 Database shows: {test_order.order_status}")
        print()

        # Step 5: Test filter service AFTER editing
        print("🔍 Testing filter service AFTER editing...")

        filters_after = {
            'date_from': date_str,
            'date_to': date_str,
            'page': 1,
            'per_page': 100
        }

        result_after = filter_service.apply_filters(filters_after)

        if not result_after.get('success'):
            print(f"❌ Filter service failed after editing: {result_after}")
            return False

        orders_after = result_after.get('orders', [])
        test_order_after = None

        for order in orders_after:
            if order.get('id') == order_id:
                test_order_after = order
                break

        if not test_order_after:
            print(f"❌ Test order not found in filter results after editing")
            return False

        after_status = test_order_after.get('order_status')
        after_cancellation = test_order_after.get('cancellation_reason')

        print(f"📊 Filter service after edit:")
        print(f"   Status: {after_status}")
        print(f"   Cancellation: {after_cancellation}")
        print()

        # Step 6: Test status filtering
        print("🔍 Testing status filtering after edit...")

        # Test filter by CANCELLED status
        cancelled_filters = {
            'date_from': date_str,
            'date_to': date_str,
            'order_status': ['CANCELLED'],
            'page': 1,
            'per_page': 100
        }

        cancelled_result = filter_service.apply_filters(cancelled_filters)

        if cancelled_result.get('success'):
            cancelled_orders = cancelled_result.get('orders', [])
            found_in_cancelled = any(order.get('id') == order_id for order in cancelled_orders)
            print(f"   Found in CANCELLED filter: {'✅' if found_in_cancelled else '❌'}")
        else:
            print(f"   ❌ CANCELLED filter failed: {cancelled_result}")
            found_in_cancelled = False

        # Test filter by original status
        original_filters = {
            'date_from': date_str,
            'date_to': date_str,
            'order_status': [original_status],
            'page': 1,
            'per_page': 100
        }

        original_result = filter_service.apply_filters(original_filters)

        if original_result.get('success'):
            original_orders = original_result.get('orders', [])
            found_in_original = any(order.get('id') == order_id for order in original_orders)
            print(f"   Found in {original_status} filter: {'❌ INCORRECTLY' if found_in_original else '✅ CORRECTLY EXCLUDED'}")
        else:
            print(f"   ❌ {original_status} filter failed: {original_result}")
            found_in_original = True  # Assume failure means it's still there

        # Results
        status_updated = after_status == 'CANCELLED'
        cancellation_updated = after_cancellation == 'Filter Service Test Cancellation'

        print(f"\n🎯 FILTER SERVICE TEST RESULTS:")
        print(f"   Status Update: {'✅ CORRECT' if status_updated else '❌ STALE'}")
        print(f"   Cancellation Update: {'✅ CORRECT' if cancellation_updated else '❌ STALE'}")
        print(f"   Status Filtering: {'✅ WORKING' if found_in_cancelled and not found_in_original else '❌ BROKEN'}")

        all_correct = status_updated and cancellation_updated and found_in_cancelled and not found_in_original

        print(f"\n🏁 FILTER SERVICE TEST: {'✅ PASSED' if all_correct else '❌ FAILED'}")

        if not all_correct:
            print("\n🔧 Issues Found:")
            if not status_updated:
                print(f"   - Status not updated: expected 'CANCELLED', got '{after_status}'")
            if not cancellation_updated:
                print(f"   - Cancellation not updated: expected 'Filter Service Test Cancellation', got '{after_cancellation}'")
            if not found_in_cancelled:
                print("   - Order not found in CANCELLED status filter")
            if found_in_original:
                print(f"   - Order still found in {original_status} filter (should be excluded)")

        return all_correct

if __name__ == "__main__":
    success = test_filter_service()
    print(f"\n{'='*60}")
    print(f"FILTER SERVICE: {'✅ PASSED' if success else '❌ FAILED'}")
    exit(0 if success else 1)