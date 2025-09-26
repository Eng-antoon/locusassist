#!/usr/bin/env python3
"""
Test Real API Endpoint
Tests the actual /api/orders endpoint that the frontend uses
"""

import os
import sys
import json
import requests
import time
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, Order
from app import create_app
from app.editing_routes import EditingService

def test_real_api_endpoint():
    """Test the actual API endpoint after making edits"""

    app = create_app()
    editing_service = EditingService()

    with app.app_context():
        print("🌐 Testing Real API Endpoint Response")
        print("=" * 50)

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

        # Step 2: Make manual edit
        print("✏️  Making manual edit...")

        edit_result = editing_service.update_order_data(
            order_id=order_id,
            update_data={
                'order_status': 'CANCELLED',
                'cancellation_reason': 'API Test Cancellation'
            },
            modified_by='test_api_endpoint@example.com'
        )

        if not edit_result['success']:
            print(f"❌ Edit failed: {edit_result['error']}")
            return False

        print(f"✅ Edit successful - status changed to CANCELLED")

        # Step 3: Check database directly
        db.session.refresh(test_order)
        print(f"📋 Database shows: {test_order.order_status}")
        print()

    # Step 4: Start the app and test the real API endpoint
    print("🚀 Starting Flask app...")

    # We'll test both with and without status filter
    test_cases = [
        {'params': f'?date={date_str}', 'description': 'All orders'},
        {'params': f'?date={date_str}&order_status=CANCELLED', 'description': 'Cancelled orders only'},
        {'params': f'?date={date_str}&order_status=COMPLETED', 'description': 'Completed orders only'}
    ]

    # Test the endpoints (assuming the app is running)
    base_url = "http://localhost:8081"  # Adjust port as needed

    for test_case in test_cases:
        url = f"{base_url}/api/orders{test_case['params']}"
        print(f"🔍 Testing: {test_case['description']}")
        print(f"   URL: {url}")

        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                orders = data.get('orders', [])

                # Find our test order
                test_order_found = False
                test_order_status = None

                for order in orders:
                    if order.get('id') == order_id:
                        test_order_found = True
                        test_order_status = order.get('orderStatus')
                        break

                print(f"   Response: {len(orders)} orders")
                print(f"   Test order found: {'✅' if test_order_found else '❌'}")
                if test_order_found:
                    print(f"   Test order status: {test_order_status} ({'✅' if test_order_status == 'CANCELLED' else '❌ STALE'}")
                print()

            else:
                print(f"   ❌ HTTP {response.status_code}: {response.text}")
                print()

        except requests.exceptions.ConnectionError:
            print(f"   ❌ Connection failed - is the server running on {base_url}?")
            print()
        except Exception as e:
            print(f"   ❌ Error: {e}")
            print()

    return True

if __name__ == "__main__":
    test_real_api_endpoint()