#!/usr/bin/env python3
"""
Test script for the comprehensive editing functionality
Tests Tour and Order editing with data protection
"""

import requests
import json
import sys
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8082"
TEST_USER = "TestUser"

def test_api_endpoint(method, endpoint, data=None, files=None):
    """Test API endpoint and return response"""
    url = f"{BASE_URL}{endpoint}"

    try:
        if method.upper() == 'GET':
            response = requests.get(url, timeout=10)
        elif method.upper() == 'POST':
            if files:
                response = requests.post(url, data=data, files=files, timeout=10)
            else:
                response = requests.post(url, json=data, timeout=10)
        elif method.upper() == 'PUT':
            response = requests.put(url, json=data, timeout=10)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, timeout=10)
        else:
            return None

        return response

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def test_tour_editing():
    """Test tour editing functionality"""
    print("\n🔧 Testing Tour Editing...")

    # Test getting available tours first
    print("1. Getting tours list...")
    response = test_api_endpoint('GET', '/api/tours')
    if response and response.status_code == 200:
        tours_data = response.json()
        if tours_data.get('success') and tours_data.get('tours'):
            test_tour = tours_data['tours'][0]
            tour_id = test_tour['tour_id']
            print(f"   ✅ Found tour: {tour_id}")

            # Test tour editing
            print("2. Testing tour update...")
            update_data = {
                "modified_by": TEST_USER,
                "data": {
                    "rider_name": "Updated Rider Name",
                    "vehicle_registration": "TEST-123-EDIT"
                },
                "propagate_to_orders": True
            }

            response = test_api_endpoint('PUT', f'/api/tours/{tour_id}/edit', update_data)
            if response and response.status_code == 200:
                result = response.json()
                print(f"   ✅ Tour updated successfully: {result.get('message')}")
                print(f"   📈 Propagated to {result.get('propagated_orders', 0)} orders")
                return tour_id
            else:
                print(f"   ❌ Tour update failed: {response.status_code if response else 'No response'}")
        else:
            print("   ❌ No tours found in response")
    else:
        print("   ❌ Failed to get tours list")

    return None

def test_order_editing():
    """Test order editing functionality"""
    print("\n🔧 Testing Order Editing...")

    # Test getting available orders first
    print("1. Getting orders list...")
    today = datetime.now().strftime("%Y-%m-%d")
    response = test_api_endpoint('GET', f'/api/orders?date={today}')

    if response and response.status_code == 200:
        orders_data = response.json()
        if orders_data.get('orders'):
            test_order = orders_data['orders'][0]
            order_id = test_order['id']
            print(f"   ✅ Found order: {order_id}")

            # Test order editing
            print("2. Testing order update...")
            update_data = {
                "modified_by": TEST_USER,
                "data": {
                    "order_status": "CANCELLED",
                    "cancellation_reason": "Test cancellation reason",
                    "rider_name": "Updated Rider for Order"
                }
            }

            response = test_api_endpoint('PUT', f'/api/orders/{order_id}/edit', update_data)
            if response and response.status_code == 200:
                result = response.json()
                print(f"   ✅ Order updated successfully: {result.get('message')}")

                # Test modification status check
                print("3. Checking modification status...")
                response = test_api_endpoint('GET', f'/api/orders/{order_id}/modification-status')
                if response and response.status_code == 200:
                    mod_status = response.json()
                    print(f"   ✅ Order is modified: {mod_status.get('is_modified')}")
                    print(f"   📝 Modified fields: {mod_status.get('modified_fields')}")
                else:
                    print("   ❌ Failed to get modification status")

                return order_id
            else:
                print(f"   ❌ Order update failed: {response.status_code if response else 'No response'}")
                if response:
                    print(f"   Error: {response.text}")
        else:
            print("   ❌ No orders found in response")
    else:
        print(f"   ❌ Failed to get orders list: {response.status_code if response else 'No response'}")

    return None

def test_line_items_editing(order_id):
    """Test line items editing functionality"""
    if not order_id:
        print("   ⚠️ Skipping line items test - no order ID")
        return

    print("\n🔧 Testing Line Items Editing...")

    # Test line items update
    line_items_data = {
        "modified_by": TEST_USER,
        "line_items": [
            {
                "sku_id": "TEST-SKU-001",
                "name": "Test Product 1",
                "quantity": 10,
                "quantity_unit": "PIECES"
            },
            {
                "sku_id": "TEST-SKU-002",
                "name": "Test Product 2",
                "quantity": 5,
                "quantity_unit": "BOXES"
            }
        ]
    }

    response = test_api_endpoint('PUT', f'/api/orders/{order_id}/line-items/edit', line_items_data)
    if response and response.status_code == 200:
        result = response.json()
        print(f"   ✅ Line items updated: {result.get('message')}")
        print(f"   📊 Results: {result.get('results')}")
    else:
        print(f"   ❌ Line items update failed: {response.status_code if response else 'No response'}")
        if response:
            print(f"   Error: {response.text}")

def test_data_protection(order_id):
    """Test data protection functionality"""
    if not order_id:
        print("   ⚠️ Skipping data protection test - no order ID")
        return

    print("\n🛡️ Testing Data Protection...")

    # First, modify an order to set protection flags
    print("1. Creating protected fields...")
    update_data = {
        "modified_by": TEST_USER,
        "data": {
            "rider_name": "PROTECTED_RIDER_NAME",
            "location_city": "PROTECTED_CITY"
        }
    }

    response = test_api_endpoint('PUT', f'/api/orders/{order_id}/edit', update_data)
    if response and response.status_code == 200:
        print("   ✅ Fields protected successfully")

        # Check that fields are now protected
        response = test_api_endpoint('GET', f'/api/orders/{order_id}/modification-status')
        if response and response.status_code == 200:
            mod_status = response.json()
            protected_fields = mod_status.get('modified_fields', [])
            print(f"   🔒 Protected fields: {protected_fields}")

            if 'rider_name' in protected_fields and 'location_city' in protected_fields:
                print("   ✅ Data protection system working correctly")
            else:
                print("   ❌ Data protection system may have issues")
        else:
            print("   ❌ Could not verify protection status")
    else:
        print(f"   ❌ Failed to create protected fields: {response.status_code if response else 'No response'}")

def main():
    """Run all tests"""
    print("🚀 Starting Comprehensive Editing Functionality Tests")
    print(f"Testing against: {BASE_URL}")

    # Wait a moment for the server to be ready
    time.sleep(2)

    try:
        # Test basic server connectivity
        print("\n🔍 Testing server connectivity...")
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code in [200, 302]:  # 302 for redirect is OK
            print("   ✅ Server is responding")
        else:
            print(f"   ❌ Server returned status {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"   ❌ Cannot connect to server: {e}")
        print("   Make sure the Flask app is running on port 8082")
        return False

    # Run tests
    tour_id = test_tour_editing()
    order_id = test_order_editing()
    test_line_items_editing(order_id)
    test_data_protection(order_id)

    print("\n📋 Test Summary:")
    print(f"   • Tour editing: {'✅ Tested' if tour_id else '❌ Failed'}")
    print(f"   • Order editing: {'✅ Tested' if order_id else '❌ Failed'}")
    print(f"   • Line items editing: {'✅ Tested' if order_id else '⚠️ Skipped'}")
    print(f"   • Data protection: {'✅ Tested' if order_id else '⚠️ Skipped'}")

    if tour_id and order_id:
        print("\n🎉 All core editing functionality is working!")
        return True
    else:
        print("\n⚠️ Some tests failed or were skipped")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)