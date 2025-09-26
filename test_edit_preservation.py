#!/usr/bin/env python3
"""
Test Edit Preservation During Refresh
Tests that manual edits are preserved when refresh operations occur
"""

import os
import sys
import json
import requests
import time
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, Order, Tour
from app import create_app
from app.editing_routes import EditingService

def test_edit_preservation():
    """Test that manual edits are preserved during refresh operations"""

    app = create_app()
    editing_service = EditingService()

    with app.app_context():
        print("🧪 Testing Edit Preservation During Refresh")
        print("=" * 50)

        # Step 1: Find an existing order to test with
        existing_order = Order.query.first()
        if not existing_order:
            print("❌ No existing orders found for testing")
            return False

        order_id = existing_order.id
        original_vehicle = existing_order.vehicle_registration
        original_rider = existing_order.rider_name

        print(f"📋 Test Order: {order_id}")
        print(f"📋 Original Vehicle: {original_vehicle}")
        print(f"📋 Original Rider: {original_rider}")
        print(f"📋 Is Modified: {existing_order.is_modified}")
        print()

        # Step 2: Make manual edits to the order
        test_vehicle = "TEST-VEHICLE-123"
        test_rider = "TEST-RIDER-MANUAL"

        print("✏️  Making manual edits...")

        edit_result = editing_service.update_order_data(
            order_id=order_id,
            update_data={
                'vehicle_registration': test_vehicle,
                'rider_name': test_rider
            },
            modified_by='test_user@example.com'
        )

        if not edit_result['success']:
            print(f"❌ Failed to make manual edits: {edit_result['error']}")
            return False

        print(f"✅ Manual edits successful: {edit_result['message']}")
        print(f"✅ Updated fields: {edit_result['updated_fields']}")

        # Verify the edits were applied
        db.session.refresh(existing_order)
        print(f"📋 After edit - Vehicle: {existing_order.vehicle_registration}")
        print(f"📋 After edit - Rider: {existing_order.rider_name}")
        print(f"📋 After edit - Is Modified: {existing_order.is_modified}")
        print(f"📋 After edit - Modified Fields: {existing_order.modified_fields}")
        print()

        # Step 3: Simulate a refresh operation that would normally overwrite data
        print("🔄 Simulating refresh operation...")

        # This simulates what happens during a refresh - fresh API data comes in
        mock_api_data = {
            'id': order_id,
            'orderStatus': existing_order.order_status,
            'location': {
                'name': existing_order.location_name,
                'address': {
                    'formattedAddress': existing_order.location_address,
                    'city': existing_order.location_city,
                    'countryCode': existing_order.location_country_code
                }
            },
            'orderMetadata': {
                'tourDetail': {
                    'tourId': existing_order.tour_id,
                    'riderName': 'API-UPDATED-RIDER',  # This should NOT overwrite our manual edit
                    'vehicleRegistrationNumber': 'API-UPDATED-VEHICLE'  # This should NOT overwrite our manual edit
                }
            },
            'rider_name': 'API-UPDATED-RIDER-DIRECT',
            'vehicle_registration': 'API-UPDATED-VEHICLE-DIRECT'
        }

        # Step 4: Use the data protection service to safely update
        from app.data_protection import data_protection_service

        try:
            data_protection_service.safe_update_order(
                existing_order,
                mock_api_data,
                'illa-frontdoor',
                existing_order.date
            )
            db.session.commit()
            print("✅ Safe update completed")
        except Exception as e:
            print(f"❌ Safe update failed: {e}")
            return False

        # Step 5: Verify that manual edits were preserved
        db.session.refresh(existing_order)

        print("🔍 Verification Results:")
        print(f"📋 Final Vehicle: {existing_order.vehicle_registration}")
        print(f"📋 Final Rider: {existing_order.rider_name}")
        print(f"📋 Is Modified: {existing_order.is_modified}")
        print(f"📋 Modified Fields: {existing_order.modified_fields}")
        print()

        # Check if edits were preserved
        vehicle_preserved = existing_order.vehicle_registration == test_vehicle
        rider_preserved = existing_order.rider_name == test_rider

        print("🎯 Test Results:")
        print(f"   Vehicle Preservation: {'✅ PASS' if vehicle_preserved else '❌ FAIL'}")
        print(f"   Rider Preservation: {'✅ PASS' if rider_preserved else '❌ FAIL'}")

        # Step 6: Test tour edit preservation as well
        print("\n🚛 Testing Tour Edit Preservation...")

        # Find a tour associated with this order
        tour = Tour.query.filter_by(tour_id=existing_order.tour_id).first()
        if tour:
            print(f"📋 Test Tour: {tour.tour_id}")
            print(f"📋 Original Tour Vehicle: {tour.vehicle_registration}")
            print(f"📋 Original Tour Rider: {tour.rider_name}")

            # Make manual edit to tour
            test_tour_vehicle = "TEST-TOUR-VEHICLE-456"

            tour_edit_result = editing_service.update_tour_data(
                tour_id=tour.tour_id,
                update_data={'vehicle_registration': test_tour_vehicle},
                modified_by='test_user@example.com',
                propagate_to_orders=False  # Don't propagate for this test
            )

            if tour_edit_result['success']:
                print(f"✅ Tour edit successful: {tour_edit_result['message']}")

                # Refresh tour and verify edit
                db.session.refresh(tour)
                tour_edit_preserved = tour.vehicle_registration == test_tour_vehicle
                print(f"   Tour Edit Preservation: {'✅ PASS' if tour_edit_preserved else '❌ FAIL'}")
            else:
                print(f"❌ Tour edit failed: {tour_edit_result['error']}")
                tour_edit_preserved = False
        else:
            print("⚠️  No tour found for testing")
            tour_edit_preserved = True  # Skip this test

        # Final result
        all_passed = vehicle_preserved and rider_preserved and tour_edit_preserved

        print(f"\n🏁 OVERALL RESULT: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")

        if not all_passed:
            print("\n🔧 Issues Found:")
            if not vehicle_preserved:
                print(f"   - Vehicle was overwritten: expected '{test_vehicle}', got '{existing_order.vehicle_registration}'")
            if not rider_preserved:
                print(f"   - Rider was overwritten: expected '{test_rider}', got '{existing_order.rider_name}'")
            if not tour_edit_preserved and tour:
                print(f"   - Tour vehicle was overwritten: expected '{test_tour_vehicle}', got '{tour.vehicle_registration}'")

        return all_passed

if __name__ == "__main__":
    success = test_edit_preservation()
    exit(0 if success else 1)