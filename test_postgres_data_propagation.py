#!/usr/bin/env python3
"""
Test script to verify data propagation from tours to orders (PostgreSQL)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.editing_routes import EditingService
from models import db, Tour, Order
from flask import Flask
import logging

def test_data_propagation():
    """Test that tour data properly propagates to orders and overrides old data"""

    print("Setting up test environment for PostgreSQL...")

    # Create Flask app for testing
    app = Flask(__name__)

    # Use PostgreSQL database
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:@localhost:5432/locus_assistant')
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # Set up logging to see detailed information
    logging.basicConfig(level=logging.INFO)

    with app.app_context():
        editing_service = EditingService()

        # Find a tour with orders to test
        tour = Tour.query.filter(Tour.total_orders > 0).first()

        if not tour:
            print("No tour with orders found for testing")
            # Let's create a test tour and order for testing
            return create_test_data_and_test(editing_service)

        print(f"Testing with tour: {tour.tour_id}")
        print(f"Original tour data:")
        print(f"  - rider_name: {tour.rider_name}")
        print(f"  - rider_id: {tour.rider_id}")
        print(f"  - vehicle_id: {tour.vehicle_id}")
        print(f"  - vehicle_registration: {tour.vehicle_registration}")
        print(f"  - rider_phone: {tour.rider_phone}")

        # Find orders linked to this tour
        orders = Order.query.filter(Order.tour_id == tour.tour_id).limit(3).all()

        if not orders:
            # Try finding orders by other methods
            orders = Order.query.filter(
                Order.rider_name == tour.rider_name,
                Order.vehicle_registration == tour.vehicle_registration
            ).limit(3).all()

        if not orders:
            print("No orders found linked to this tour")
            return create_test_data_and_test(editing_service)

        print(f"\nFound {len(orders)} orders linked to tour")

        # Show original order data
        for i, order in enumerate(orders):
            print(f"\nOrder {i+1} ({order.id}) original data:")
            print(f"  - rider_name: {order.rider_name}")
            print(f"  - rider_id: {order.rider_id}")
            print(f"  - vehicle_id: {order.vehicle_id}")
            print(f"  - vehicle_registration: {order.vehicle_registration}")
            print(f"  - rider_phone: {order.rider_phone}")

        # Test updating tour data
        test_update = {
            'rider_name': f'Updated Rider {tour.id}',
            'vehicle_id': f'VH-{tour.id}-TEST',
            'rider_phone': '+1234567890',
            'rider_id': f'RIDER-{tour.id}'
        }

        print(f"\nTesting update with data: {test_update}")

        # Perform the update
        result = editing_service.update_tour_data(
            tour_id=tour.tour_id,
            update_data=test_update,
            modified_by='Test Script',
            propagate_to_orders=True
        )

        print(f"\nUpdate result: {result}")

        if result['success']:
            # Refresh orders from database
            db.session.expire_all()
            updated_orders = Order.query.filter(Order.tour_id == tour.tour_id).limit(3).all()

            if not updated_orders:
                # Try alternative search again
                updated_orders = Order.query.filter(
                    Order.rider_name == test_update['rider_name']
                ).limit(3).all()

            print(f"\nAfter update - checking {len(updated_orders)} orders:")

            all_tests_passed = True
            for i, order in enumerate(updated_orders):
                print(f"\nOrder {i+1} ({order.id}) after update:")
                print(f"  - rider_name: {order.rider_name}")
                print(f"  - rider_id: {order.rider_id}")
                print(f"  - vehicle_id: {order.vehicle_id}")
                print(f"  - vehicle_registration: {order.vehicle_registration}")
                print(f"  - rider_phone: {order.rider_phone}")
                print(f"  - is_modified: {order.is_modified}")
                print(f"  - last_modified_by: {order.last_modified_by}")

                # Verify the data was propagated correctly
                if order.rider_name == test_update['rider_name']:
                    print(f"  ✓ rider_name updated correctly")
                else:
                    print(f"  ✗ rider_name NOT updated (expected: {test_update['rider_name']}, got: {order.rider_name})")
                    all_tests_passed = False

                if order.vehicle_id == test_update['vehicle_id']:
                    print(f"  ✓ vehicle_id updated correctly")
                else:
                    print(f"  ✗ vehicle_id NOT updated (expected: {test_update['vehicle_id']}, got: {order.vehicle_id})")
                    all_tests_passed = False

                if order.rider_phone == test_update['rider_phone']:
                    print(f"  ✓ rider_phone updated correctly")
                else:
                    print(f"  ✗ rider_phone NOT updated (expected: {test_update['rider_phone']}, got: {order.rider_phone})")
                    all_tests_passed = False

                if order.rider_id == test_update['rider_id']:
                    print(f"  ✓ rider_id updated correctly")
                else:
                    print(f"  ✗ rider_id NOT updated (expected: {test_update['rider_id']}, got: {order.rider_id})")
                    all_tests_passed = False

            print(f"\n{'🎉 ALL TESTS PASSED!' if all_tests_passed else '❌ SOME TESTS FAILED!'}")
            return all_tests_passed
        else:
            print(f"Update failed: {result}")
            return False

def create_test_data_and_test(editing_service):
    """Create test data if none exists"""
    print("\n🔧 Creating test data...")

    # This would create test data but we'll skip for now
    # since we want to test with real data
    print("⚠️ No existing data found for testing. Please run the application first to populate some data.")
    return False

if __name__ == '__main__':
    try:
        success = test_data_propagation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)