#!/usr/bin/env python3
"""
Test Transaction Details Editing Functionality
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8083"
TEST_USER = "TransactionTest"

def test_transaction_editing():
    """Test transaction details editing"""
    print("🔄 Testing Transaction Details Editing...")

    # Find an order with line items
    for i in range(7):
        test_date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        try:
            response = requests.get(f"{BASE_URL}/api/orders?date={test_date}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('orders'):
                    for order in data['orders']:
                        # Check if order has line items with transaction details
                        if (order.get('orderMetadata', {}).get('lineItems') and
                            len(order['orderMetadata']['lineItems']) > 0):

                            order_id = order['id']
                            line_items = order['orderMetadata']['lineItems']

                            print(f"   📋 Testing order: {order_id} with {len(line_items)} line items")

                            # Create transaction updates
                            transactions = []
                            for item in line_items[:2]:  # Test first 2 items
                                transaction = {
                                    'id': item['id'],
                                    'ordered_quantity': 50,
                                    'transacted_quantity': 45,
                                    'transacted_weight': 12.5,
                                    'status': 'PARTIALLY_DELIVERED'
                                }
                                transactions.append(transaction)

                            # Update transactions
                            update_data = {
                                'modified_by': TEST_USER,
                                'transactions': transactions
                            }

                            response = requests.put(
                                f"{BASE_URL}/api/orders/{order_id}/transactions/edit",
                                json=update_data,
                                timeout=10
                            )

                            if response.status_code == 200:
                                result = response.json()
                                print(f"   ✅ Transaction details updated: {result.get('message')}")
                                print(f"   📊 Updated {result.get('updated_items')} transaction items")

                                # Verify the order is marked as modified
                                mod_response = requests.get(f"{BASE_URL}/api/orders/{order_id}/modification-status", timeout=10)
                                if mod_response.status_code == 200:
                                    mod_status = mod_response.json()
                                    if 'transaction_details' in mod_status.get('modified_fields', []):
                                        print("   ✅ Order properly marked with transaction modifications")
                                        return True
                                    else:
                                        print("   ⚠️ Order not marked with transaction modifications")
                                        return False
                                else:
                                    print(f"   ❌ Failed to check modification status: {mod_response.status_code}")
                                    return False
                            else:
                                print(f"   ❌ Transaction update failed: {response.status_code} - {response.text}")
                                return False

        except Exception as e:
            print(f"   ⚠️ Error testing date {test_date}: {e}")
            continue

    print("   ❌ No suitable orders found for transaction testing")
    return False

def test_ui_integration():
    """Test that the UI components are properly integrated"""
    print("🎨 Testing UI Integration...")

    # Test that an order detail page loads with editing features
    try:
        response = requests.get(f"{BASE_URL}/order/1704784160", timeout=10)
        if response.status_code == 200:
            print("   ✅ Order detail page loads successfully")

            # Check if the response contains our new editing features
            content = response.text
            if 'toggleTransactionEdit' in content:
                print("   ✅ Transaction editing JavaScript found")
            else:
                print("   ❌ Transaction editing JavaScript not found")
                return False

            if 'Edit Transactions' in content:
                print("   ✅ Edit Transactions button found")
            else:
                print("   ❌ Edit Transactions button not found")
                return False

            if 'saveTransactionDetails' in content:
                print("   ✅ Save transaction function found")
            else:
                print("   ❌ Save transaction function not found")
                return False

            return True
        else:
            print(f"   ❌ Order detail page failed to load: {response.status_code}")
            return False

    except Exception as e:
        print(f"   ❌ UI integration test failed: {e}")
        return False

def main():
    """Run transaction editing tests"""
    print("🧪 TRANSACTION EDITING TEST")
    print("=" * 40)

    # Check connectivity
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print("✅ Server connectivity: OK")
    except Exception as e:
        print(f"❌ Server connectivity failed: {e}")
        return False

    tests = [
        ("Transaction Details Editing", test_transaction_editing),
        ("UI Integration", test_ui_integration)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{'-' * 20} {test_name} {'-' * 20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")

    print(f"\n{'=' * 40}")
    print(f"📊 TEST RESULTS: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TRANSACTION TESTS PASSED!")
        return True
    else:
        print(f"⚠️ {total - passed} tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)