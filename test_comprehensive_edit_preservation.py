#!/usr/bin/env python3
"""
Comprehensive Edit Preservation Test
Tests the complete workflow that was causing data loss and verifies the fix
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

def test_comprehensive_edit_preservation():
    """Comprehensive test of edit preservation during all refresh operations"""

    app = create_app()
    editing_service = EditingService()
    locus_auth = LocusAuth({})

    with app.app_context():
        print("🚀 COMPREHENSIVE EDIT PRESERVATION TEST")
        print("=" * 60)
        print("Testing the complete user workflow that was causing data loss")
        print()

        # Step 1: Setup test data - find orders and tours
        test_orders = Order.query.limit(3).all()
        test_tour = Tour.query.first()

        if len(test_orders) < 2 or not test_tour:
            print("❌ Insufficient test data found")
            return False

        order_1, order_2 = test_orders[0], test_orders[1]
        date_str = str(order_1.date)

        print(f"📋 Test Setup:")
        print(f"   Order 1: {order_1.id}")
        print(f"   Order 2: {order_2.id}")
        print(f"   Tour: {test_tour.tour_id}")
        print(f"   Date: {date_str}")
        print()

        # Step 2: User makes manual edits to orders
        print("👤 USER ACTION: Manual edits to orders...")

        edit_1 = editing_service.update_order_data(
            order_id=order_1.id,
            update_data={
                'vehicle_registration': 'USER-EDIT-VEHICLE-1',
                'rider_name': 'User Edited Rider 1',
                'location_city': 'User Edited City 1'
            },
            modified_by='user@company.com'
        )

        edit_2 = editing_service.update_order_data(
            order_id=order_2.id,
            update_data={
                'vehicle_registration': 'USER-EDIT-VEHICLE-2',
                'cancellation_reason': 'User manual edit reason'
            },
            modified_by='user@company.com'
        )

        if not edit_1['success'] or not edit_2['success']:
            print("❌ Manual edits failed")
            return False

        print("✅ Manual edits completed successfully")

        # Step 3: User makes manual edits to a tour with propagation
        print("\n👤 USER ACTION: Manual edit to tour with propagation...")

        tour_edit = editing_service.update_tour_data(
            tour_id=test_tour.tour_id,
            update_data={
                'vehicle_registration': 'USER-EDIT-TOUR-VEHICLE',
                'rider_name': 'User Edited Tour Rider'
            },
            modified_by='user@company.com',
            propagate_to_orders=True
        )

        if not tour_edit['success']:
            print("❌ Tour edit failed")
            return False

        print(f"✅ Tour edit completed - propagated to {tour_edit.get('propagated_orders', 0)} orders")

        # Step 4: Record current state
        db.session.refresh(order_1)
        db.session.refresh(order_2)
        db.session.refresh(test_tour)

        state_before_refresh = {
            'order_1': {
                'vehicle_registration': order_1.vehicle_registration,
                'rider_name': order_1.rider_name,
                'location_city': order_1.location_city,
                'is_modified': order_1.is_modified
            },
            'order_2': {
                'vehicle_registration': order_2.vehicle_registration,
                'cancellation_reason': order_2.cancellation_reason,
                'is_modified': order_2.is_modified
            },
            'tour': {
                'vehicle_registration': test_tour.vehicle_registration,
                'rider_name': test_tour.rider_name,
                'is_modified': test_tour.is_modified
            }
        }

        print("\n📊 State before refresh:")
        for entity, data in state_before_refresh.items():
            print(f"   {entity}: {data}")

        # Step 5: USER CLICKS REFRESH BUTTON (the problem scenario)
        print("\n🔄 USER ACTION: Clicks refresh button (force refresh)...")
        print("   This was previously causing data loss!")

        # This simulates the full refresh_orders_force_fresh workflow
        try:
            # Step 5.1: Clear cache (preserve manual edits)
            cache_clear_result = locus_auth.clear_orders_cache('illa-frontdoor', date_str)
            print(f"   Cache clear result: {'✅' if cache_clear_result else '❌'}")

            # Step 5.2: Check if our edits survived cache clearing
            surviving_order_1 = Order.query.filter_by(id=order_1.id).first()
            surviving_order_2 = Order.query.filter_by(id=order_2.id).first()
            surviving_tour = Tour.query.filter_by(tour_id=test_tour.tour_id).first()

            cache_clear_preservation = (
                surviving_order_1 and surviving_order_1.is_modified and
                surviving_order_2 and surviving_order_2.is_modified and
                surviving_tour and surviving_tour.is_modified
            )

            print(f"   Edit preservation after cache clear: {'✅' if cache_clear_preservation else '❌'}")

            # Step 5.3: Simulate fresh API data caching
            mock_fresh_data = {
                'orders': [
                    {
                        'id': order_1.id,
                        'orderStatus': 'EXECUTING',
                        'location': {
                            'name': 'Fresh API Location 1',
                            'address': {
                                'formattedAddress': 'Fresh API Address 1',
                                'city': 'Fresh API City 1',
                                'countryCode': 'US'
                            }
                        },
                        'orderMetadata': {
                            'tourDetail': {
                                'tourId': order_1.tour_id,
                                'riderName': 'Fresh API Rider 1',
                                'vehicleRegistrationNumber': 'FRESH-API-VEHICLE-1'
                            }
                        },
                        'rider_name': 'Fresh API Direct Rider 1',
                        'vehicle_registration': 'FRESH-API-DIRECT-VEHICLE-1'
                    },
                    {
                        'id': order_2.id,
                        'orderStatus': 'CANCELLED',
                        'location': {
                            'name': 'Fresh API Location 2',
                            'address': {
                                'formattedAddress': 'Fresh API Address 2',
                                'city': 'Fresh API City 2',
                                'countryCode': 'IN'
                            }
                        },
                        'orderMetadata': {
                            'tourDetail': {
                                'tourId': order_2.tour_id,
                                'riderName': 'Fresh API Rider 2',
                                'vehicleRegistrationNumber': 'FRESH-API-VEHICLE-2'
                            }
                        },
                        'rider_name': 'Fresh API Direct Rider 2',
                        'vehicle_registration': 'FRESH-API-DIRECT-VEHICLE-2',
                        'cancellation_reason': 'Fresh API cancellation reason'
                    }
                ],
                'totalCount': 2
            }

            cache_result = locus_auth.cache_orders_to_database(
                mock_fresh_data,
                'illa-frontdoor',
                date_str
            )

            print(f"   Fresh data caching result: {'✅' if cache_result else '❌'}")

        except Exception as e:
            print(f"❌ Refresh simulation failed: {e}")
            return False

        # Step 6: Final verification - check if ALL edits survived
        print("\n🔍 FINAL VERIFICATION - checking if all user edits survived...")

        final_order_1 = Order.query.filter_by(id=order_1.id).first()
        final_order_2 = Order.query.filter_by(id=order_2.id).first()
        final_tour = Tour.query.filter_by(tour_id=test_tour.tour_id).first()

        # Define what we expect to be preserved
        expected_preservations = {
            'order_1_vehicle': ('USER-EDIT-VEHICLE-1', final_order_1.vehicle_registration if final_order_1 else None),
            'order_1_rider': ('User Edited Rider 1', final_order_1.rider_name if final_order_1 else None),
            'order_1_city': ('User Edited City 1', final_order_1.location_city if final_order_1 else None),
            'order_2_vehicle': ('USER-EDIT-VEHICLE-2', final_order_2.vehicle_registration if final_order_2 else None),
            'order_2_cancellation': ('User manual edit reason', final_order_2.cancellation_reason if final_order_2 else None),
            'tour_vehicle': ('USER-EDIT-TOUR-VEHICLE', final_tour.vehicle_registration if final_tour else None),
            'tour_rider': ('User Edited Tour Rider', final_tour.rider_name if final_tour else None),
        }

        preservation_results = {}
        all_preserved = True

        print("\n📊 Preservation Results:")
        for field, (expected, actual) in expected_preservations.items():
            preserved = expected == actual
            preservation_results[field] = preserved
            if not preserved:
                all_preserved = False

            status = '✅ PRESERVED' if preserved else '❌ LOST'
            print(f"   {field}: {status}")
            if not preserved:
                print(f"      Expected: {expected}")
                print(f"      Actual: {actual}")

        # Step 7: Test propagated changes preservation
        print("\n🔍 Checking propagated changes preservation...")

        # Find an order that should have received tour propagation
        propagated_orders = Order.query.filter_by(tour_id=test_tour.tour_id).filter(Order.id != order_1.id, Order.id != order_2.id).limit(2).all()

        propagation_preserved = True
        if propagated_orders:
            for porder in propagated_orders:
                if porder.is_modified and porder.vehicle_registration == 'USER-EDIT-TOUR-VEHICLE':
                    print(f"   ✅ Propagated edit preserved in order {porder.id}")
                else:
                    print(f"   ❌ Propagated edit lost in order {porder.id}")
                    propagation_preserved = False
        else:
            print("   ⚠️  No propagated orders found to test")

        # Final summary
        tests_passed = all_preserved and propagation_preserved

        print(f"\n🎯 COMPREHENSIVE TEST SUMMARY:")
        print(f"   Manual Order Edits: {'✅ PRESERVED' if all_preserved else '❌ SOME LOST'}")
        print(f"   Tour Propagated Edits: {'✅ PRESERVED' if propagation_preserved else '❌ LOST'}")
        print(f"   Cache Clear Protection: {'✅ WORKING' if cache_clear_preservation else '❌ FAILED'}")

        print(f"\n🏁 FINAL RESULT: {'✅ ALL TESTS PASSED' if tests_passed else '❌ SOME TESTS FAILED'}")

        if not tests_passed:
            print("\n🔧 FAILED ITEMS:")
            for field, preserved in preservation_results.items():
                if not preserved:
                    expected, actual = expected_preservations[field]
                    print(f"   - {field}: expected '{expected}', got '{actual}'")

        return tests_passed

if __name__ == "__main__":
    success = test_comprehensive_edit_preservation()
    print(f"\n{'='*60}")
    print(f"COMPREHENSIVE EDIT PRESERVATION: {'✅ PASSED' if success else '❌ FAILED'}")
    exit(0 if success else 1)