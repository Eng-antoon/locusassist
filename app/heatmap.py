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

    def get_delivery_heatmap_data(self, date: str = None, aggregation_level: str = 'coordinate') -> dict:
        """
        Get delivery heatmap data aggregated by location

        Args:
            date: Filter by specific date (YYYY-MM-DD format)
            aggregation_level: 'coordinate' for exact coordinates, 'area' for location names, 'city' for cities

        Returns:
            Dict with heatmap data and statistics
        """
        try:
            # Start with base query for orders with location data
            query = db.session.query(Order).filter(
                and_(
                    Order.location_latitude.isnot(None),
                    Order.location_longitude.isnot(None)
                )
            )

            # Apply date filtering if provided
            if date:
                try:
                    date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                    query = query.filter(Order.date == date_obj)
                except ValueError:
                    logger.error(f"Invalid date format: {date}")
                    return {
                        'success': False,
                        'error': 'Invalid date format. Please use YYYY-MM-DD.',
                        'heatmap_data': [],
                        'statistics': {}
                    }

            # Get all orders with location data
            orders = query.all()

            if not orders:
                # Check if we have orders for this date but without coordinates
                orders_without_coords = db.session.query(Order).filter(Order.date == date_obj).count()

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
                    'date_filter': date,
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
            statistics = self._calculate_statistics(orders)

            return {
                'success': True,
                'heatmap_data': heatmap_data,
                'statistics': statistics,
                'aggregation_level': aggregation_level,
                'date_filter': date
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
                'completed_on': order.completed_on.isoformat() if order.completed_on else None
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
                'location_address': order.location_address,
                'completed_on': order.completed_on.isoformat() if order.completed_on else None
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
                'completed_on': order.completed_on.isoformat() if order.completed_on else None
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
        pending_orders = total_orders - completed_orders - cancelled_orders

        total_quantity = 0
        delivered_quantity = 0
        unique_locations = set()
        unique_cities = set()

        for order in orders:
            # Track unique locations
            if order.location_name:
                unique_locations.add(order.location_name)
            if order.location_city:
                unique_cities.add(order.location_city)

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
            'pending_orders': pending_orders,
            'completion_rate': round(completion_rate, 1),
            'total_quantity': total_quantity,
            'delivered_quantity': delivered_quantity,
            'delivery_rate': round(delivery_rate, 1),
            'unique_locations': len(unique_locations),
            'unique_cities': len(unique_cities)
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