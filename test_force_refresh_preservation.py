#!/usr/bin/env python3
"""
Test Force Refresh Edit Preservation
Tests that manual edits are preserved during actual force refresh operations
This reproduces the real-world issue where users edit data and then refresh, losing edits
"""

import os
import sys
import json
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, Order, Tour
from app import create_app
from app.editing_routes import EditingService
from app.auth import LocusAuth

def test_force_refresh_preservation():
    """Test that manual edits are preserved during force refresh operations"""

    app = create_app()
    editing_service = EditingService()

    with app.app_context():
        print("🚨 Testing FORCE REFRESH Edit Preservation (Real World Scenario)")
        print("=" * 70)

        # Step 1: Find existing orders to test with
        existing_orders = Order.query.limit(3).all()
        if len(existing_orders) < 2:
            print("❌ Need at least 2 orders for comprehensive testing")
            return False

        # Use the first 2 orders for testing
        test_order_1 = existing_orders[0]
        test_order_2 = existing_orders[1]

        print(f"📋 Test Order 1: {test_order_1.id}")
        print(f"📋 Test Order 2: {test_order_2.id}")
        print(f"📋 Date: {test_order_1.date}")
        print()

        # Step 2: Make manual edits to both orders (different fields to test comprehensively)
        print("✏️  Making manual edits to test orders...")

        # Edit Order 1: Vehicle and Rider
        edit_result_1 = editing_service.update_order_data(
            order_id=test_order_1.id,
            update_data={
                'vehicle_registration': 'MANUAL-EDIT-VEHICLE-1',
                'rider_name': 'Manual Edited Rider 1'
            },
            modified_by='test_force_refresh@example.com'
        )

        # Edit Order 2: Different fields to test various protections
        edit_result_2 = editing_service.update_order_data(
            order_id=test_order_2.id,
            update_data={
                'vehicle_registration': 'MANUAL-EDIT-VEHICLE-2',
                'location_city': 'Manual Edited City',
                'cancellation_reason': 'Manual edit test reason'
            },
            modified_by='test_force_refresh@example.com'
        )

        if not edit_result_1['success'] or not edit_result_2['success']:
            print(f"❌ Failed to make manual edits")
            print(f"   Order 1: {edit_result_1}")
            print(f"   Order 2: {edit_result_2}")
            return False

        print(f"✅ Manual edits successful:")
        print(f"   Order 1: {edit_result_1['updated_fields']}")
        print(f"   Order 2: {edit_result_2['updated_fields']}")

        # Refresh order states to verify edits
        db.session.refresh(test_order_1)
        db.session.refresh(test_order_2)

        print(f"📋 Order 1 after edit - Vehicle: {test_order_1.vehicle_registration}, Rider: {test_order_1.rider_name}")
        print(f"📋 Order 2 after edit - Vehicle: {test_order_2.vehicle_registration}, City: {test_order_2.location_city}")
        print(f"📋 Order 1 is_modified: {test_order_1.is_modified}")
        print(f"📋 Order 2 is_modified: {test_order_2.is_modified}")
        print()

        # Step 3: Test the problematic force refresh that was causing data loss
        print("🔥 SIMULATING FORCE REFRESH (The Problem Scenario)...")
        print("   This simulates clicking 'Refresh' button which calls refresh_orders_force_fresh")

        # Create mock Locus auth with mock data
        locus_auth = LocusAuth({})

        # Mock the API response that would normally come from Locus
        mock_fresh_api_data = {
            'orders': [
                {
                    'id': test_order_1.id,
                    'orderStatus': 'COMPLETED',
                    'location': {
                        'name': 'API Updated Location 1',
                        'address': {
                            'formattedAddress': 'API Updated Address 1',
                            'city': 'API Updated City 1',
                            'countryCode': 'US'
                        }
                    },
                    'orderMetadata': {
                        'tourDetail': {
                            'tourId': test_order_1.tour_id,
                            'riderName': 'API Updated Rider 1',
                            'vehicleRegistrationNumber': 'API-UPDATED-VEHICLE-1'
                        }
                    },
                    'rider_name': 'API Direct Rider 1',
                    'vehicle_registration': 'API-DIRECT-VEHICLE-1'
                },
                {
                    'id': test_order_2.id,
                    'orderStatus': 'CANCELLED',
                    'location': {
                        'name': 'API Updated Location 2',
                        'address': {
                            'formattedAddress': 'API Updated Address 2',
                            'city': 'API Updated City 2',
                            'countryCode': 'IN'
                        }
                    },
                    'orderMetadata': {
                        'tourDetail': {
                            'tourId': test_order_2.tour_id,
                            'riderName': 'API Updated Rider 2',
                            'vehicleRegistrationNumber': 'API-UPDATED-VEHICLE-2'
                        }
                    },
                    'rider_name': 'API Direct Rider 2',
                    'vehicle_registration': 'API-DIRECT-VEHICLE-2',
                    'cancellation_reason': 'API provided cancellation reason'
                }
            ],
            'totalCount': 2
        }

        # Step 4: Simulate the cache clearing (the problem step)
        print("🗑️  Step 1: Cache clearing (this was deleting manual edits)...")
        cache_clear_success = locus_auth.clear_orders_cache('illa-frontdoor', str(test_order_1.date))

        if not cache_clear_success:
            print("❌ Cache clearing failed")
            return False

        # Check if our manually edited orders still exist
        remaining_order_1 = Order.query.filter_by(id=test_order_1.id).first()
        remaining_order_2 = Order.query.filter_by(id=test_order_2.id).first()

        print(f"   Order 1 after cache clear: {'✅ EXISTS' if remaining_order_1 else '❌ DELETED'}")
        print(f"   Order 2 after cache clear: {'✅ EXISTS' if remaining_order_2 else '❌ DELETED'}")

        if not remaining_order_1 or not remaining_order_2:
            print("❌ CRITICAL: Manually edited orders were deleted during cache clear!")
            return False

        # Verify edits are still preserved
        if (remaining_order_1.vehicle_registration == 'MANUAL-EDIT-VEHICLE-1' and
            remaining_order_2.vehicle_registration == 'MANUAL-EDIT-VEHICLE-2'):
            print("✅ EXCELLENT: Manual edits preserved after cache clear!")
        else:
            print("❌ FAILURE: Manual edits lost during cache clear!")
            return False

        # Step 5: Simulate caching fresh data (this should not overwrite our manual edits)
        print("📥 Step 2: Caching fresh API data (should preserve manual edits)...")

        cache_success = locus_auth.cache_orders_to_database(
            mock_fresh_api_data,
            'illa-frontdoor',
            str(test_order_1.date)
        )

        if not cache_success:
            print("❌ Caching fresh data failed")
            return False

        # Step 6: Final verification - check if edits survived the complete refresh
        db.session.refresh(remaining_order_1)
        db.session.refresh(remaining_order_2)

        print("\n🔍 FINAL VERIFICATION:")
        print(f"📋 Order 1 Final State:")
        print(f"   Vehicle: {remaining_order_1.vehicle_registration} (expected: MANUAL-EDIT-VEHICLE-1)")
        print(f"   Rider: {remaining_order_1.rider_name} (expected: Manual Edited Rider 1)")
        print(f"   Is Modified: {remaining_order_1.is_modified}")

        print(f"📋 Order 2 Final State:")
        print(f"   Vehicle: {remaining_order_2.vehicle_registration} (expected: MANUAL-EDIT-VEHICLE-2)")
        print(f"   City: {remaining_order_2.location_city} (expected: Manual Edited City)")
        print(f"   Cancellation: {remaining_order_2.cancellation_reason} (expected: Manual edit test reason)")
        print(f"   Is Modified: {remaining_order_2.is_modified}")

        # Check preservation results
        order_1_vehicle_preserved = remaining_order_1.vehicle_registration == 'MANUAL-EDIT-VEHICLE-1'
        order_1_rider_preserved = remaining_order_1.rider_name == 'Manual Edited Rider 1'
        order_2_vehicle_preserved = remaining_order_2.vehicle_registration == 'MANUAL-EDIT-VEHICLE-2'
        order_2_city_preserved = remaining_order_2.location_city == 'Manual Edited City'
        order_2_cancellation_preserved = remaining_order_2.cancellation_reason == 'Manual edit test reason'

        print("\n🎯 PRESERVATION TEST RESULTS:")
        print(f"   Order 1 Vehicle: {'✅ PRESERVED' if order_1_vehicle_preserved else '❌ LOST'}")
        print(f"   Order 1 Rider: {'✅ PRESERVED' if order_1_rider_preserved else '❌ LOST'}")
        print(f"   Order 2 Vehicle: {'✅ PRESERVED' if order_2_vehicle_preserved else '❌ LOST'}")
        print(f"   Order 2 City: {'✅ PRESERVED' if order_2_city_preserved else '❌ LOST'}")
        print(f"   Order 2 Cancellation: {'✅ PRESERVED' if order_2_cancellation_preserved else '❌ LOST'}")

        all_preserved = (order_1_vehicle_preserved and order_1_rider_preserved and
                        order_2_vehicle_preserved and order_2_city_preserved and
                        order_2_cancellation_preserved)

        print(f"\n🏁 FORCE REFRESH TEST RESULT: {'✅ ALL EDITS PRESERVED' if all_preserved else '❌ SOME EDITS LOST'}")

        if not all_preserved:
            print("\n🔧 FAILED PRESERVATIONS:")
            if not order_1_vehicle_preserved:
                print(f"   - Order 1 Vehicle: got '{remaining_order_1.vehicle_registration}' instead of 'MANUAL-EDIT-VEHICLE-1'")
            if not order_1_rider_preserved:
                print(f"   - Order 1 Rider: got '{remaining_order_1.rider_name}' instead of 'Manual Edited Rider 1'")
            if not order_2_vehicle_preserved:
                print(f"   - Order 2 Vehicle: got '{remaining_order_2.vehicle_registration}' instead of 'MANUAL-EDIT-VEHICLE-2'")
            if not order_2_city_preserved:
                print(f"   - Order 2 City: got '{remaining_order_2.location_city}' instead of 'Manual Edited City'")
            if not order_2_cancellation_preserved:
                print(f"   - Order 2 Cancellation: got '{remaining_order_2.cancellation_reason}' instead of 'Manual edit test reason'")

        return all_preserved

if __name__ == "__main__":
    success = test_force_refresh_preservation()
    print(f"\n{'='*70}")
    print(f"FORCE REFRESH EDIT PRESERVATION: {'✅ PASSED' if success else '❌ FAILED'}")
    exit(0 if success else 1)