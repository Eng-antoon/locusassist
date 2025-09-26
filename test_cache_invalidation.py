#!/usr/bin/env python3
"""
Test Cache Invalidation Fix
Tests that the filter service cache is properly invalidated after edits
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

def test_cache_invalidation():
    """Test that the filter service cache is invalidated after edits"""

    app = create_app()
    editing_service = EditingService()

    with app.app_context():
        print("🗑️  Testing Filter Cache Invalidation Fix")
        print("=" * 60)

        # Step 1: Find orders and ensure we have data to work with
        test_orders = Order.query.limit(5).all()
        if len(test_orders) < 2:
            print("❌ Need at least 2 orders for testing")
            return False

        # Use the first available order
        test_order = test_orders[0]
        order_id = test_order.id
        original_status = test_order.order_status
        date_str = str(test_order.date)

        print(f"📋 Test Order: {order_id}")
        print(f"📋 Original Status: {original_status}")
        print(f"📋 Date: {date_str}")
        print()

        # Step 2: Check filter service cache state
        print("🔍 Checking filter service cache state...")
        print(f"   Cache entries before: {len(filter_service._filter_cache)}")

        # Step 3: Create a cache entry by calling filter service
        filters_initial = {
            'date_from': date_str,
            'date_to': date_str,
            'page': 1,
            'per_page': 10
        }

        result_initial = filter_service.apply_filters(filters_initial)
        print(f"   Cache entries after first call: {len(filter_service._filter_cache)}")

        if not result_initial.get('success'):
            print(f"❌ Initial filter call failed: {result_initial}")
            return False

        print(f"   Initial filter result: {len(result_initial.get('orders', []))} orders")

        # Step 4: Make a manual edit that should invalidate cache
        print("\n✏️  Making manual edit to trigger cache invalidation...")

        new_status = 'CANCELLED' if original_status != 'CANCELLED' else 'COMPLETED'
        edit_result = editing_service.update_order_data(
            order_id=order_id,
            update_data={
                'order_status': new_status,
                'cancellation_reason': 'Cache invalidation test'
            },
            modified_by='test_cache_invalidation@example.com'
        )

        if not edit_result['success']:
            print(f"❌ Edit failed: {edit_result['error']}")
            return False

        print(f"✅ Edit successful - status changed to {new_status}")

        # Step 5: Check if cache was invalidated
        print(f"\n🗑️  Checking cache invalidation...")
        print(f"   Cache entries after edit: {len(filter_service._filter_cache)}")

        cache_invalidated = len(filter_service._filter_cache) == 0

        print(f"   Cache invalidation: {'✅ SUCCESS' if cache_invalidated else '❌ FAILED'}")

        # Step 6: Verify that subsequent filter calls get fresh data
        print(f"\n🔍 Testing fresh data retrieval...")

        result_after_edit = filter_service.apply_filters(filters_initial)

        if not result_after_edit.get('success'):
            print(f"❌ Filter call after edit failed: {result_after_edit}")
            return False

        # Check if the edited order shows the new status
        orders_after = result_after_edit.get('orders', [])
        test_order_after = None

        for order in orders_after:
            if order.get('id') == order_id:
                test_order_after = order
                break

        if test_order_after:
            after_status = test_order_after.get('order_status')
            data_fresh = after_status == new_status

            print(f"   Order found in results: ✅")
            print(f"   Status in results: {after_status}")
            print(f"   Data freshness: {'✅ FRESH' if data_fresh else '❌ STALE'}")
        else:
            print(f"   Order not found in results: ❌")
            data_fresh = False

        # Step 7: Test with status filter to ensure cache works correctly
        print(f"\n🔍 Testing status filtering with fresh cache...")

        status_filters = {
            'date_from': date_str,
            'date_to': date_str,
            'order_status': [new_status],
            'page': 1,
            'per_page': 100
        }

        status_result = filter_service.apply_filters(status_filters)

        if status_result.get('success'):
            status_orders = status_result.get('orders', [])
            found_in_status_filter = any(order.get('id') == order_id for order in status_orders)
            print(f"   Found in {new_status} filter: {'✅' if found_in_status_filter else '❌'}")
        else:
            print(f"   Status filter failed: {status_result}")
            found_in_status_filter = False

        # Results
        all_tests_passed = cache_invalidated and data_fresh and found_in_status_filter

        print(f"\n🎯 CACHE INVALIDATION TEST RESULTS:")
        print(f"   Cache Invalidation: {'✅ PASS' if cache_invalidated else '❌ FAIL'}")
        print(f"   Fresh Data Retrieval: {'✅ PASS' if data_fresh else '❌ FAIL'}")
        print(f"   Status Filter Accuracy: {'✅ PASS' if found_in_status_filter else '❌ FAIL'}")

        print(f"\n🏁 CACHE INVALIDATION TEST: {'✅ PASSED' if all_tests_passed else '❌ FAILED'}")

        if not all_tests_passed:
            print("\n🔧 Issues Found:")
            if not cache_invalidated:
                print("   - Filter cache was not invalidated after edit")
            if not data_fresh:
                print(f"   - Data is stale: expected status '{new_status}', got '{after_status if test_order_after else 'order not found'}'")
            if not found_in_status_filter:
                print(f"   - Order not found in {new_status} status filter")

        return all_tests_passed

if __name__ == "__main__":
    success = test_cache_invalidation()
    print(f"\n{'='*60}")
    print(f"CACHE INVALIDATION: {'✅ PASSED' if success else '❌ FAILED'}")
    exit(0 if success else 1)