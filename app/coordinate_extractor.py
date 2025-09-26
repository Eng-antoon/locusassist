"""
Coordinate Extraction Service
Enhances order data with location coordinates from Locus API
"""

import logging
import json
import time
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

logger = logging.getLogger(__name__)

class CoordinateExtractor:
    """Service to extract and store coordinates for orders"""

    def __init__(self, auth_service, rate_limit_delay: float = 0.1):
        self.auth_service = auth_service
        self.rate_limit_delay = rate_limit_delay  # Delay between API calls to avoid rate limiting

    def extract_coordinates_from_order_detail(self, order_detail: Dict) -> Optional[Tuple[float, float]]:
        """
        Extract coordinates from order detail API response

        Args:
            order_detail: Order detail response from Locus API

        Returns:
            Tuple of (latitude, longitude) or None if not found
        """
        try:
            # Check location.latLng first (primary source)
            if 'location' in order_detail and order_detail['location']:
                location = order_detail['location']
                if 'latLng' in location and location['latLng']:
                    lat_lng = location['latLng']
                    lat = lat_lng.get('lat')
                    lng = lat_lng.get('lng')

                    if lat is not None and lng is not None:
                        logger.debug(f"Found coordinates in location.latLng: ({lat}, {lng})")
                        return (float(lat), float(lng))

            # Check geocodingMetadata.latLng as backup
            if 'geocodingMetadata' in order_detail and order_detail['geocodingMetadata']:
                geocoding = order_detail['geocodingMetadata']
                if 'latLng' in geocoding and geocoding['latLng']:
                    lat_lng = geocoding['latLng']
                    lat = lat_lng.get('lat')
                    lng = lat_lng.get('lng')

                    if lat is not None and lng is not None:
                        logger.debug(f"Found coordinates in geocodingMetadata.latLng: ({lat}, {lng})")
                        return (float(lat), float(lng))

            logger.debug("No coordinates found in order detail")
            return None

        except Exception as e:
            logger.error(f"Error extracting coordinates from order detail: {e}")
            return None

    def update_single_order_coordinates(self, order_id: str, access_token: str, client_id: str = 'illa-frontdoor', app_context=None) -> bool:
        """
        Update coordinates for a single order by fetching detailed information

        Args:
            order_id: Order ID to update
            access_token: API access token
            client_id: Client ID for API calls
            app_context: Flask application context

        Returns:
            True if coordinates were successfully updated, False otherwise
        """
        # Handle application context for threaded execution
        if app_context:
            with app_context:
                return self._update_single_order_coordinates_impl(order_id, access_token, client_id)
        else:
            return self._update_single_order_coordinates_impl(order_id, access_token, client_id)

    def _update_single_order_coordinates_impl(self, order_id: str, access_token: str, client_id: str = 'illa-frontdoor') -> bool:
        """Internal implementation of coordinate update"""
        try:
            from models import db, Order

            # Get order from database
            order = Order.query.filter_by(id=order_id).first()
            if not order:
                logger.warning(f"Order {order_id} not found in database")
                return False

            # Skip if already has coordinates
            if order.location_latitude is not None and order.location_longitude is not None:
                logger.debug(f"Order {order_id} already has coordinates")
                return False

            # Get detailed order information from API
            order_detail = self.auth_service.get_order_detail(access_token, client_id, order_id)
            if not order_detail:
                logger.warning(f"Could not get order detail for {order_id}")
                return False

            # Extract coordinates
            coordinates = self.extract_coordinates_from_order_detail(order_detail)
            if not coordinates:
                logger.info(f"No coordinates available for order {order_id}")
                return False

            # Update order with coordinates
            lat, lng = coordinates
            order.location_latitude = lat
            order.location_longitude = lng

            db.session.commit()

            logger.info(f"Updated coordinates for order {order_id}: ({lat}, {lng})")
            return True

        except Exception as e:
            logger.error(f"Error updating coordinates for order {order_id}: {e}")
            try:
                from models import db
                db.session.rollback()
            except:
                pass
            return False

    def update_orders_coordinates_batch(self, order_ids: List[str], access_token: str,
                                       client_id: str = 'illa-frontdoor',
                                       max_workers: int = 1, app_context=None) -> Dict:
        """
        Update coordinates for multiple orders with rate limiting

        Note: Using max_workers=1 for now to avoid application context issues in threads

        Args:
            order_ids: List of order IDs to update
            access_token: API access token
            client_id: Client ID for API calls
            max_workers: Maximum number of concurrent workers (1 for now)
            app_context: Flask application context

        Returns:
            Dictionary with results summary
        """
        try:
            updated_count = 0
            failed_count = 0
            skipped_count = 0

            logger.info(f"Starting coordinate extraction for {len(order_ids)} orders")

            # Process orders sequentially to avoid context issues
            for i, order_id in enumerate(order_ids):
                try:
                    time.sleep(self.rate_limit_delay)  # Rate limiting

                    success = self.update_single_order_coordinates(order_id, access_token, client_id, app_context)

                    if success:
                        updated_count += 1
                        logger.info(f"Progress: {i+1}/{len(order_ids)} - Updated order {order_id}")
                    else:
                        # Check if it was skipped (already has coordinates) or failed
                        from models import Order
                        if app_context:
                            with app_context:
                                order = Order.query.filter_by(id=order_id).first()
                        else:
                            order = Order.query.filter_by(id=order_id).first()

                        if order and order.location_latitude is not None:
                            skipped_count += 1
                            logger.debug(f"Progress: {i+1}/{len(order_ids)} - Skipped order {order_id} (already has coordinates)")
                        else:
                            failed_count += 1
                            logger.warning(f"Progress: {i+1}/{len(order_ids)} - Failed to update order {order_id}")

                except Exception as e:
                    logger.error(f"Error processing order {order_id}: {e}")
                    failed_count += 1

            return {
                'success': True,
                'total_processed': len(order_ids),
                'updated_count': updated_count,
                'skipped_count': skipped_count,
                'failed_count': failed_count,
                'message': f'Processed {len(order_ids)} orders: {updated_count} updated, {skipped_count} skipped, {failed_count} failed'
            }

        except Exception as e:
            logger.error(f"Error in batch coordinate extraction: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_processed': 0,
                'updated_count': 0,
                'skipped_count': 0,
                'failed_count': 0
            }

    def update_orders_by_date(self, date: str, access_token: str,
                             client_id: str = 'illa-frontdoor',
                             limit: Optional[int] = None) -> Dict:
        """
        Update coordinates for all orders on a specific date

        Args:
            date: Date string (YYYY-MM-DD)
            access_token: API access token
            client_id: Client ID for API calls
            limit: Maximum number of orders to process (None for all)

        Returns:
            Dictionary with results summary
        """
        try:
            from models import Order
            from datetime import datetime

            # Parse date
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()

            # Get orders without coordinates for this date
            query = Order.query.filter(
                Order.date == date_obj,
                Order.location_latitude.is_(None)
            )

            if limit:
                query = query.limit(limit)

            orders = query.all()

            if not orders:
                return {
                    'success': True,
                    'message': f'No orders without coordinates found for date {date}',
                    'total_processed': 0,
                    'updated_count': 0,
                    'skipped_count': 0,
                    'failed_count': 0
                }

            order_ids = [order.id for order in orders]
            logger.info(f"Found {len(order_ids)} orders without coordinates for date {date}")

            # Process orders in batch
            result = self.update_orders_coordinates_batch(order_ids, access_token, client_id)
            result['date'] = date

            return result

        except Exception as e:
            logger.error(f"Error updating coordinates for date {date}: {e}")
            return {
                'success': False,
                'error': str(e),
                'date': date,
                'total_processed': 0,
                'updated_count': 0,
                'skipped_count': 0,
                'failed_count': 0
            }

def create_coordinate_extractor(auth_service):
    """Factory function to create coordinate extractor"""
    return CoordinateExtractor(auth_service)