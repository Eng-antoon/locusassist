#!/usr/bin/env python3
"""
Test script to verify transaction editing functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json

def test_transaction_editing():
    """Test the transaction editing API endpoint"""

    # Use the order ID from your error log
    order_id = "WA-250925"

    # Test data for transaction update
    test_data = {
        "modified_by": "Test Script",
        "transactions": [
            {
                "id": "4103020471001",
                "ordered_quantity": 10,
                "transacted_quantity": 8,
                "transacted_weight": 2.5,
                "status": "DELIVERED"
            },
            {
                "id": "4103020471002",
                "ordered_quantity": 5,
                "transacted_quantity": 5,
                "transacted_weight": 1.2,
                "status": "DELIVERED"
            }
        ]
    }

    print(f"Testing transaction editing for order: {order_id}")
    print(f"Test data: {json.dumps(test_data, indent=2)}")

    try:
        # Make the API request
        url = f"http://localhost:5000/api/orders/{order_id}/transactions/edit"

        response = requests.put(
            url,
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )

        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Content: {response.text}")

        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Transaction editing test PASSED!")
                print(f"Message: {result.get('message')}")
                print(f"Updated items: {result.get('updated_items')}")
                return True
            else:
                print("❌ Transaction editing test FAILED!")
                print(f"Error: {result.get('error')}")
                return False
        else:
            print("❌ Transaction editing test FAILED!")
            print(f"HTTP {response.status_code}: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Transaction editing test FAILED with exception: {e}")
        return False

if __name__ == '__main__':
    print("=== Transaction Editing Test ===")
    success = test_transaction_editing()
    print(f"\nTest Result: {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
