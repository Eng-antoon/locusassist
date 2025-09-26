"""
Heatmap Service Module
Handles delivery heatmap data operations and API endpoints
"""

import logging
import json
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Optional, Tuple

from models import db, Order, OrderLineItem
from sqlalchemy import func, and_, or_

logger = logging.getLogger(__name__)

class HeatmapService:
    """Service class for managing delivery heatmap data and operations"""

    def __init__(self):
        pass

    def get_delivery_heatmap_data(self, date: str = None, date_from: str = None, date_to: str = None, aggregation_level: str = 'coordinate',
                                  status_filter: str = None, rider_filter: str = None, vehicle_filter: str = None) -> dict:
        """
        Get delivery heatmap data aggregated by location

        Args:
            date: Filter by specific date (YYYY-MM-DD format) - for backward compatibility
            date_from: Start date for date range filtering (YYYY-MM-DD format)
            date_to: End date for date range filtering (YYYY-MM-DD format)
            aggregation_level: 'coordinate' for exact coordinates, 'area' for location names, 'city' for cities
            status_filter: Filter by status ('completed', 'cancelled', 'partially_delivered', 'pending')
            rider_filter: Filter by rider name
            vehicle_filter: Filter by vehicle registration

        Returns:
            Dict with heatmap data and statistics
        """
        logger.info(f"🔥 === HEATMAP DATA REQUEST ===")
        logger.info(f"📅 Date filter: {date}")
        logger.info(f"📅 Date range: {date_from} to {date_to}")
        logger.info(f"📊 Aggregation level: {aggregation_level}")
        try:
            # Start with base query for orders with location data
            query = db.session.query(Order).filter(
                and_(
                    Order.location_latitude.isnot(None),
                    Order.location_longitude.isnot(None)
                )
            )

            # Apply date filtering if provided - support date ranges
            if date_from and date_to:
                try:
                    start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                    end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                    query = query.filter(Order.date >= start_date)
                    query = query.filter(Order.date <= end_date)
                    logger.info(f"📅 Applied date range filter: {start_date} to {end_date}")
                except ValueError:
                    logger.error(f"Invalid date format in range: {date_from} to {date_to}")
                    return {
                        'success': False,
                        'error': 'Invalid date format. Please use YYYY-MM-DD.',
                        'heatmap_data': [],
                        'statistics': {}
                    }
            elif date_from:
                try:
                    date_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                    query = query.filter(Order.date == date_obj)
                    logger.info(f"📅 Applied single date filter from date_from: {date_obj}")
                except ValueError:
                    logger.error(f"Invalid date format: {date_from}")
                    return {
                        'success': False,
                        'error': 'Invalid date format. Please use YYYY-MM-DD.',
                        'heatmap_data': [],
                        'statistics': {}
                    }
            elif date:
                try:
                    date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                    query = query.filter(Order.date == date_obj)
                    logger.info(f"📅 Applied single date filter: {date_obj}")
                except ValueError:
                    logger.error(f"Invalid date format: {date}")
                    return {
                        'success': False,
                        'error': 'Invalid date format. Please use YYYY-MM-DD.',
                        'heatmap_data': [],
                        'statistics': {}
                    }

            # Apply additional filters
            if status_filter:
                logger.info(f"📋 Applying status filter: {status_filter}")
                if status_filter == 'completed':
                    query = query.filter(Order.order_status == 'COMPLETED')
                elif status_filter == 'cancelled':
                    query = query.filter(Order.order_status == 'CANCELLED')
                elif status_filter == 'partially_delivered':
                    query = query.filter(Order.partially_delivered == True)
                elif status_filter == 'pending':
                    query = query.filter(and_(
                        Order.order_status != 'COMPLETED',
                        Order.order_status != 'CANCELLED'
                    ))

            if rider_filter:
                logger.info(f"📋 Applying rider filter: {rider_filter}")
                query = query.filter(Order.rider_name.ilike(f'%{rider_filter}%'))

            if vehicle_filter:
                logger.info(f"📋 Applying vehicle filter: {vehicle_filter}")
                query = query.filter(Order.vehicle_registration.ilike(f'%{vehicle_filter}%'))

            # Get all orders with location data
            logger.info(f"📋 Executing database query...")
            orders = query.all()
            logger.info(f"✓ Query completed. Found {len(orders)} orders with coordinates")

            if not orders:
                # Check if we have orders for this date range but without coordinates
                orders_without_coords = 0
                if date_from and date_to:
                    try:
                        start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                        end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                        orders_without_coords = db.session.query(Order).filter(Order.date >= start_date, Order.date <= end_date).count()
                    except ValueError:
                        pass
                elif date_from:
                    try:
                        date_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                        orders_without_coords = db.session.query(Order).filter(Order.date == date_obj).count()
                    except ValueError:
                        pass
                elif date:
                    try:
                        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                        orders_without_coords = db.session.query(Order).filter(Order.date == date_obj).count()
                    except ValueError:
                        pass

                # Determine date display for response
                date_display = None
                if date_from and date_to:
                    date_display = f"{date_from} to {date_to}" if date_from != date_to else date_from
                elif date_from:
                    date_display = date_from
                elif date:
                    date_display = date

                return {
                    'success': True,
                    'heatmap_data': [],
                    'statistics': {
                        'total_orders': 0,
                        'total_locations': 0,
                        'total_quantity': 0,
                        'delivered_quantity': 0,
                        'completion_rate': 0.0
                    },
                    'aggregation_level': aggregation_level,
                    'date_filter': date_display,
                    'date_from': date_from,
                    'date_to': date_to,
                    'orders_without_coordinates': orders_without_coords,
                    'needs_coordinate_extraction': orders_without_coords > 0
                }

            # Aggregate data based on level
            if aggregation_level == 'coordinate':
                heatmap_data = self._aggregate_by_coordinates(orders)
            elif aggregation_level == 'area':
                heatmap_data = self._aggregate_by_area(orders)
            elif aggregation_level == 'city':
                heatmap_data = self._aggregate_by_city(orders)
            else:
                heatmap_data = self._aggregate_by_coordinates(orders)  # Default

            # Calculate statistics
            logger.info(f"📊 Calculating statistics...")
            statistics = self._calculate_statistics(orders)
            logger.info(f"✓ Statistics calculated")

            logger.info(f"✅ HEATMAP DATA GENERATED:")
            logger.info(f"   - Orders processed: {len(orders)}")
            logger.info(f"   - Heatmap points: {len(heatmap_data)}")
            logger.info(f"   - Total orders: {statistics.get('total_orders', 0)}")
            logger.info(f"   - Unique locations: {statistics.get('unique_locations', 0)}")

            # Determine date display for response
            date_display = None
            if date_from and date_to:
                date_display = f"{date_from} to {date_to}" if date_from != date_to else date_from
            elif date_from:
                date_display = date_from
            elif date:
                date_display = date

            return {
                'success': True,
                'heatmap_data': heatmap_data,
                'statistics': statistics,
                'aggregation_level': aggregation_level,
                'date_filter': date_display,
                'date_from': date_from,
                'date_to': date_to
            }

        except Exception as e:
            logger.error(f"Error getting heatmap data: {e}")
            return {
                'success': False,
                'error': str(e),
                'heatmap_data': [],
                'statistics': {}
            }

    def _aggregate_by_coordinates(self, orders: List[Order]) -> List[Dict]:
        """Aggregate delivery data by exact coordinates"""
        coordinate_data = defaultdict(lambda: {
            'orders': [],
            'total_quantity': 0,
            'delivered_quantity': 0,
            'order_count': 0,
            'completed_orders': 0,
            'cancelled_orders': 0,
            'pending_orders': 0
        })

        for order in orders:
            # Create coordinate key (round to avoid too many unique points)
            coord_key = (round(order.location_latitude, 5), round(order.location_longitude, 5))

            data = coordinate_data[coord_key]
            data['orders'].append({
                'id': order.id,
                'status': order.order_status,
                'location_name': order.location_name,
                'location_address': order.location_address,
                'location_city': order.location_city,
                'rider_name': order.rider_name,
                'vehicle_registration': order.vehicle_registration,
                'date': order.date.isoformat() if order.date else None,
                'completed_on': order.completed_on.isoformat() if order.completed_on else None,
                'customer_name': getattr(order, 'customer_name', None),
                'total_items': len(order.line_items) if order.line_items else 0,
                'order_value': sum(getattr(item, 'amount', 0) or 0 for item in order.line_items) if order.line_items else 0
            })
            data['order_count'] += 1

            # Count by status
            if order.order_status == 'COMPLETED':
                data['completed_orders'] += 1
            elif order.order_status == 'CANCELLED':
                data['cancelled_orders'] += 1
            else:
                data['pending_orders'] += 1

            # Get quantities from line items
            for line_item in order.line_items:
                data['total_quantity'] += line_item.quantity or 0
                data['delivered_quantity'] += line_item.transacted_quantity or 0

        # Convert to list format for frontend
        heatmap_points = []
        for (lat, lng), data in coordinate_data.items():
            completion_rate = (data['completed_orders'] / data['order_count']) * 100 if data['order_count'] > 0 else 0
            delivery_rate = (data['delivered_quantity'] / data['total_quantity']) * 100 if data['total_quantity'] > 0 else 0

            heatmap_points.append({
                'latitude': lat,
                'longitude': lng,
                'order_count': data['order_count'],
                'completed_orders': data['completed_orders'],
                'cancelled_orders': data['cancelled_orders'],
                'pending_orders': data['pending_orders'],
                'total_quantity': data['total_quantity'],
                'delivered_quantity': data['delivered_quantity'],
                'completion_rate': round(completion_rate, 1),
                'delivery_rate': round(delivery_rate, 1),
                'intensity': data['order_count'],  # For heatmap intensity
                'orders': data['orders'][:10],  # Limit to 10 orders for popup
                'location_name': data['orders'][0]['location_name'] if data['orders'] else 'Unknown Location'
            })

        # Sort by intensity for better visualization
        heatmap_points.sort(key=lambda x: x['intensity'], reverse=True)

        return heatmap_points

    def _aggregate_by_area(self, orders: List[Order]) -> List[Dict]:
        """Aggregate delivery data by location name/area"""
        area_data = defaultdict(lambda: {
            'orders': [],
            'coordinates': [],
            'total_quantity': 0,
            'delivered_quantity': 0,
            'order_count': 0,
            'completed_orders': 0,
            'cancelled_orders': 0,
            'pending_orders': 0
        })

        for order in orders:
            area_key = order.location_name or 'Unknown Area'

            data = area_data[area_key]
            data['orders'].append({
                'id': order.id,
                'status': order.order_status,
                'location_name': order.location_name,
                'location_address': order.location_address,
                'location_city': order.location_city,
                'rider_name': order.rider_name,
                'vehicle_registration': order.vehicle_registration,
                'date': order.date.isoformat() if order.date else None,
                'completed_on': order.completed_on.isoformat() if order.completed_on else None,
                'customer_name': getattr(order, 'customer_name', None),
                'total_items': len(order.line_items) if order.line_items else 0,
                'order_value': sum(getattr(item, 'amount', 0) or 0 for item in order.line_items) if order.line_items else 0
            })
            data['coordinates'].append({
                'lat': order.location_latitude,
                'lng': order.location_longitude
            })
            data['order_count'] += 1

            # Count by status
            if order.order_status == 'COMPLETED':
                data['completed_orders'] += 1
            elif order.order_status == 'CANCELLED':
                data['cancelled_orders'] += 1
            else:
                data['pending_orders'] += 1

            # Get quantities from line items
            for line_item in order.line_items:
                data['total_quantity'] += line_item.quantity or 0
                data['delivered_quantity'] += line_item.transacted_quantity or 0

        # Convert to list format with center coordinates
        heatmap_points = []
        for area_name, data in area_data.items():
            if not data['coordinates']:
                continue

            # Calculate center point
            avg_lat = sum(coord['lat'] for coord in data['coordinates']) / len(data['coordinates'])
            avg_lng = sum(coord['lng'] for coord in data['coordinates']) / len(data['coordinates'])

            completion_rate = (data['completed_orders'] / data['order_count']) * 100 if data['order_count'] > 0 else 0
            delivery_rate = (data['delivered_quantity'] / data['total_quantity']) * 100 if data['total_quantity'] > 0 else 0

            heatmap_points.append({
                'latitude': avg_lat,
                'longitude': avg_lng,
                'area_name': area_name,
                'order_count': data['order_count'],
                'completed_orders': data['completed_orders'],
                'cancelled_orders': data['cancelled_orders'],
                'pending_orders': data['pending_orders'],
                'total_quantity': data['total_quantity'],
                'delivered_quantity': data['delivered_quantity'],
                'completion_rate': round(completion_rate, 1),
                'delivery_rate': round(delivery_rate, 1),
                'intensity': data['order_count'],
                'orders': data['orders'][:10],
                'location_name': area_name
            })

        heatmap_points.sort(key=lambda x: x['intensity'], reverse=True)
        return heatmap_points

    def _aggregate_by_city(self, orders: List[Order]) -> List[Dict]:
        """Aggregate delivery data by city"""
        city_data = defaultdict(lambda: {
            'orders': [],
            'coordinates': [],
            'areas': set(),
            'total_quantity': 0,
            'delivered_quantity': 0,
            'order_count': 0,
            'completed_orders': 0,
            'cancelled_orders': 0,
            'pending_orders': 0
        })

        for order in orders:
            city_key = order.location_city or 'Unknown City'

            data = city_data[city_key]
            data['orders'].append({
                'id': order.id,
                'status': order.order_status,
                'location_name': order.location_name,
                'location_address': order.location_address,
                'location_city': order.location_city,
                'rider_name': order.rider_name,
                'vehicle_registration': order.vehicle_registration,
                'date': order.date.isoformat() if order.date else None,
                'completed_on': order.completed_on.isoformat() if order.completed_on else None,
                'customer_name': getattr(order, 'customer_name', None),
                'total_items': len(order.line_items) if order.line_items else 0,
                'order_value': sum(getattr(item, 'amount', 0) or 0 for item in order.line_items) if order.line_items else 0
            })
            data['coordinates'].append({
                'lat': order.location_latitude,
                'lng': order.location_longitude
            })
            if order.location_name:
                data['areas'].add(order.location_name)
            data['order_count'] += 1

            # Count by status
            if order.order_status == 'COMPLETED':
                data['completed_orders'] += 1
            elif order.order_status == 'CANCELLED':
                data['cancelled_orders'] += 1
            else:
                data['pending_orders'] += 1

            # Get quantities from line items
            for line_item in order.line_items:
                data['total_quantity'] += line_item.quantity or 0
                data['delivered_quantity'] += line_item.transacted_quantity or 0

        # Convert to list format with center coordinates
        heatmap_points = []
        for city_name, data in city_data.items():
            if not data['coordinates']:
                continue

            # Calculate center point
            avg_lat = sum(coord['lat'] for coord in data['coordinates']) / len(data['coordinates'])
            avg_lng = sum(coord['lng'] for coord in data['coordinates']) / len(data['coordinates'])

            completion_rate = (data['completed_orders'] / data['order_count']) * 100 if data['order_count'] > 0 else 0
            delivery_rate = (data['delivered_quantity'] / data['total_quantity']) * 100 if data['total_quantity'] > 0 else 0

            heatmap_points.append({
                'latitude': avg_lat,
                'longitude': avg_lng,
                'city_name': city_name,
                'area_count': len(data['areas']),
                'order_count': data['order_count'],
                'completed_orders': data['completed_orders'],
                'cancelled_orders': data['cancelled_orders'],
                'pending_orders': data['pending_orders'],
                'total_quantity': data['total_quantity'],
                'delivered_quantity': data['delivered_quantity'],
                'completion_rate': round(completion_rate, 1),
                'delivery_rate': round(delivery_rate, 1),
                'intensity': data['order_count'],
                'orders': data['orders'][:10],
                'location_name': city_name
            })

        heatmap_points.sort(key=lambda x: x['intensity'], reverse=True)
        return heatmap_points

    def _calculate_statistics(self, orders: List[Order]) -> Dict:
        """Calculate overall statistics for the heatmap data"""
        total_orders = len(orders)
        completed_orders = sum(1 for order in orders if order.order_status == 'COMPLETED')
        cancelled_orders = sum(1 for order in orders if order.order_status == 'CANCELLED')
        partially_delivered_orders = sum(1 for order in orders if order.partially_delivered)
        pending_orders = total_orders - completed_orders - cancelled_orders

        total_quantity = 0
        delivered_quantity = 0
        unique_locations = set()
        unique_cities = set()
        unique_riders = set()
        unique_vehicles = set()

        for order in orders:
            # Track unique locations
            if order.location_name:
                unique_locations.add(order.location_name)
            if order.location_city:
                unique_cities.add(order.location_city)

            # Track unique riders and vehicles for filter options
            if order.rider_name:
                unique_riders.add(order.rider_name)
            if order.vehicle_registration:
                unique_vehicles.add(order.vehicle_registration)

            # Sum quantities
            for line_item in order.line_items:
                total_quantity += line_item.quantity or 0
                delivered_quantity += line_item.transacted_quantity or 0

        completion_rate = (completed_orders / total_orders) * 100 if total_orders > 0 else 0
        delivery_rate = (delivered_quantity / total_quantity) * 100 if total_quantity > 0 else 0

        return {
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'cancelled_orders': cancelled_orders,
            'partially_delivered_orders': partially_delivered_orders,
            'pending_orders': pending_orders,
            'completion_rate': round(completion_rate, 1),
            'total_quantity': total_quantity,
            'delivered_quantity': delivered_quantity,
            'delivery_rate': round(delivery_rate, 1),
            'unique_locations': len(unique_locations),
            'unique_cities': len(unique_cities),
            'unique_riders': len(unique_riders),
            'unique_vehicles': len(unique_vehicles)
        }

    def get_filter_options(self, date: str = None, date_from: str = None, date_to: str = None) -> dict:
        """
        Get available filter options for the heatmap

        Args:
            date: Filter by specific date (YYYY-MM-DD format) - for backward compatibility
            date_from: Start date for date range filtering (YYYY-MM-DD format)
            date_to: End date for date range filtering (YYYY-MM-DD format)

        Returns:
            Dict with available filter options
        """
        try:
            # Start with base query for orders with location data
            query = db.session.query(Order).filter(
                and_(
                    Order.location_latitude.isnot(None),
                    Order.location_longitude.isnot(None)
                )
            )

            # Apply date filtering
            if date_from and date_to:
                try:
                    start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                    end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                    query = query.filter(Order.date >= start_date)
                    query = query.filter(Order.date <= end_date)
                except ValueError:
                    pass
            elif date_from:
                try:
                    date_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                    query = query.filter(Order.date == date_obj)
                except ValueError:
                    pass
            elif date:
                try:
                    date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                    query = query.filter(Order.date == date_obj)
                except ValueError:
                    pass

            # Get unique riders and vehicles
            riders = db.session.query(Order.rider_name.distinct().label('rider_name')).filter(
                and_(
                    Order.location_latitude.isnot(None),
                    Order.location_longitude.isnot(None),
                    Order.rider_name.isnot(None)
                )
            )

            vehicles = db.session.query(Order.vehicle_registration.distinct().label('vehicle_registration')).filter(
                and_(
                    Order.location_latitude.isnot(None),
                    Order.location_longitude.isnot(None),
                    Order.vehicle_registration.isnot(None)
                )
            )

            # Apply same date filters to rider/vehicle queries
            if date_from and date_to:
                try:
                    start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                    end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                    riders = riders.filter(Order.date >= start_date, Order.date <= end_date)
                    vehicles = vehicles.filter(Order.date >= start_date, Order.date <= end_date)
                except ValueError:
                    pass
            elif date_from:
                try:
                    date_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                    riders = riders.filter(Order.date == date_obj)
                    vehicles = vehicles.filter(Order.date == date_obj)
                except ValueError:
                    pass
            elif date:
                try:
                    date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                    riders = riders.filter(Order.date == date_obj)
                    vehicles = vehicles.filter(Order.date == date_obj)
                except ValueError:
                    pass

            rider_list = [r.rider_name for r in riders.order_by('rider_name').all() if r.rider_name]
            vehicle_list = [v.vehicle_registration for v in vehicles.order_by('vehicle_registration').all() if v.vehicle_registration]

            return {
                'success': True,
                'riders': rider_list,
                'vehicles': vehicle_list,
                'status_options': [
                    {'value': 'completed', 'label': 'Completed Orders'},
                    {'value': 'cancelled', 'label': 'Cancelled Orders'},
                    {'value': 'partially_delivered', 'label': 'Partially Delivered Orders'},
                    {'value': 'pending', 'label': 'Pending Orders'}
                ]
            }

        except Exception as e:
            logger.error(f"Error getting filter options: {e}")
            return {
                'success': False,
                'error': str(e),
                'riders': [],
                'vehicles': [],
                'status_options': []
            }

    def get_location_details(self, latitude: float, longitude: float, radius: float = 0.001) -> dict:
        """
        Get detailed information for orders near specific coordinates

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius: Search radius in degrees (default ~100m)

        Returns:
            Detailed information about orders in the area
        """
        try:
            # Query orders within radius
            query = db.session.query(Order).filter(
                and_(
                    Order.location_latitude.between(latitude - radius, latitude + radius),
                    Order.location_longitude.between(longitude - radius, longitude + radius)
                )
            )

            orders = query.all()

            if not orders:
                return {
                    'success': True,
                    'orders': [],
                    'summary': {
                        'order_count': 0,
                        'total_quantity': 0,
                        'delivered_quantity': 0
                    }
                }

            # Prepare detailed order information
            order_details = []
            total_quantity = 0
            delivered_quantity = 0

            for order in orders:
                # Get line items with details
                line_items = []
                for line_item in order.line_items:
                    total_quantity += line_item.quantity or 0
                    delivered_quantity += line_item.transacted_quantity or 0

                    line_items.append({
                        'sku_id': line_item.sku_id,
                        'name': line_item.name,
                        'quantity': line_item.quantity,
                        'delivered_quantity': line_item.transacted_quantity,
                        'unit': line_item.quantity_unit
                    })

                order_details.append({
                    'id': order.id,
                    'status': order.order_status,
                    'location_name': order.location_name,
                    'location_address': order.location_address,
                    'location_city': order.location_city,
                    'rider_name': order.rider_name,
                    'vehicle_registration': order.vehicle_registration,
                    'completed_on': order.completed_on.isoformat() if order.completed_on else None,
                    'line_items': line_items
                })

            return {
                'success': True,
                'orders': order_details,
                'summary': {
                    'order_count': len(orders),
                    'completed_orders': sum(1 for order in orders if order.order_status == 'COMPLETED'),
                    'cancelled_orders': sum(1 for order in orders if order.order_status == 'CANCELLED'),
                    'pending_orders': len(orders) - sum(1 for order in orders if order.order_status in ['COMPLETED', 'CANCELLED']),
                    'total_quantity': total_quantity,
                    'delivered_quantity': delivered_quantity,
                    'delivery_rate': round((delivered_quantity / total_quantity) * 100, 1) if total_quantity > 0 else 0
                }
            }

        except Exception as e:
            logger.error(f"Error getting location details: {e}")
            return {
                'success': False,
                'error': str(e),
                'orders': [],
                'summary': {}
            }

# Global service instance
heatmap_service = HeatmapService()