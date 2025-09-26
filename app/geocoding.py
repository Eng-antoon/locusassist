"""
Geocoding Service Module
Handles location coordinate extraction and geocoding for orders
"""

import logging
import re
import json
from typing import Optional, Tuple, Dict

logger = logging.getLogger(__name__)

class GeocodingService:
    """Service class for geocoding addresses and extracting coordinates"""

    def __init__(self):
        # Pre-defined coordinates for common locations in Egypt
        # This is a basic fallback system for known locations
        self.known_locations = {
            # Spinneys locations
            'spinneys geziret el arab': (29.982941, 31.455952),
            'spinneys city scape': (29.958333, 31.218333), # 6th of October estimate
            'spinneys mazar': (30.020833, 31.021667), # Sheikh Zayed estimate

            # Carrefour locations
            'carrefour madinaty': (30.03511, 31.313013),
            'carrefour obour': (30.087594, 31.318328),

            # Cities (approximate centers)
            '6th of october': (29.955833, 31.211944),
            'madinaty': (30.103333, 31.643333),
            'nasr city': (30.063611, 31.341944),
            'sheikh zayed': (30.020833, 31.021667),
            'mohndsien': (30.027778, 31.201389),
            'giza': (30.013056, 31.208889),
            'cairo': (30.044420, 31.235712),
            'new cairo': (30.030556, 31.476111),
            'heliopolis': (30.088889, 31.327778),
            'zamalek': (30.061944, 31.221944),

            # Malls and shopping centers
            'city stars': (30.073333, 31.343056),
            'mall of arabia': (30.015833, 31.018333),
            'mall of egypt': (29.972222, 31.216667),
            'point 90 mall': (30.027778, 31.497222),
        }

    def extract_coordinates_from_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Try to extract coordinates from address string using various methods

        Args:
            address: Address string to geocode

        Returns:
            Tuple of (latitude, longitude) or None if not found
        """
        if not address or not isinstance(address, str):
            return None

        # Clean and normalize the address
        normalized_address = address.lower().strip()

        # Method 1: Check for Plus Codes (Google Plus Codes like "XW7G+3RQ")
        plus_code_match = re.search(r'([2-9C-FH-NP-TV-X]{4}\+[2-9C-FH-NP-TV-X]{2,3})', address)
        if plus_code_match:
            # Plus codes can be converted to coordinates, but for now we'll use approximate locations
            plus_code = plus_code_match.group(1)
            logger.info(f"Found Plus Code: {plus_code}, using approximate location")
            # For Egyptian Plus Codes starting with specific patterns, use approximate coords
            if plus_code.startswith(('XW7G', 'XW6G')):  # 6th of October area
                return (29.955833, 31.211944)
            elif plus_code.startswith(('3X3', '3X2')):  # Sheikh Zayed area
                return (30.020833, 31.021667)

        # Method 2: Check known locations database
        for location_name, coords in self.known_locations.items():
            if location_name in normalized_address:
                logger.info(f"Found known location: {location_name}")
                return coords

        # Method 3: Pattern matching for common address formats
        # Look for major area names in the address
        area_patterns = {
            r'6th of october|sixth of october|6 october': (29.955833, 31.211944),
            r'sheikh zayed|zayed': (30.020833, 31.021667),
            r'nasr city': (30.063611, 31.341944),
            r'madinaty': (30.103333, 31.643333),
            r'new cairo': (30.030556, 31.476111),
            r'heliopolis': (30.088889, 31.327778),
            r'mohndsien': (30.027778, 31.201389),
            r'zamalek': (30.061944, 31.221944),
            r'giza': (30.013056, 31.208889),
        }

        for pattern, coords in area_patterns.items():
            if re.search(pattern, normalized_address):
                logger.info(f"Found area pattern: {pattern}")
                return coords

        logger.debug(f"Could not geocode address: {address}")
        return None

    def geocode_order_location(self, order_data: dict) -> Optional[Tuple[float, float]]:
        """
        Extract coordinates from order location data

        Args:
            order_data: Order data dictionary (from raw_data)

        Returns:
            Tuple of (latitude, longitude) or None if not found
        """
        if not order_data or not isinstance(order_data, dict):
            return None

        # Try different location data sources in the order
        location_sources = []

        # Check if location data exists
        if 'location' in order_data:
            location = order_data['location']
            if isinstance(location, dict):
                # Try location name
                if 'name' in location:
                    location_sources.append(location['name'])

                # Try formatted address
                if 'address' in location and isinstance(location['address'], dict):
                    if 'formattedAddress' in location['address']:
                        location_sources.append(location['address']['formattedAddress'])

        # Also try top-level location fields
        for field in ['location_name', 'location_address']:
            if field in order_data and order_data[field]:
                location_sources.append(order_data[field])

        # Try to geocode each location source
        for location_str in location_sources:
            if location_str:
                coords = self.extract_coordinates_from_address(location_str)
                if coords:
                    return coords

        return None

    def update_order_coordinates(self, order, save=True) -> bool:
        """
        Update an order's latitude and longitude coordinates

        Args:
            order: Order model instance
            save: Whether to commit the changes to database

        Returns:
            True if coordinates were updated, False otherwise
        """
        try:
            # Skip if already has coordinates
            if order.location_latitude and order.location_longitude:
                return False

            # Try to get coordinates from various sources
            coords = None

            # Method 1: Try from raw_data if available
            if order.raw_data:
                try:
                    raw_data = json.loads(order.raw_data)
                    coords = self.geocode_order_location(raw_data)
                except json.JSONDecodeError:
                    logger.warning(f"Order {order.id}: Invalid JSON in raw_data")

            # Method 2: Try from order fields
            if not coords:
                location_sources = []
                if order.location_name:
                    location_sources.append(order.location_name)
                if order.location_address:
                    location_sources.append(order.location_address)

                for location_str in location_sources:
                    coords = self.extract_coordinates_from_address(location_str)
                    if coords:
                        break

            # Update coordinates if found
            if coords:
                order.location_latitude, order.location_longitude = coords
                if save:
                    from models import db
                    db.session.commit()
                logger.info(f"Updated coordinates for order {order.id}: {coords}")
                return True
            else:
                logger.debug(f"Could not find coordinates for order {order.id}")
                return False

        except Exception as e:
            logger.error(f"Error updating coordinates for order {order.id}: {e}")
            return False

    def batch_update_coordinates(self, date_filter: str = None, limit: int = None) -> dict:
        """
        Update coordinates for multiple orders in batch

        Args:
            date_filter: Date string (YYYY-MM-DD) to filter orders, None for all
            limit: Maximum number of orders to process, None for all

        Returns:
            Dictionary with results summary
        """
        try:
            from models import db, Order
            from datetime import datetime

            # Build query for orders without coordinates
            query = Order.query.filter(
                Order.location_latitude.is_(None),
                Order.location_longitude.is_(None)
            )

            # Apply date filter if provided
            if date_filter:
                try:
                    date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
                    query = query.filter(Order.date == date_obj)
                except ValueError:
                    return {
                        'success': False,
                        'error': f'Invalid date format: {date_filter}',
                        'updated_count': 0,
                        'processed_count': 0
                    }

            # Apply limit if provided
            if limit:
                query = query.limit(limit)

            orders = query.all()

            updated_count = 0
            processed_count = len(orders)

            logger.info(f"Processing {processed_count} orders for coordinate updates")

            # Process orders in batches to avoid memory issues
            batch_size = 100
            for i in range(0, len(orders), batch_size):
                batch = orders[i:i + batch_size]
                batch_updated = 0

                for order in batch:
                    if self.update_order_coordinates(order, save=False):
                        batch_updated += 1
                        updated_count += 1

                # Commit batch
                if batch_updated > 0:
                    db.session.commit()
                    logger.info(f"Batch {i//batch_size + 1}: Updated {batch_updated} orders")

            return {
                'success': True,
                'updated_count': updated_count,
                'processed_count': processed_count,
                'message': f'Successfully updated coordinates for {updated_count} out of {processed_count} orders'
            }

        except Exception as e:
            logger.error(f"Error in batch coordinate update: {e}")
            return {
                'success': False,
                'error': str(e),
                'updated_count': 0,
                'processed_count': 0
            }

    def add_known_location(self, location_name: str, latitude: float, longitude: float):
        """
        Add a new known location to the geocoding database

        Args:
            location_name: Name of the location (will be normalized)
            latitude: Latitude coordinate
            longitude: Longitude coordinate
        """
        normalized_name = location_name.lower().strip()
        self.known_locations[normalized_name] = (latitude, longitude)
        logger.info(f"Added known location: {normalized_name} -> ({latitude}, {longitude})")

# Global service instance
geocoding_service = GeocodingService()