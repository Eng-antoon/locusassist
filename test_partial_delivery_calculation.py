#!/usr/bin/env python3
"""
Test Partial Delivery Calculation
Tests the new local partial delivery calculation logic
"""

import os
import sys
import json
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, Order, OrderLineItem
from app import create_app
from app.editing_routes import EditingService

def test_partial_delivery_calculation():
    """Test the local partial delivery calculation"""

    app = create_app()
    editing_service = EditingService()

    with app.app_context():
        print("🧮 Testing Partial Delivery Calculation")
        print("=" * 50)

        # Find an order with line items to test with
        test_order = Order.query.join(OrderLineItem).first()
        if not test_order:
            print("❌ No orders with line items found for testing")
            return False

        order_id = test_order.id
        print(f"📋 Test Order: {order_id}")
        print(f"📋 Original partially_delivered: {test_order.partially_delivered}")

        # Get line items
        line_items = OrderLineItem.query.filter_by(order_id=order_id).all()
        if not line_items:
            print("❌ No line items found")
            return False

        print(f"📋 Found {len(line_items)} line items")
        for i, item in enumerate(line_items[:3]):  # Show first 3 items
            print(f"   Item {i+1}: {item.sku_id} - ordered: {item.quantity}, transacted: {item.transacted_quantity}")

        # Test Case 1: Set all items as fully delivered
        print(f"\n🧪 Test Case 1: All items fully delivered")
        for item in line_items:
            item.transacted_quantity = item.quantity or 0

        calculated_status = editing_service.calculate_partial_delivery(test_order)
        print(f"   Result: {calculated_status} (Expected: False)")
        test1_passed = calculated_status == False

        # Test Case 2: Set some items as partially delivered
        print(f"\n🧪 Test Case 2: Some items partially delivered")
        if len(line_items) > 1:
            # Make first item partial, rest full
            line_items[0].transacted_quantity = (line_items[0].quantity or 0) // 2
            for item in line_items[1:]:
                item.transacted_quantity = item.quantity or 0
        else:
            # Single item - make it partial
            line_items[0].transacted_quantity = (line_items[0].quantity or 0) // 2

        calculated_status = editing_service.calculate_partial_delivery(test_order)
        print(f"   Result: {calculated_status} (Expected: True)")
        test2_passed = calculated_status == True

        # Test Case 3: Set all items as not delivered
        print(f"\n🧪 Test Case 3: No items delivered")
        for item in line_items:
            item.transacted_quantity = 0

        calculated_status = editing_service.calculate_partial_delivery(test_order)
        print(f"   Result: {calculated_status} (Expected: False)")
        test3_passed = calculated_status == False

        # Test Case 4: Set some items with partial quantities (0 < transacted < ordered)
        print(f"\n🧪 Test Case 4: Some items with partial quantities")
        for i, item in enumerate(line_items):
            if i % 2 == 0:
                # Even items: partial delivery
                item.transacted_quantity = max(1, (item.quantity or 0) // 3)
            else:
                # Odd items: no delivery
                item.transacted_quantity = 0

        calculated_status = editing_service.calculate_partial_delivery(test_order)
        print(f"   Result: {calculated_status} (Expected: True)")
        test4_passed = calculated_status == True

        # Test Case 5: Mix of full and no delivery
        print(f"\n🧪 Test Case 5: Mix of full delivery and no delivery")
        for i, item in enumerate(line_items):
            if i % 2 == 0:
                # Even items: full delivery
                item.transacted_quantity = item.quantity or 0
            else:
                # Odd items: no delivery
                item.transacted_quantity = 0

        calculated_status = editing_service.calculate_partial_delivery(test_order)
        expected = len(line_items) > 1  # Should be True if multiple items, False if single item
        print(f"   Result: {calculated_status} (Expected: {expected})")
        test5_passed = calculated_status == expected

        # Reset to original state (don't commit changes)
        db.session.rollback()

        # Results
        all_tests_passed = test1_passed and test2_passed and test3_passed and test4_passed and test5_passed

        print(f"\n🎯 PARTIAL DELIVERY CALCULATION TEST RESULTS:")
        print(f"   Test 1 (All Full): {'✅ PASS' if test1_passed else '❌ FAIL'}")
        print(f"   Test 2 (Some Partial): {'✅ PASS' if test2_passed else '❌ FAIL'}")
        print(f"   Test 3 (None Delivered): {'✅ PASS' if test3_passed else '❌ FAIL'}")
        print(f"   Test 4 (Partial Quantities): {'✅ PASS' if test4_passed else '❌ FAIL'}")
        print(f"   Test 5 (Mixed Full/None): {'✅ PASS' if test5_passed else '❌ FAIL'}")

        print(f"\n🏁 PARTIAL DELIVERY CALCULATION: {'✅ ALL PASSED' if all_tests_passed else '❌ SOME FAILED'}")

        return all_tests_passed

def test_transaction_update_integration():
    """Test the integration with transaction updates"""

    app = create_app()

    with app.app_context():
        print("\n🔄 Testing Transaction Update Integration")
        print("=" * 50)

        # Find an order with line items
        test_order = Order.query.join(OrderLineItem).first()
        if not test_order:
            print("❌ No orders with line items found")
            return False

        order_id = test_order.id
        original_status = test_order.partially_delivered

        print(f"📋 Test Order: {order_id}")
        print(f"📋 Original partially_delivered: {original_status}")

        # Get first line item
        line_item = OrderLineItem.query.filter_by(order_id=order_id).first()
        if not line_item:
            print("❌ No line items found")
            return False

        original_transacted = line_item.transacted_quantity or 0
        ordered_qty = line_item.quantity or 0

        print(f"📋 Line item: {line_item.sku_id} - ordered: {ordered_qty}, transacted: {original_transacted}")

        # Simulate transaction update (make it partial)
        new_transacted = max(1, ordered_qty // 2) if ordered_qty > 0 else 1

        # Create mock transaction data
        transaction_data = {
            'modified_by': 'test_partial_delivery@example.com',
            'transactions': [
                {
                    'id': line_item.sku_id,
                    'transacted_quantity': new_transacted
                }
            ]
        }

        # This would normally be called via API, but we'll simulate the logic
        from app.editing_routes import EditingService
        editing_service = EditingService()

        # Update the line item
        line_item.transacted_quantity = new_transacted

        # Recalculate partial delivery
        calculated_status = editing_service.calculate_partial_delivery(test_order)
        test_order.partially_delivered = calculated_status

        print(f"🔄 Updated transacted quantity to: {new_transacted}")
        print(f"🔄 Calculated partially_delivered: {calculated_status}")

        expected_partial = new_transacted < ordered_qty if ordered_qty > 0 else False
        integration_passed = calculated_status == expected_partial

        # Reset changes
        line_item.transacted_quantity = original_transacted
        test_order.partially_delivered = original_status
        db.session.rollback()

        print(f"\n🎯 INTEGRATION TEST RESULT:")
        print(f"   Expected partial delivery: {expected_partial}")
        print(f"   Calculated partial delivery: {calculated_status}")
        print(f"   Integration test: {'✅ PASS' if integration_passed else '❌ FAIL'}")

        return integration_passed

if __name__ == "__main__":
    success1 = test_partial_delivery_calculation()
    success2 = test_transaction_update_integration()

    overall_success = success1 and success2

    print(f"\n{'='*50}")
    print(f"OVERALL PARTIAL DELIVERY TESTS: {'✅ SUCCESS' if overall_success else '❌ FAILED'}")
    exit(0 if overall_success else 1)