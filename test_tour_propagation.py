#!/usr/bin/env python3
"""
Test Tour Field Propagation
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8081"
TEST_USER = "PropagationTest"

def test_tour_field_propagation():
    """Test that tour field changes propagate to linked orders"""
    print("🔄 Testing Tour Field Propagation...")

    # Get available tours
    response = requests.get(f"{BASE_URL}/api/tours", timeout=10)
    if response.status_code != 200:
        print(f"   ❌ Failed to get tours: {response.status_code}")
        return False

    tours_data = response.json()
    if not tours_data.get('success') or not tours_data.get('tours'):
        print("   ❌ No tours found")
        return False

    # Find a tour with linked orders
    test_tour = None
    for tour in tours_data['tours']:
        # Get orders for this tour to see if it has any
        for i in range(7):
            test_date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            try:
                orders_response = requests.get(f"{BASE_URL}/api/orders?date={test_date}", timeout=10)
                if orders_response.status_code == 200:
                    orders_data = orders_response.json()
                    if orders_data.get('orders'):
                        # Check if any orders belong to this tour
                        linked_orders = [o for o in orders_data['orders'] if o.get('tour_id') == tour['tour_id']]
                        if linked_orders:
                            test_tour = tour
                            print(f"   📋 Found tour with {len(linked_orders)} linked orders: {tour['tour_id']}")
                            break
            except:
                continue
        if test_tour:
            break

    if not test_tour:
        print("   ❌ No tour with linked orders found")
        return False

    tour_id = test_tour['tour_id']

    # Remember the original values
    original_rider = test_tour.get('rider_name', 'Original Rider')
    original_vehicle = test_tour.get('vehicle_registration', 'ORIGINAL-REG')

    # Test 1: Update tour fields
    print("   1️⃣ Updating tour fields...")
    new_rider_name = f"PROPAGATION_TEST_{datetime.now().strftime('%H%M%S')}"
    new_vehicle_reg = f"PROP-TEST-{datetime.now().strftime('%H%M%S')}"

    edit_data = {
        "modified_by": TEST_USER,
        "data": {
            "rider_name": new_rider_name,
            "vehicle_registration": new_vehicle_reg
        },
        "propagate_to_orders": True
    }

    response = requests.put(f"{BASE_URL}/api/tours/{tour_id}/edit", json=edit_data, timeout=10)
    if response.status_code != 200:
        print(f"   ❌ Failed to update tour: {response.status_code} - {response.text}")
        return False

    result = response.json()
    if not result.get('success'):
        print(f"   ❌ Tour update failed: {result.get('error')}")
        return False

    print(f"   ✅ Tour updated successfully! Propagated to {result.get('propagated_orders', 0)} orders")

    # Test 2: Verify propagation by checking linked orders
    print("   2️⃣ Verifying propagation in linked orders...")

    # Wait a moment for database to be updated
    import time
    time.sleep(1)

    verified_orders = 0
    for i in range(7):
        test_date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        try:
            orders_response = requests.get(f"{BASE_URL}/api/orders?date={test_date}", timeout=10)
            if orders_response.status_code == 200:
                orders_data = orders_response.json()
                if orders_data.get('orders'):
                    # Check linked orders
                    for order in orders_data['orders']:
                        if order.get('tour_id') == tour_id:
                            order_rider = order.get('rider_name', '')
                            order_vehicle = order.get('vehicle_registration', '')

                            if order_rider == new_rider_name and order_vehicle == new_vehicle_reg:
                                verified_orders += 1
                                print(f"      ✅ Order {order['id']} updated with new tour data")
                            else:
                                print(f"      ⚠️ Order {order['id']} not updated:")
                                print(f"         Rider: {order_rider} (expected: {new_rider_name})")
                                print(f"         Vehicle: {order_vehicle} (expected: {new_vehicle_reg})")
        except:
            continue

    if verified_orders > 0:
        print(f"   ✅ Successfully verified propagation in {verified_orders} orders")
        return True
    else:
        print("   ❌ No orders found with propagated changes")
        return False

def main():
    """Run tour propagation test"""
    print("🧪 TOUR FIELD PROPAGATION TEST")
    print("=" * 40)

    # Check connectivity
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print("✅ Server connectivity: OK")
    except Exception as e:
        print(f"❌ Server connectivity failed: {e}")
        return False

    if test_tour_field_propagation():
        print("\n🎉 TOUR PROPAGATION TEST PASSED!")
        print("✨ Tour field changes successfully propagate to linked orders")
        return True
    else:
        print("\n❌ TOUR PROPAGATION TEST FAILED!")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)