#!/usr/bin/env python3
"""
Test to verify that vehicle_id and rider_id are properly stored and displayed
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.editing_routes import EditingService
from models import db, Tour, Order
from flask import Flask
import logging

def test_vehicle_rider_propagation():
    """Test that vehicle_id and rider_id are properly stored and propagated"""

    print("Testing Vehicle ID and Rider ID propagation...")

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
            return False

        print(f"Testing with tour: {tour.tour_id}")

        # Find orders linked to this tour
        orders = Order.query.filter(Order.tour_id == tour.tour_id).limit(2).all()

        if not orders:
            print("No orders found linked to this tour")
            return False

        print(f"\nBefore update:")
        print(f"Tour data:")
        print(f"  - vehicle_id: {tour.vehicle_id}")
        print(f"  - rider_id: {tour.rider_id}")

        for i, order in enumerate(orders):
            print(f"\nOrder {i+1} ({order.id}):")
            print(f"  - vehicle_id: {order.vehicle_id}")
            print(f"  - rider_id: {order.rider_id}")

        # Test updating tour with specific vehicle_id and rider_id
        test_update = {
            'vehicle_id': f'VH-TEST-{tour.id}',
            'rider_id': f'RIDER-TEST-{tour.id}'
        }

        print(f"\nTesting update with data: {test_update}")

        # Perform the update with propagation
        result = editing_service.update_tour_data(
            tour_id=tour.tour_id,
            update_data=test_update,
            modified_by='Vehicle Rider Test Script',
            propagate_to_orders=True
        )

        print(f"\nUpdate result: {result}")

        if result['success']:
            # Refresh from database
            db.session.expire_all()
            updated_tour = Tour.query.filter_by(tour_id=tour.tour_id).first()
            updated_orders = Order.query.filter(Order.tour_id == tour.tour_id).limit(2).all()

            print(f"\nAfter update:")
            print(f"Tour data:")
            print(f"  - vehicle_id: {updated_tour.vehicle_id}")
            print(f"  - rider_id: {updated_tour.rider_id}")

            all_tests_passed = True
            for i, order in enumerate(updated_orders):
                print(f"\nOrder {i+1} ({order.id}):")
                print(f"  - vehicle_id: {order.vehicle_id}")
                print(f"  - rider_id: {order.rider_id}")

                # Verify the data was propagated correctly
                if order.vehicle_id == test_update['vehicle_id']:
                    print(f"  ✓ vehicle_id propagated correctly")
                else:
                    print(f"  ✗ vehicle_id NOT propagated (expected: {test_update['vehicle_id']}, got: {order.vehicle_id})")
                    all_tests_passed = False

                if order.rider_id == test_update['rider_id']:
                    print(f"  ✓ rider_id propagated correctly")
                else:
                    print(f"  ✗ rider_id NOT propagated (expected: {test_update['rider_id']}, got: {order.rider_id})")
                    all_tests_passed = False

            print(f"\n{'🎉 ALL TESTS PASSED!' if all_tests_passed else '❌ SOME TESTS FAILED!'}")
            return all_tests_passed
        else:
            print(f"Update failed: {result}")
            return False

if __name__ == '__main__':
    try:
        success = test_vehicle_rider_propagation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)