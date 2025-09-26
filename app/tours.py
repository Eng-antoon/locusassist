"""
Tours Service Module
Handles tour data operations, aggregation, and API endpoints
"""

import logging
import json
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Optional, Tuple

from models import db, Order, Tour
from sqlalchemy import func, desc, asc
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

class TourService:
    """Service class for managing tour data and operations"""

    def __init__(self):
        pass

    def parse_tour_id(self, tour_id: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[int]]:
        """Parse a tour ID into its components"""
        return Tour.parse_tour_id(tour_id)

    def update_order_tour_data(self, order: Order, raw_order_data: dict) -> bool:
        """Update an order with parsed tour data from raw API data"""
        try:
            # Extract tour data from raw order data
            tour_detail = raw_order_data.get('orderMetadata', {}).get('tourDetail', {})
            tour_id = tour_detail.get('tourId')

            if not tour_id:
                logger.warning(f"Order {order.id}: No tour ID found in raw data")
                return False

            # Parse tour ID components
            tour_date, plan_id, tour_name, tour_number = self.parse_tour_id(tour_id)

            if not tour_date:
                logger.warning(f"Order {order.id}: Could not parse tour ID {tour_id}")
                return False

            # Update order with tour data
            order.tour_id = tour_id
            order.tour_date = tour_date
            order.tour_plan_id = plan_id
            order.tour_name = tour_name
            order.tour_number = tour_number or 0

            # Also update rider/vehicle info if available
            if tour_detail.get('riderName'):
                order.rider_name = tour_detail['riderName']
            if tour_detail.get('vehicleRegistrationNumber'):
                order.vehicle_registration = tour_detail['vehicleRegistrationNumber']

            logger.info(f"Order {order.id}: Updated with tour data - {tour_name} (#{tour_number})")
            return True

        except Exception as e:
            logger.error(f"Error updating order {order.id} with tour data: {e}")
            return False

    def get_or_create_tour(self, tour_id: str, tour_data: dict = None) -> Optional[Tour]:
        """Get existing tour or create a new one"""
        try:
            # Check if tour already exists
            tour = Tour.query.filter_by(tour_id=tour_id).first()

            if tour:
                return tour

            # Parse tour ID to get components
            tour_date, plan_id, tour_name, tour_number = self.parse_tour_id(tour_id)

            if not tour_date:
                logger.error(f"Could not parse tour ID: {tour_id}")
                return None

            # Create new tour
            tour = Tour(
                tour_id=tour_id,
                tour_date=tour_date,
                tour_plan_id=plan_id,
                tour_name=tour_name,
                tour_number=tour_number or 0
            )

            # Add tour-specific data if provided
            if tour_data:
                tour.rider_name = tour_data.get('riderName')
                tour.vehicle_registration = tour_data.get('vehicleRegistrationNumber')

                # Parse tour start/end times
                if tour_data.get('tourStartTime'):
                    try:
                        tour.tour_start_time = datetime.fromisoformat(tour_data['tourStartTime'].replace('Z', '+00:00'))
                    except Exception:
                        pass

                if tour_data.get('tourEndTime'):
                    try:
                        tour.tour_end_time = datetime.fromisoformat(tour_data['tourEndTime'].replace('Z', '+00:00'))
                    except Exception:
                        pass

            db.session.add(tour)
            db.session.commit()

            logger.info(f"Created new tour: {tour_id}")
            return tour

        except Exception as e:
            logger.error(f"Error creating/retrieving tour {tour_id}: {e}")
            db.session.rollback()
            return None

    def update_tour_statistics(self, tour_id: str):
        """Update statistics for a specific tour"""
        try:
            tour = Tour.query.filter_by(tour_id=tour_id).first()
            if not tour:
                logger.warning(f"Tour {tour_id} not found for statistics update")
                return

            # Get all orders for this tour
            orders = Order.query.filter_by(tour_id=tour_id).all()

            if not orders:
                logger.warning(f"No orders found for tour {tour_id}")
                return

            # Calculate statistics
            tour.total_orders = len(orders)
            completed_orders = [o for o in orders if o.order_status == 'COMPLETED']
            cancelled_orders = [o for o in orders if o.order_status == 'CANCELLED']
            waiting_orders = [o for o in orders if o.order_status == 'WAITING']

            tour.completed_orders = len(completed_orders)
            tour.cancelled_orders = len(cancelled_orders)
            tour.pending_orders = tour.total_orders - tour.completed_orders - tour.cancelled_orders

            # Calculate tour status based on order statuses
            if tour.total_orders == 0:
                tour.tour_status = 'WAITING'
            elif len(cancelled_orders) == tour.total_orders:
                # All orders are cancelled
                tour.tour_status = 'CANCELLED'
            elif len(completed_orders) + len(cancelled_orders) == tour.total_orders:
                # All orders are either completed or cancelled (consider cancelled as completed for tour)
                tour.tour_status = 'COMPLETED'
            elif len(waiting_orders) == tour.total_orders:
                # All orders are waiting
                tour.tour_status = 'WAITING'
            else:
                # Mixed statuses - some completed/ongoing/cancelled
                tour.tour_status = 'ONGOING'

            # Collect location data
            cities = set()
            areas = set()

            for order in orders:
                if order.location_city:
                    cities.add(order.location_city)
                if order.location_name:
                    areas.add(order.location_name)

            # Update location data
            tour.delivery_cities = json.dumps(list(cities))
            tour.delivery_areas = json.dumps(list(areas))

            # Get rider/vehicle info from first order if not set
            if not tour.rider_name and orders:
                tour.rider_name = orders[0].rider_name
            if not tour.vehicle_registration and orders:
                tour.vehicle_registration = orders[0].vehicle_registration

            db.session.commit()
            logger.info(f"Updated statistics for tour {tour_id}: {tour.total_orders} orders")

        except Exception as e:
            logger.error(f"Error updating tour statistics for {tour_id}: {e}")
            db.session.rollback()

    def get_tours(self, date: str = None, page: int = 1, per_page: int = 50,
                  search: str = None, sort_by: str = 'tour_number',
                  sort_order: str = 'asc') -> dict:
        """Get tours with filtering, searching, and pagination"""
        try:
            query = Tour.query

            # Date filtering
            if date:
                query = query.filter(Tour.tour_date.like(f"{date}%"))

            # Search filtering
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    db.or_(
                        Tour.tour_id.ilike(search_term),
                        Tour.tour_name.ilike(search_term),
                        Tour.rider_name.ilike(search_term),
                        Tour.vehicle_registration.ilike(search_term)
                    )
                )

            # Sorting
            if sort_by == 'tour_number':
                if sort_order == 'desc':
                    query = query.order_by(desc(Tour.tour_number))
                else:
                    query = query.order_by(asc(Tour.tour_number))
            elif sort_by == 'tour_date':
                if sort_order == 'desc':
                    query = query.order_by(desc(Tour.tour_date))
                else:
                    query = query.order_by(asc(Tour.tour_date))
            elif sort_by == 'total_orders':
                if sort_order == 'desc':
                    query = query.order_by(desc(Tour.total_orders))
                else:
                    query = query.order_by(asc(Tour.total_orders))
            else:
                # Default to tour number ascending
                query = query.order_by(asc(Tour.tour_number))

            # Get total count for pagination
            total_count = query.count()

            # Apply pagination
            tours = query.offset((page - 1) * per_page).limit(per_page).all()

            # Calculate pagination info
            total_pages = (total_count + per_page - 1) // per_page

            return {
                'success': True,
                'tours': [tour.to_dict() for tour in tours],
                'total_count': total_count,
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }

        except Exception as e:
            logger.error(f"Error getting tours: {e}")
            return {
                'success': False,
                'error': str(e),
                'tours': [],
                'total_count': 0
            }

    def get_tour_details(self, tour_id: str) -> dict:
        """Get detailed information about a specific tour including its orders"""
        try:
            # Get the tour
            tour = Tour.query.filter_by(tour_id=tour_id).first()
            if not tour:
                return {
                    'success': False,
                    'error': f'Tour {tour_id} not found',
                    'tour': None,
                    'orders': []
                }

            # Get all orders for this tour
            orders = Order.query.filter_by(tour_id=tour_id).order_by(Order.id).all()

            # Update tour statistics if orders exist
            if orders:
                self.update_tour_statistics(tour_id)
                # Refresh tour object to get updated stats
                db.session.refresh(tour)

            return {
                'success': True,
                'tour': tour.to_dict(),
                'orders': [order.to_dict() for order in orders],
                'orders_count': len(orders)
            }

        except Exception as e:
            logger.error(f"Error getting tour details for {tour_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'tour': None,
                'orders': []
            }

    def get_tour_summary_stats(self, date: str = None) -> dict:
        """Get summary statistics for all tours on a given date"""
        try:
            query = Tour.query

            if date:
                query = query.filter(Tour.tour_date.like(f"{date}%"))

            tours = query.all()

            if not tours:
                return {
                    'success': True,
                    'total_tours': 0,
                    'total_orders': 0,
                    'completed_orders': 0,
                    'pending_orders': 0,
                    'unique_riders': 0,
                    'unique_cities': 0
                }

            # Calculate summary statistics
            total_tours = len(tours)
            total_orders = sum(tour.total_orders for tour in tours)
            completed_orders = sum(tour.completed_orders for tour in tours)
            cancelled_orders = sum(tour.cancelled_orders for tour in tours)
            pending_orders = sum(tour.pending_orders for tour in tours)

            # Count unique riders and cities
            unique_riders = set()
            all_cities = set()

            for tour in tours:
                if tour.rider_name:
                    unique_riders.add(tour.rider_name)

                if tour.delivery_cities:
                    try:
                        cities = json.loads(tour.delivery_cities)
                        all_cities.update(cities)
                    except json.JSONDecodeError:
                        pass

            return {
                'success': True,
                'total_tours': total_tours,
                'total_orders': total_orders,
                'completed_orders': completed_orders,
                'cancelled_orders': cancelled_orders,
                'pending_orders': pending_orders,
                'unique_riders': len(unique_riders),
                'unique_cities': len(all_cities),
                'completion_rate': round(((completed_orders + cancelled_orders) / total_orders * 100) if total_orders > 0 else 0, 1)
            }

        except Exception as e:
            logger.error(f"Error getting tour summary stats: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def refresh_all_tour_data(self, date: str = None) -> dict:
        """Refresh tour data by processing all orders and updating tour statistics"""
        try:
            query = Order.query

            if date:
                query = query.filter(Order.date == datetime.strptime(date, '%Y-%m-%d').date())

            orders = query.all()

            if not orders:
                return {
                    'success': True,
                    'message': f'No orders found for date {date}',
                    'processed_orders': 0,
                    'updated_tours': 0
                }

            processed_orders = 0
            updated_tours = set()

            # Process each order to extract and update tour data
            for order in orders:
                if order.raw_data:
                    try:
                        raw_data = json.loads(order.raw_data)
                        if self.update_order_tour_data(order, raw_data):
                            processed_orders += 1

                            # Track tours that need statistics update
                            if order.tour_id:
                                updated_tours.add(order.tour_id)
                    except json.JSONDecodeError:
                        logger.warning(f"Order {order.id}: Could not parse raw_data")

            # Commit order updates
            db.session.commit()

            # Update statistics for all affected tours
            for tour_id in updated_tours:
                # Create or update tour record
                tour_detail = None
                # Get tour detail from first order of this tour
                sample_order = Order.query.filter_by(tour_id=tour_id).first()
                if sample_order and sample_order.raw_data:
                    try:
                        raw_data = json.loads(sample_order.raw_data)
                        tour_detail = raw_data.get('orderMetadata', {}).get('tourDetail', {})
                    except json.JSONDecodeError:
                        pass

                self.get_or_create_tour(tour_id, tour_detail)
                self.update_tour_statistics(tour_id)

            return {
                'success': True,
                'message': f'Successfully processed {processed_orders} orders and updated {len(updated_tours)} tours',
                'processed_orders': processed_orders,
                'updated_tours': len(updated_tours)
            }

        except Exception as e:
            logger.error(f"Error refreshing tour data: {e}")
            db.session.rollback()
            return {
                'success': False,
                'error': str(e),
                'processed_orders': 0,
                'updated_tours': 0
            }

# Global service instance
tour_service = TourService()