"""
Enhanced Order Filtering System
Provides backend-driven filtering with dynamic filter generation
"""
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func, distinct
from models import db, Order, OrderLineItem, ValidationResult
import json


class OrderFilterService:
    """Service class for handling order filtering operations"""

    def __init__(self):
        self.available_filters = self._generate_available_filters()
        # Cache for filter results to improve performance
        self._filter_cache = {}
        self._cache_timeout = 300  # 5 minutes cache timeout

    def _generate_available_filters(self):
        """Dynamically generate available filter options based on database schema"""
        filters = {
            'basic': {
                'date': {
                    'type': 'date_range',
                    'label': 'Date Range',
                    'field': 'date',
                    'required': False
                },
                'order_status': {
                    'type': 'multi_select',
                    'label': 'Order Status',
                    'field': 'order_status',
                    'options': self._get_order_status_options(),
                    'required': False
                }
            },
            'location': {
                'location_name': {
                    'type': 'text',
                    'label': 'Location Name',
                    'field': 'location_name',
                    'required': False
                },
                'location_city': {
                    'type': 'multi_select',
                    'label': 'City',
                    'field': 'location_city',
                    'options': self._get_city_options(),
                    'required': False
                },
                'location_country_code': {
                    'type': 'multi_select',
                    'label': 'Country',
                    'field': 'location_country_code',
                    'options': self._get_country_options(),
                    'required': False
                }
            },
            'delivery': {
                'rider_name': {
                    'type': 'multi_select',
                    'label': 'Rider',
                    'field': 'rider_name',
                    'options': self._get_rider_options(),
                    'required': False
                },
                'vehicle_registration': {
                    'type': 'text',
                    'label': 'Vehicle Registration',
                    'field': 'vehicle_registration',
                    'required': False
                },
                'completed_on': {
                    'type': 'date_range',
                    'label': 'Completion Date Range',
                    'field': 'completed_on',
                    'required': False
                }
            },
            'validation': {
                'has_validation': {
                    'type': 'select',
                    'label': 'Validation Status',
                    'field': 'validation_status',
                    'options': [
                        {'value': 'all', 'label': 'All Orders'},
                        {'value': 'validated', 'label': 'Has Validation'},
                        {'value': 'unvalidated', 'label': 'No Validation'},
                        {'value': 'valid', 'label': 'Valid Only'},
                        {'value': 'invalid', 'label': 'Invalid Only'},
                        {'value': 'no_document', 'label': 'No Document Detected'},
                        {'value': 'has_issues', 'label': 'Has Issues'}
                    ],
                    'required': False
                },
                'confidence_score': {
                    'type': 'range',
                    'label': 'Confidence Score Range',
                    'field': 'confidence_score',
                    'min': 0,
                    'max': 1,
                    'step': 0.1,
                    'required': False
                }
            },
            'line_items': {
                'sku_id': {
                    'type': 'text',
                    'label': 'SKU ID',
                    'field': 'sku_id',
                    'required': False
                },
                'item_name': {
                    'type': 'text',
                    'label': 'Item Name',
                    'field': 'item_name',
                    'required': False
                },
                'quantity_range': {
                    'type': 'number_range',
                    'label': 'Quantity Range',
                    'field': 'quantity',
                    'required': False
                }
            },
            'advanced': {
                'client_id': {
                    'type': 'multi_select',
                    'label': 'Client ID',
                    'field': 'client_id',
                    'options': self._get_client_options(),
                    'required': False
                },
                'search': {
                    'type': 'text',
                    'label': 'Global Search',
                    'field': 'search',
                    'placeholder': 'Search order ID, location, rider...',
                    'required': False
                }
            }
        }
        return filters

    def _get_order_status_options(self):
        """Get distinct order status values from database"""
        try:
            statuses = db.session.query(distinct(Order.order_status)).filter(
                Order.order_status.isnot(None)
            ).all()
            return [{'value': status[0], 'label': status[0].title()} for status in statuses]
        except Exception:
            return [
                {'value': 'COMPLETED', 'label': 'Completed'},
                {'value': 'EXECUTING', 'label': 'Executing'},
                {'value': 'CANCELLED', 'label': 'Cancelled'},
                {'value': 'ASSIGNED', 'label': 'Assigned'},
                {'value': 'OPEN', 'label': 'Open'},
                {'value': 'PARKED', 'label': 'Parked'},
                {'value': 'PLANNING', 'label': 'Planning'},
                {'value': 'PLANNED', 'label': 'Planned'}
            ]

    def _get_city_options(self):
        """Get distinct city values from database"""
        try:
            cities = db.session.query(distinct(Order.location_city)).filter(
                Order.location_city.isnot(None)
            ).order_by(Order.location_city).limit(50).all()
            return [{'value': city[0], 'label': city[0]} for city in cities]
        except Exception:
            return []

    def _get_country_options(self):
        """Get distinct country values from database"""
        try:
            countries = db.session.query(distinct(Order.location_country_code)).filter(
                Order.location_country_code.isnot(None)
            ).order_by(Order.location_country_code).all()
            return [{'value': country[0], 'label': country[0]} for country in countries]
        except Exception:
            return []

    def _get_rider_options(self):
        """Get distinct rider names from database"""
        try:
            riders = db.session.query(distinct(Order.rider_name)).filter(
                Order.rider_name.isnot(None)
            ).order_by(Order.rider_name).limit(50).all()
            return [{'value': rider[0], 'label': rider[0]} for rider in riders]
        except Exception:
            return []

    def _get_client_options(self):
        """Get distinct client IDs from database"""
        try:
            clients = db.session.query(distinct(Order.client_id)).filter(
                Order.client_id.isnot(None)
            ).order_by(Order.client_id).limit(20).all()
            return [{'value': client[0], 'label': client[0]} for client in clients]
        except Exception:
            return []

    def get_available_filters(self):
        """Return all available filter configurations"""
        return self.available_filters

    def _get_cache_key(self, filters_data):
        """Generate cache key from filter data"""
        import hashlib
        import json

        # Create a sorted dictionary for consistent cache keys
        cache_data = {}
        for key, value in sorted(filters_data.items()):
            if key != 'page':  # Don't include page in cache key for result reuse
                cache_data[key] = value

        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()

    def _is_cache_valid(self, cache_entry):
        """Check if cache entry is still valid"""
        import time
        return time.time() - cache_entry['timestamp'] < self._cache_timeout

    def apply_filters(self, filters_data):
        """
        Apply filters to order query and return filtered results
        Handles day-by-day API fetching for date ranges with missing database data
        Uses caching for improved performance

        Args:
            filters_data (dict): Filter criteria from the frontend

        Returns:
            dict: Filtered order results with metadata
        """
        try:
            import time

            # Generate cache key (excluding pagination)
            cache_key = self._get_cache_key(filters_data)

            # Check cache first (for non-paginated results)
            if cache_key in self._filter_cache and self._is_cache_valid(self._filter_cache[cache_key]):
                cached_result = self._filter_cache[cache_key]['data'].copy()

                # Apply pagination to cached results
                page = int(filters_data.get('page', 1))
                per_page = int(filters_data.get('per_page', 50))

                # Apply pagination to cached full results
                total_filtered = len(cached_result['full_orders'])
                start_index = (page - 1) * per_page
                end_index = start_index + per_page
                paginated_orders = cached_result['full_orders'][start_index:end_index]

                cached_result.update({
                    'orders': paginated_orders,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': max(1, (total_filtered + per_page - 1) // per_page),
                    'from_cache': True
                })

                return cached_result
            from datetime import datetime, timedelta
            from app.auth import LocusAuth
            from flask import current_app

            # Check if we need to fetch missing data from API
            date_from = filters_data.get('date_from')
            date_to = filters_data.get('date_to')

            if date_from and date_to:
                # Check for missing data and fetch if needed
                self._ensure_data_for_date_range(date_from, date_to, filters_data, current_app.config)
            elif date_from and not date_to:
                # Single date filtering
                self._ensure_data_for_date_range(date_from, date_from, filters_data, current_app.config)

            # Start with base query and order by date DESC for recent orders first
            query = db.session.query(Order).order_by(Order.date.desc(), Order.created_at.desc())

            # Apply basic filters
            query = self._apply_basic_filters(query, filters_data)

            # Apply location filters
            query = self._apply_location_filters(query, filters_data)

            # Apply delivery filters
            query = self._apply_delivery_filters(query, filters_data)

            # Apply line item filters
            query = self._apply_line_item_filters(query, filters_data)

            # Apply advanced search
            query = self._apply_search_filter(query, filters_data)

            # Execute query to get all filtered results (no pagination yet)
            orders = query.all()

            # Convert to dict format
            orders_data = [order.to_dict() for order in orders]

            # Apply validation filters (post-query filtering for complex validation logic)
            filtered_orders = self._apply_validation_filters(orders_data, filters_data)

            # Get pagination parameters
            page = int(filters_data.get('page', 1))
            per_page = int(filters_data.get('per_page', 50))

            # Apply pagination to final filtered results
            total_filtered = len(filtered_orders)
            start_index = (page - 1) * per_page
            end_index = start_index + per_page
            paginated_orders = filtered_orders[start_index:end_index]


            # Calculate status totals from all filtered orders (not just current page)
            status_totals = {}
            for order in filtered_orders:
                status = order.get('order_status')
                if status:
                    status_totals[status] = status_totals.get(status, 0) + 1

            # Calculate day-specific totals for date range filtering
            day_totals = self._calculate_day_totals(filtered_orders, filters_data)

            # Get date range info for display
            date_info = self._get_date_range_info(filters_data)

            # Prepare result
            result = {
                'orders': paginated_orders,  # Only current page orders
                'full_orders': filtered_orders,  # Store full results for cache
                'total_count': total_filtered,  # Total filtered count
                'page': page,
                'per_page': per_page,
                'total_pages': max(1, (total_filtered + per_page - 1) // per_page),
                'status_totals': status_totals,
                'day_totals': day_totals,
                'date_info': date_info,
                'applied_filters': filters_data,
                'success': True
            }

            # Cache the result (excluding pagination-specific data)
            cache_entry = {
                'data': {
                    'full_orders': filtered_orders,
                    'total_count': total_filtered,
                    'status_totals': status_totals,
                    'day_totals': day_totals,
                    'date_info': date_info,
                    'applied_filters': filters_data,
                    'success': True
                },
                'timestamp': time.time()
            }
            self._filter_cache[cache_key] = cache_entry

            # Clean up old cache entries (keep cache size manageable)
            if len(self._filter_cache) > 50:
                oldest_key = min(self._filter_cache.keys(),
                                key=lambda k: self._filter_cache[k]['timestamp'])
                del self._filter_cache[oldest_key]

            return result

        except Exception as e:
            import traceback
            print(f"Error applying filters: {str(e)}")
            print(traceback.format_exc())
            return {
                'orders': [],
                'total_count': 0,
                'error': str(e),
                'success': False
            }

    def _apply_basic_filters(self, query, filters_data):
        """Apply basic filters like date and order status"""

        # Date filter
        if filters_data.get('date_from'):
            try:
                date_from = datetime.strptime(filters_data['date_from'], '%Y-%m-%d').date()
                query = query.filter(Order.date >= date_from)
            except ValueError:
                pass

        if filters_data.get('date_to'):
            try:
                date_to = datetime.strptime(filters_data['date_to'], '%Y-%m-%d').date()
                query = query.filter(Order.date <= date_to)
            except ValueError:
                pass

        # Single date filter (for backward compatibility)
        if filters_data.get('date') and not filters_data.get('date_from'):
            try:
                single_date = datetime.strptime(filters_data['date'], '%Y-%m-%d').date()
                query = query.filter(Order.date == single_date)
            except ValueError:
                pass

        # Order status filter
        if filters_data.get('order_status') and filters_data['order_status'] != 'all':
            if isinstance(filters_data['order_status'], list):
                query = query.filter(Order.order_status.in_(filters_data['order_status']))
            else:
                query = query.filter(Order.order_status == filters_data['order_status'].upper())

        return query

    def _apply_location_filters(self, query, filters_data):
        """Apply location-based filters"""

        if filters_data.get('location_name'):
            query = query.filter(Order.location_name.ilike(f"%{filters_data['location_name']}%"))

        if filters_data.get('location_city'):
            if isinstance(filters_data['location_city'], list):
                query = query.filter(Order.location_city.in_(filters_data['location_city']))
            else:
                query = query.filter(Order.location_city == filters_data['location_city'])

        if filters_data.get('location_country_code'):
            if isinstance(filters_data['location_country_code'], list):
                query = query.filter(Order.location_country_code.in_(filters_data['location_country_code']))
            else:
                query = query.filter(Order.location_country_code == filters_data['location_country_code'])

        return query

    def _apply_delivery_filters(self, query, filters_data):
        """Apply delivery-related filters"""

        if filters_data.get('rider_name'):
            if isinstance(filters_data['rider_name'], list):
                query = query.filter(Order.rider_name.in_(filters_data['rider_name']))
            else:
                query = query.filter(Order.rider_name.ilike(f"%{filters_data['rider_name']}%"))

        if filters_data.get('vehicle_registration'):
            query = query.filter(Order.vehicle_registration.ilike(f"%{filters_data['vehicle_registration']}%"))

        if filters_data.get('completed_on_from'):
            try:
                completed_from = datetime.strptime(filters_data['completed_on_from'], '%Y-%m-%d')
                query = query.filter(Order.completed_on >= completed_from)
            except ValueError:
                pass

        if filters_data.get('completed_on_to'):
            try:
                completed_to = datetime.strptime(filters_data['completed_on_to'], '%Y-%m-%d')
                # Add 1 day and subtract 1 second to include the entire end date
                completed_to = completed_to + timedelta(days=1) - timedelta(seconds=1)
                query = query.filter(Order.completed_on <= completed_to)
            except ValueError:
                pass

        return query

    def _apply_line_item_filters(self, query, filters_data):
        """Apply line item related filters"""

        if filters_data.get('sku_id') or filters_data.get('item_name') or filters_data.get('quantity_min') or filters_data.get('quantity_max'):
            # Join with line items table
            query = query.join(OrderLineItem)

            if filters_data.get('sku_id'):
                query = query.filter(OrderLineItem.sku_id.ilike(f"%{filters_data['sku_id']}%"))

            if filters_data.get('item_name'):
                query = query.filter(OrderLineItem.name.ilike(f"%{filters_data['item_name']}%"))

            if filters_data.get('quantity_min'):
                try:
                    min_qty = int(filters_data['quantity_min'])
                    query = query.filter(OrderLineItem.quantity >= min_qty)
                except ValueError:
                    pass

            if filters_data.get('quantity_max'):
                try:
                    max_qty = int(filters_data['quantity_max'])
                    query = query.filter(OrderLineItem.quantity <= max_qty)
                except ValueError:
                    pass

            # Use distinct to avoid duplicate orders
            query = query.distinct()

        return query

    def _apply_search_filter(self, query, filters_data):
        """Apply global search filter"""

        if filters_data.get('search'):
            search_term = filters_data['search']
            # Search across multiple fields
            search_filter = or_(
                Order.id.ilike(f"%{search_term}%"),
                Order.location_name.ilike(f"%{search_term}%"),
                Order.location_address.ilike(f"%{search_term}%"),
                Order.location_city.ilike(f"%{search_term}%"),
                Order.rider_name.ilike(f"%{search_term}%"),
                Order.vehicle_registration.ilike(f"%{search_term}%"),
                Order.client_id.ilike(f"%{search_term}%")
            )
            query = query.filter(search_filter)

        return query

    def _apply_validation_filters(self, orders_data, filters_data):
        """Apply validation-related filters (post-query)"""

        validation_filter = filters_data.get('has_validation', 'all')

        if validation_filter == 'all':
            return orders_data

        filtered_orders = []

        for order in orders_data:
            # Get validation results for this order
            validation_results = db.session.query(ValidationResult).filter(
                ValidationResult.order_id == order['id']
            ).order_by(ValidationResult.validation_date.desc()).first()

            include_order = False

            if validation_filter == 'validated':
                include_order = validation_results is not None
            elif validation_filter == 'unvalidated':
                include_order = validation_results is None
            elif validation_filter == 'valid':
                include_order = validation_results is not None and validation_results.is_valid
            elif validation_filter == 'invalid':
                include_order = validation_results is not None and not validation_results.is_valid
            elif validation_filter == 'no_document':
                include_order = validation_results is not None and validation_results.has_document is False
            elif validation_filter == 'has_issues':
                include_order = validation_results is not None and not validation_results.is_valid

            # Apply confidence score filter
            if include_order and filters_data.get('confidence_min'):
                try:
                    min_confidence = float(filters_data['confidence_min'])
                    if validation_results and validation_results.confidence_score is not None:
                        include_order = validation_results.confidence_score >= min_confidence
                    else:
                        include_order = False
                except ValueError:
                    pass

            if include_order and filters_data.get('confidence_max'):
                try:
                    max_confidence = float(filters_data['confidence_max'])
                    if validation_results and validation_results.confidence_score is not None:
                        include_order = validation_results.confidence_score <= max_confidence
                    else:
                        include_order = False
                except ValueError:
                    pass

            if include_order:
                filtered_orders.append(order)

        return filtered_orders

    def _ensure_data_for_date_range(self, date_from, date_to, filters_data, config=None):
        """
        Ensure data exists in database for the date range, fetch from API if missing
        """
        try:
            from datetime import datetime, timedelta
            from app.auth import LocusAuth
            from flask import current_app
            import logging

            logger = logging.getLogger(__name__)

            # Parse dates
            start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            end_date = datetime.strptime(date_to, '%Y-%m-%d').date()

            # Generate list of dates in the range
            current_date = start_date
            dates_to_check = []
            while current_date <= end_date:
                dates_to_check.append(current_date.strftime('%Y-%m-%d'))
                current_date += timedelta(days=1)

            logger.info(f"Checking data for date range: {dates_to_check}")

            # Check which dates have data in database
            missing_dates = []
            for date_str in dates_to_check:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                count = db.session.query(Order).filter(Order.date == date_obj).count()
                if count == 0:
                    missing_dates.append(date_str)
                    logger.info(f"No data found for date {date_str}, adding to fetch list")
                else:
                    logger.info(f"Found {count} orders for date {date_str} in database")

            if not missing_dates:
                logger.info("All dates have data in database, no API fetch needed")
                return

            logger.info(f"Fetching data from API for missing dates: {missing_dates}")

            # Get app config and initialize auth
            if config is None:
                config = getattr(current_app, 'config', None)
            if not config or not hasattr(config, 'BEARER_TOKEN'):
                logger.warning("No bearer token available, skipping API fetch")
                return

            locus_auth = LocusAuth(config)

            # Parse order status filter for API
            order_statuses = None
            if filters_data.get('order_status') and filters_data['order_status'] != 'all':
                if isinstance(filters_data['order_status'], list):
                    order_statuses = filters_data['order_status']
                else:
                    order_statuses = [filters_data['order_status']]

            # Fetch data for each missing date
            total_fetched = 0
            for date_str in missing_dates:
                try:
                    logger.info(f"Fetching data for date {date_str}")
                    orders_data = locus_auth.get_orders(
                        config.BEARER_TOKEN,
                        'illa-frontdoor',
                        date=date_str,
                        fetch_all=True,
                        order_statuses=order_statuses
                    )

                    if orders_data and orders_data.get('orders'):
                        count = len(orders_data['orders'])
                        total_fetched += count
                        logger.info(f"Fetched {count} orders for date {date_str}")

                        # Cache the data to database
                        locus_auth.cache_orders_to_database(orders_data, 'illa-frontdoor', date_str)
                        logger.info(f"Cached {count} orders for date {date_str} to database")
                    else:
                        logger.info(f"No orders found for date {date_str}")

                except Exception as e:
                    logger.error(f"Error fetching data for date {date_str}: {e}")
                    continue

            logger.info(f"Day-by-day fetch completed: {total_fetched} orders fetched across {len(missing_dates)} dates")

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error in _ensure_data_for_date_range: {e}")
            # Don't raise the error - just log it and continue with existing data

    def refresh_date_range_data(self, date_from, date_to, filters_data, force_refresh=False, config=None):
        """
        Refresh data for a date range by fetching fresh data from API day by day
        """
        try:
            from datetime import datetime, timedelta
            from app.auth import LocusAuth
            from flask import current_app
            import logging

            logger = logging.getLogger(__name__)

            # Parse dates
            start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            end_date = datetime.strptime(date_to, '%Y-%m-%d').date()

            # Generate list of dates in the range
            current_date = start_date
            dates_to_refresh = []
            while current_date <= end_date:
                dates_to_refresh.append(current_date.strftime('%Y-%m-%d'))
                current_date += timedelta(days=1)

            logger.info(f"Refreshing data for date range: {dates_to_refresh}")

            # Get app config and initialize auth
            if config is None:
                config = getattr(current_app, 'config', None)
            if not config or not hasattr(config, 'BEARER_TOKEN'):
                logger.error("No bearer token available for refresh")
                return {'success': False, 'error': 'No authentication token available'}

            locus_auth = LocusAuth(config)

            # Parse order status filter for API
            order_statuses = None
            if filters_data.get('order_status') and filters_data['order_status'] != 'all':
                if isinstance(filters_data['order_status'], list):
                    order_statuses = filters_data['order_status']
                else:
                    order_statuses = [filters_data['order_status']]

            # Refresh data for each date
            total_refreshed = 0
            refresh_results = []

            for date_str in dates_to_refresh:
                try:
                    logger.info(f"Refreshing data for date {date_str}")

                    if force_refresh:
                        # Force refresh: clear cache and fetch fresh
                        orders_data = locus_auth.refresh_orders_force_fresh(
                            config.BEARER_TOKEN,
                            'illa-frontdoor',
                            date=date_str,
                            fetch_all=True
                        )
                    else:
                        # Smart refresh: merge new data with existing
                        orders_data = locus_auth.refresh_orders_smart_merge(
                            config.BEARER_TOKEN,
                            'illa-frontdoor',
                            date=date_str,
                            fetch_all=True,
                            order_statuses=order_statuses
                        )

                    if orders_data and orders_data.get('orders'):
                        count = len(orders_data['orders'])
                        total_refreshed += count
                        refresh_results.append({
                            'date': date_str,
                            'count': count,
                            'success': True
                        })
                        logger.info(f"Refreshed {count} orders for date {date_str}")
                    else:
                        refresh_results.append({
                            'date': date_str,
                            'count': 0,
                            'success': True,
                            'message': 'No orders found'
                        })
                        logger.info(f"No orders found for date {date_str}")

                except Exception as e:
                    refresh_results.append({
                        'date': date_str,
                        'count': 0,
                        'success': False,
                        'error': str(e)
                    })
                    logger.error(f"Error refreshing data for date {date_str}: {e}")
                    continue

            success_count = sum(1 for r in refresh_results if r['success'])

            return {
                'success': True,
                'total_orders_refreshed': total_refreshed,
                'dates_processed': len(dates_to_refresh),
                'dates_successful': success_count,
                'dates_failed': len(dates_to_refresh) - success_count,
                'results': refresh_results,
                'message': f'Refreshed {total_refreshed} orders across {success_count}/{len(dates_to_refresh)} dates'
            }

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error in refresh_date_range_data: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _calculate_day_totals(self, orders, filters_data):
        """
        Calculate totals grouped by day for the filtered orders
        """
        try:
            from datetime import datetime
            from collections import defaultdict

            day_totals = defaultdict(lambda: {
                'total_orders': 0,
                'status_breakdown': defaultdict(int)
            })

            for order in orders:
                # Get the order date
                order_date = order.get('date')
                if not order_date:
                    # Try to extract from created_at or other date fields
                    created_at = order.get('created_at')
                    if created_at:
                        if isinstance(created_at, str):
                            try:
                                order_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date().isoformat()
                            except:
                                order_date = 'unknown'
                        else:
                            order_date = created_at.date().isoformat()
                    else:
                        order_date = 'unknown'
                elif hasattr(order_date, 'isoformat'):
                    order_date = order_date.isoformat()
                elif not isinstance(order_date, str):
                    order_date = str(order_date)

                # Increment totals for this day
                day_totals[order_date]['total_orders'] += 1

                # Increment status breakdown for this day
                status = order.get('order_status', 'UNKNOWN')
                day_totals[order_date]['status_breakdown'][status] += 1

            # Convert defaultdict to regular dict for JSON serialization
            result = {}
            for date, totals in day_totals.items():
                result[date] = {
                    'total_orders': totals['total_orders'],
                    'status_breakdown': dict(totals['status_breakdown'])
                }

            return result

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error calculating day totals: {e}")
            return {}

    def _get_date_range_info(self, filters_data):
        """
        Get formatted date range information for display
        """
        try:
            from datetime import datetime

            date_from = filters_data.get('date_from')
            date_to = filters_data.get('date_to')

            if not date_from and not date_to:
                # Default to today
                today = datetime.now().strftime('%Y-%m-%d')
                return {
                    'single_date': today,
                    'display': today,
                    'is_range': False
                }

            if date_from and date_to:
                if date_from == date_to:
                    # Single date
                    return {
                        'single_date': date_from,
                        'display': date_from,
                        'is_range': False
                    }
                else:
                    # Date range
                    try:
                        from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                        to_obj = datetime.strptime(date_to, '%Y-%m-%d')

                        from_formatted = from_obj.strftime('%b %d, %Y')
                        to_formatted = to_obj.strftime('%b %d, %Y')

                        return {
                            'date_from': date_from,
                            'date_to': date_to,
                            'display': f"{from_formatted} - {to_formatted}",
                            'is_range': True
                        }
                    except ValueError:
                        return {
                            'display': f"{date_from} - {date_to}",
                            'is_range': True
                        }

            elif date_from:
                return {
                    'single_date': date_from,
                    'display': date_from,
                    'is_range': False
                }

            return {
                'display': 'All Dates',
                'is_range': False
            }

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting date range info: {e}")
            return {
                'display': 'Date Range',
                'is_range': False
            }

    def _calculate_status_totals(self, orders):
        """Calculate order status totals"""
        status_totals = {}
        for order in orders:
            status = order.order_status
            status_totals[status] = status_totals.get(status, 0) + 1
        return status_totals


# Global filter service instance
filter_service = OrderFilterService()