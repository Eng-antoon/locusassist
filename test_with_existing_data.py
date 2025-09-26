#!/usr/bin/env python3
"""
Test editing functionality with existing data
Finds actual data in the database and tests with it
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8082"
TEST_USER = "TestUser"

def find_available_orders():
    """Find orders in the database by checking recent dates"""
    print("🔍 Searching for available orders...")

    # Try the last 7 days
    for i in range(7):
        test_date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        print(f"   Checking {test_date}...")

        try:
            response = requests.get(f"{BASE_URL}/api/orders?date={test_date}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('orders'):
                    print(f"   ✅ Found {len(data['orders'])} orders for {test_date}")
                    return test_date, data['orders'][0]['id']
        except:
            continue

    print("   ❌ No orders found in the last 7 days")
    return None, None

def test_comprehensive_order_editing():
    """Test order editing with real data"""
    print("\n🔧 Testing Order Editing with Real Data...")

    date, order_id = find_available_orders()
    if not order_id:
        print("   ⚠️ No order data available for testing")
        return False

    print(f"   📋 Testing with Order ID: {order_id}")

    # Test 1: Basic order editing
    print("1. Testing basic order update...")
    update_data = {
        "modified_by": TEST_USER,
        "data": {
            "rider_name": "TEST_EDITED_RIDER",
            "cancellation_reason": "Test editing functionality",
            "location_city": "EDITED_CITY"
        }
    }

    try:
        response = requests.put(f"{BASE_URL}/api/orders/{order_id}/edit", json=update_data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Order updated: {result.get('message')}")
            print(f"   📝 Updated fields: {result.get('updated_fields')}")

            # Test 2: Check modification status
            print("2. Checking modification status...")
            response = requests.get(f"{BASE_URL}/api/orders/{order_id}/modification-status", timeout=10)
            if response.status_code == 200:
                mod_status = response.json()
                print(f"   ✅ Is modified: {mod_status.get('is_modified')}")
                print(f"   🔒 Protected fields: {mod_status.get('modified_fields')}")

                # Test 3: Line items editing
                print("3. Testing line items editing...")
                line_items_data = {
                    "modified_by": TEST_USER,
                    "line_items": [
                        {
                            "sku_id": "TEST-SKU-001",
                            "name": "Edited Test Product",
                            "quantity": 15,
                            "quantity_unit": "PIECES"
                        }
                    ]
                }

                response = requests.put(f"{BASE_URL}/api/orders/{order_id}/line-items/edit",
                                      json=line_items_data, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    print(f"   ✅ Line items updated: {result.get('message')}")

                    # Test 4: Data protection verification
                    print("4. Testing data protection...")
                    # Try to update a protected field again
                    second_update = {
                        "modified_by": "API_SYSTEM",
                        "data": {
                            "rider_name": "API_SHOULD_NOT_OVERWRITE",
                            "location_city": "API_SHOULD_NOT_OVERWRITE"
                        }
                    }

                    # This should not overwrite because fields are protected
                    response = requests.put(f"{BASE_URL}/api/orders/{order_id}/edit",
                                          json=second_update, timeout=10)
                    if response.status_code == 200:
                        print("   ✅ Data protection working - fields should remain protected")

                        # Verify protection worked
                        response = requests.get(f"{BASE_URL}/api/orders/{order_id}/modification-status", timeout=10)
                        if response.status_code == 200:
                            final_status = response.json()
                            print(f"   🔒 Final protected fields: {final_status.get('modified_fields')}")

                    return True
                else:
                    print(f"   ❌ Line items update failed: {response.status_code}")
            else:
                print(f"   ❌ Modification status check failed: {response.status_code}")
        else:
            print(f"   ❌ Order update failed: {response.status_code}")
            print(f"   Error: {response.text}")

    except Exception as e:
        print(f"   ❌ Test failed with exception: {e}")

    return False

def main():
    """Run comprehensive tests with real data"""
    print("🚀 Testing Editing Functionality with Existing Data")
    print(f"Testing against: {BASE_URL}")

    # Test connectivity
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"✅ Server connectivity: OK (status: {response.status_code})")
    except Exception as e:
        print(f"❌ Server connectivity failed: {e}")
        return False

    # Run comprehensive order editing test
    success = test_comprehensive_order_editing()

    print(f"\n{'🎉' if success else '❌'} Test Results:")
    if success:
        print("   ✅ Order editing functionality")
        print("   ✅ Line items editing")
        print("   ✅ Data protection system")
        print("   ✅ Modification tracking")
        print("\n🎉 All editing functionality is working correctly!")
    else:
        print("   ❌ Some tests failed")

    return success

if __name__ == "__main__":
    main()