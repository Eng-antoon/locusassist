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

    def apply_filters(self, filters_data):
        """
        Apply filters to order query and return filtered results

        Args:
            filters_data (dict): Filter criteria from the frontend

        Returns:
            dict: Filtered order results with metadata
        """
        try:
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

            return {
                'orders': paginated_orders,  # Only current page orders
                'total_count': total_filtered,  # Total filtered count
                'page': page,
                'per_page': per_page,
                'total_pages': max(1, (total_filtered + per_page - 1) // per_page),
                'status_totals': status_totals,
                'applied_filters': filters_data,
                'success': True
            }

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

    def _calculate_status_totals(self, orders):
        """Calculate order status totals"""
        status_totals = {}
        for order in orders:
            status = order.order_status
            status_totals[status] = status_totals.get(status, 0) + 1
        return status_totals


# Global filter service instance
filter_service = OrderFilterService()