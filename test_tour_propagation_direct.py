#!/usr/bin/env python3
"""
Direct Tour Propagation Test
Tests that tour edits still propagate correctly to orders after the fix
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

def test_tour_propagation_direct():
    """Test that tour edits propagate correctly to associated orders"""

    app = create_app()
    editing_service = EditingService()

    with app.app_context():
        print("🚛 Testing Tour Propagation After Edit Preservation Fix")
        print("=" * 60)

        # Step 1: Find a tour with associated orders
        tour_with_orders = None
        for tour in Tour.query.limit(10).all():
            orders = Order.query.filter_by(tour_id=tour.tour_id).all()
            if len(orders) >= 2:
                tour_with_orders = tour
                break

        if not tour_with_orders:
            print("❌ No tours with multiple orders found for testing")
            return False

        associated_orders = Order.query.filter_by(tour_id=tour_with_orders.tour_id).all()

        print(f"📋 Test Tour: {tour_with_orders.tour_id}")
        print(f"📋 Associated Orders: {len(associated_orders)}")
        print(f"📋 Tour Vehicle: {tour_with_orders.vehicle_registration}")
        print(f"📋 Tour Rider: {tour_with_orders.rider_name}")
        print()

        # Record original order values
        original_order_values = {}
        for order in associated_orders:
            original_order_values[order.id] = {
                'vehicle_registration': order.vehicle_registration,
                'rider_name': order.rider_name
            }

        # Step 2: Make edits to the tour with propagation enabled
        print("✏️  Making tour edits with propagation...")

        new_vehicle = 'TOUR-PROPAGATION-TEST-VEHICLE'
        new_rider = 'Tour Propagation Test Rider'

        edit_result = editing_service.update_tour_data(
            tour_id=tour_with_orders.tour_id,
            update_data={
                'vehicle_registration': new_vehicle,
                'rider_name': new_rider
            },
            modified_by='test_propagation@example.com',
            propagate_to_orders=True  # Enable propagation
        )

        if not edit_result['success']:
            print(f"❌ Tour edit failed: {edit_result['error']}")
            return False

        print(f"✅ Tour edit successful: {edit_result['message']}")
        print(f"✅ Updated fields: {edit_result['updated_fields']}")
        print(f"✅ Propagated orders: {edit_result.get('propagated_orders', 0)}")

        # Step 3: Verify propagation worked
        print("\n🔍 Verifying propagation...")

        # Refresh tour
        db.session.refresh(tour_with_orders)
        print(f"📋 Tour after edit - Vehicle: {tour_with_orders.vehicle_registration}")
        print(f"📋 Tour after edit - Rider: {tour_with_orders.rider_name}")

        # Check each associated order
        propagation_success = True
        for order in associated_orders:
            db.session.refresh(order)

            vehicle_propagated = order.vehicle_registration == new_vehicle
            rider_propagated = order.rider_name == new_rider

            print(f"📦 Order {order.id}:")
            print(f"   Vehicle: {order.vehicle_registration} ({'✅' if vehicle_propagated else '❌'})")
            print(f"   Rider: {order.rider_name} ({'✅' if rider_propagated else '❌'})")
            print(f"   Is Modified: {order.is_modified}")

            if not vehicle_propagated or not rider_propagated:
                propagation_success = False

        # Step 4: Test that propagated changes are also preserved during refresh
        print("\n🔄 Testing refresh preservation of propagated changes...")

        # Simulate a refresh for one of the orders
        test_order = associated_orders[0]

        # Mock API data that would try to overwrite our propagated changes
        mock_api_data = {
            'id': test_order.id,
            'orderStatus': test_order.order_status,
            'location': {
                'name': test_order.location_name,
                'address': {
                    'formattedAddress': test_order.location_address,
                    'city': test_order.location_city,
                    'countryCode': test_order.location_country_code
                }
            },
            'orderMetadata': {
                'tourDetail': {
                    'tourId': test_order.tour_id,
                    'riderName': 'API-OVERWRITE-RIDER',
                    'vehicleRegistrationNumber': 'API-OVERWRITE-VEHICLE'
                }
            },
            'rider_name': 'API-DIRECT-RIDER',
            'vehicle_registration': 'API-DIRECT-VEHICLE'
        }

        # Use data protection service
        from app.data_protection import data_protection_service

        try:
            data_protection_service.safe_update_order(
                test_order,
                mock_api_data,
                'illa-frontdoor',
                test_order.date
            )
            db.session.commit()
            print("✅ Safe update completed on propagated order")
        except Exception as e:
            print(f"❌ Safe update failed: {e}")
            return False

        # Verify propagated changes were preserved
        db.session.refresh(test_order)

        propagated_preserved = (test_order.vehicle_registration == new_vehicle and
                               test_order.rider_name == new_rider)

        print(f"📦 Propagated Order After Refresh:")
        print(f"   Vehicle: {test_order.vehicle_registration} (expected: {new_vehicle})")
        print(f"   Rider: {test_order.rider_name} (expected: {new_rider})")
        print(f"   Preservation: {'✅ PRESERVED' if propagated_preserved else '❌ LOST'}")

        # Final results
        all_tests_passed = propagation_success and propagated_preserved

        print(f"\n🎯 TOUR PROPAGATION TEST RESULTS:")
        print(f"   Initial Propagation: {'✅ PASSED' if propagation_success else '❌ FAILED'}")
        print(f"   Refresh Preservation: {'✅ PASSED' if propagated_preserved else '❌ FAILED'}")
        print(f"\n🏁 OVERALL RESULT: {'✅ ALL TESTS PASSED' if all_tests_passed else '❌ SOME TESTS FAILED'}")

        return all_tests_passed

if __name__ == "__main__":
    success = test_tour_propagation_direct()
    exit(0 if success else 1)