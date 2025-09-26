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
        url = f"http://localhost:8081/api/orders/{order_id}/transactions/edit"

        response = requests.put(
            url,
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )

        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Content: {response.text}")

        assert response.status_code == 200, f"HTTP {response.status_code}: {response.text}"

        result = response.json()
        assert result.get('success'), f"Transaction editing failed: {result.get('error')}"

        print("✅ Transaction editing test PASSED!")
        print(f"Message: {result.get('message')}")
        print(f"Updated items: {result.get('updated_items')}")

    except Exception as e:
        assert False, f"Transaction editing test failed with exception: {e}"

if __name__ == '__main__':
    print("=== Transaction Editing Test ===")
    success = test_transaction_editing()
    print(f"\nTest Result: {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
