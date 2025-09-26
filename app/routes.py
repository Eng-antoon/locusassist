from flask import render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
import io

from models import ValidationResult, Order
from app.auth import LocusAuth
from app.validators import GoogleAIValidator
from app.utils import rate_limit_api_call, api_rate_limiter
from app.filters import filter_service

logger = logging.getLogger(__name__)

def transform_task_to_order_format(task_data):
    """Transform task API response to match expected order format"""
    try:
        # Create a unified order structure from task data
        order_data = {}

        # Basic task information - CRITICAL: Use taskStatus as the primary status
        order_data['id'] = task_data.get('taskId')
        order_data['order_status'] = task_data.get('taskStatus', 'UNKNOWN')  # This is the correct status
        order_data['client_id'] = task_data.get('clientId')

        # IMPORTANT: Also set these aliases for template compatibility
        order_data['orderStatus'] = task_data.get('taskStatus', 'UNKNOWN')
        order_data['effective_status'] = task_data.get('taskStatus', 'UNKNOWN')

        # Get cancellation information from visits
        cancelled_visit = None
        cancellation_reason = None

        # Look through all visits to find cancellation information
        for visit in task_data.get('visits', []):
            if visit.get('cancelledReason'):
                cancelled_visit = visit
                cancellation_reason = visit.get('cancelledReason')
                break

        # Set cancellation information
        order_data['cancellation_reason'] = cancellation_reason
        if cancelled_visit:
            order_data['cancelled_source'] = cancelled_visit.get('cancelledSource')

        # Log for debugging
        logger.info(f"Task {task_data.get('taskId')}: status={task_data.get('taskStatus')}, cancellation={cancellation_reason}")

        # Extract timing information
        order_data['creation_time'] = task_data.get('creationTime')
        order_data['completion_time'] = task_data.get('completionTime')

        # Extract location information from visits
        customer_visit = None
        for visit in task_data.get('visits', []):
            if visit.get('visitType') == 'DROP':
                customer_visit = visit
                break

        if customer_visit:
            chosen_location = customer_visit.get('chosenLocation', {})
            address = chosen_location.get('address', {})

            # Create location structure
            order_data['location'] = {
                'id': customer_visit.get('locationId', {}).get('locationId'),
                'name': address.get('placeName', ''),
                'status': 'ACTIVE',
                'address': {
                    'formattedAddress': address.get('formattedAddress', ''),
                    'city': address.get('city', ''),
                    'state': address.get('state', ''),
                    'countryCode': address.get('countryCode', ''),
                    'pincode': address.get('pincode', '')
                },
                'latLng': chosen_location.get('geometry', {}).get('latLng', {})
            }

            # Extract performance metrics
            order_data['sla_status'] = customer_visit.get('slaStatus')
            order_data['tardiness'] = customer_visit.get('tardiness')
            order_data['sla_breached'] = customer_visit.get('slaBreached')

            # Extract tour information
            tour_id_info = customer_visit.get('tourId', {})
            order_data['tour_id'] = tour_id_info.get('tourId')
            order_data['batch_id'] = customer_visit.get('batchId')

            # Extract assigned user information
            assigned_user = customer_visit.get('assignedUser', {})
            order_data['rider_id'] = assigned_user.get('userId')

            # Extract custom fields
            custom_fields = customer_visit.get('customFields', {})
            order_data['custom_fields'] = custom_fields

        # Extract line items from orderDetail
        order_detail = task_data.get('orderDetail', {})
        if order_detail:
            line_items = order_detail.get('lineItems', [])

            # Transform line items to match expected format
            transformed_items = []
            for item in line_items:
                transformed_item = {
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'quantity': item.get('quantity', 0),
                    'description': item.get('description', ''),
                    'quantityUnit': 'PIECES',  # Default
                    'handlingUnit': 'PIECES',  # Default
                    'transactionStatus': item.get('transactionStatus', {})
                }
                transformed_items.append(transformed_item)

            order_data['lineItems'] = transformed_items

            # Create metadata structure similar to original order format
            order_data['orderMetadata'] = {
                'lineItems': transformed_items
            }

        # Store original task data for reference
        order_data['_original_task_data'] = task_data
        order_data['_is_task_format'] = True

        return order_data

    except Exception as e:
        logger.error(f"Error transforming task data: {e}")
        return task_data  # Return original if transformation fails

def store_order_from_api_data(order_data, date_str):
    """Store order data from API into database"""
    from models import db
    from datetime import datetime
    import json

    try:
        # Parse the date
        order_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Create new Order instance
        new_order = Order(
            id=order_data.get('id'),
            client_id=order_data.get('client_id', 'illa-frontdoor'),
            date=order_date,
            order_status=order_data.get('order_status', 'UNKNOWN'),
        )

        # Location data
        location = order_data.get('location', {})
        if location:
            new_order.location_name = location.get('name', '')
            address = location.get('address', {})
            new_order.location_address = address.get('formattedAddress', '')
            new_order.location_city = address.get('city', '')
            new_order.location_country_code = address.get('countryCode', '')

        # Cancellation information
        new_order.cancellation_reason = order_data.get('cancellation_reason')

        # Tour information
        new_order.tour_id = order_data.get('tour_id')
        new_order.rider_id = order_data.get('rider_id')
        new_order.batch_id = order_data.get('batch_id')

        # Performance metrics
        new_order.sla_status = order_data.get('sla_status')
        new_order.tardiness = order_data.get('tardiness')

        # Timing
        if order_data.get('completion_time'):
            try:
                new_order.completed_on = datetime.fromisoformat(order_data['completion_time'].replace('Z', '+00:00'))
            except:
                pass

        # Custom fields
        if order_data.get('custom_fields'):
            new_order.custom_fields = json.dumps(order_data['custom_fields'])

        # Raw data
        new_order.raw_data = json.dumps(order_data)

        # Add to session and commit
        db.session.add(new_order)
        db.session.commit()

        logger.info(f"Successfully stored order {order_data.get('id')} from API data")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error storing order from API data: {e}")
        raise

def register_routes(app, config):
    """Register all Flask routes"""

    # Initialize auth and validator
    locus_auth = LocusAuth(config)
    ai_validator = GoogleAIValidator(config)

    def has_grn_document(order_data):
        """Check if an order has a GRN document available"""
        try:
            order_id = order_data.get('id', 'unknown')

            # Try different possible paths where the GRN might be stored
            possible_paths = [
                # Direct path
                ['orderMetadata', 'customerProofOfCompletion', 'Proof Of Delivery Document', 'Proof Of Delivery Document'],
                ['orderMetadata', 'customerProofOfCompletion', 'proofOfDeliveryDocument'],
                ['orderMetadata', 'customerProofOfCompletion', 'deliveryDocument'],
                # Alternative paths
                ['proofOfDelivery', 'document'],
                ['proofOfDelivery', 'documentUrl'],
                ['proofOfDelivery', 'deliveryDocument'],
                ['customerProofOfCompletion', 'deliveryDocument'],
                ['customerProofOfCompletion', 'document'],
            ]

            # Try each possible path
            for path in possible_paths:
                current_data = order_data
                try:
                    for key in path:
                        current_data = current_data[key]
                    if isinstance(current_data, str) and current_data.startswith('http'):
                        logger.info(f"Order {order_id}: Found GRN document at path: {' -> '.join(path)}")
                        return True
                except (KeyError, TypeError):
                    continue

            # If still no URL, try to find any URL in the proof data
            proof_data = order_data.get('orderMetadata', {}).get('customerProofOfCompletion', {})
            if proof_data:
                def find_urls_recursive(obj, path=""):
                    urls = []
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            new_path = f"{path}.{key}" if path else key
                            if isinstance(value, str) and value.startswith('http'):
                                urls.append((new_path, value))
                            elif isinstance(value, (dict, list)):
                                urls.extend(find_urls_recursive(value, new_path))
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj):
                            new_path = f"{path}[{i}]"
                            urls.extend(find_urls_recursive(item, new_path))
                    return urls

                found_urls = find_urls_recursive(proof_data)
                if found_urls:
                    logger.info(f"Order {order_id}: Found GRN document via recursive search: {found_urls[0]}")
                    return True

            logger.info(f"Order {order_id}: No GRN document found")
            return False
        except Exception as e:
            logger.error(f"Error checking GRN document for order: {e}")
            return False

    def validate_single_order_worker(order_basic, date, force_reprocess=False):
        """Worker function to validate a single order in a thread"""
        # Create application context for database operations in thread
        with app.app_context():
            try:
                order_id = order_basic.get('id')
                if not order_id:
                    return {
                        'order_id': 'unknown',
                        'success': False,
                        'error': 'No order ID found',
                        'is_valid': False
                    }

                # Get detailed order data
                order_detail_data = locus_auth.get_order_detail(
                    config.BEARER_TOKEN,
                    'illa-frontdoor',
                    order_id
                )

                if not order_detail_data:
                    return {
                        'order_id': order_id,
                        'success': False,
                        'error': 'Could not fetch order details',
                        'is_valid': False
                    }

                # Check if order has GRN document first
                if not has_grn_document(order_detail_data):
                    return {
                        'order_id': order_id,
                        'success': False,
                        'error': 'Order has no GRN document - skipped from validation',
                        'is_valid': False,
                        'skipped_no_grn': True
                    }

                # Get GRN document URL
                grn_url = None
                if (order_detail_data.get('orderMetadata', {}).get('customerProofOfCompletion', {}).get('Proof Of Delivery Document')):
                    grn_url = order_detail_data['orderMetadata']['customerProofOfCompletion']['Proof Of Delivery Document']['Proof Of Delivery Document']

                if not grn_url:
                    return {
                        'order_id': order_id,
                        'success': False,
                        'error': 'No GRN document found',
                        'is_valid': False
                    }

                # Check for existing validation result to avoid unnecessary API calls
                if not force_reprocess:
                    stored_result = ai_validator.get_stored_validation_result(order_id, grn_url)
                    if stored_result:
                        logger.info(f"Using stored validation result for order {order_id}")
                        stored_result['order_id'] = order_id
                        stored_result['from_cache'] = True
                        return stored_result

                # Validate using Google AI with rate limiting (only if not cached or forced reprocess)
                logger.info(f"Calling Google AI API for order {order_id}")

                # Apply rate limiting and concurrency control
                with api_rate_limiter:  # Limit concurrent API calls
                    rate_limit_api_call()  # Apply time-based rate limiting
                    validation_result = ai_validator.validate_grn_against_order(order_detail_data, grn_url)

                validation_result['order_id'] = order_id
                validation_result['from_cache'] = False
                return validation_result

            except Exception as e:
                logger.error(f"Error validating order {order_basic.get('id', 'unknown')} in worker thread: {e}")
                return {
                    'order_id': order_basic.get('id', 'unknown'),
                    'success': False,
                    'error': str(e),
                    'is_valid': False,
                    'from_cache': False
                }

    @app.route('/')
    def index():
        """Main route - directly show dashboard with provided token"""
        return redirect(url_for('dashboard'))

    @app.route('/dashboard')
    def dashboard():
        # Get filter parameters with caching support
        today = datetime.now().strftime("%Y-%m-%d")
        selected_date = request.args.get('date', today)
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        selected_order_status = request.args.get('order_status', 'all')

        # Determine the date range for filtering
        if date_from and date_to:
            # Date range filtering
            start_date = date_from
            end_date = date_to
            date_display = f"{date_from} to {date_to}" if date_from != date_to else date_from
        elif date_from:
            # Single date from date_from
            start_date = end_date = date_from
            date_display = date_from
        else:
            # Single date or today (backward compatibility)
            try:
                datetime.strptime(selected_date, "%Y-%m-%d")
                start_date = end_date = selected_date
                date_display = selected_date
            except ValueError:
                flash(f"Invalid date format: {selected_date}. Please use YYYY-MM-DD format.", "error")
                return redirect(url_for('dashboard', date=today))

        fetch_all = request.args.get('all', 'true').lower() == 'true'

        # Parse order status filter
        order_statuses = None
        if selected_order_status and selected_order_status.lower() != 'all':
            order_statuses = [selected_order_status.upper()]

        # Use filter service for cached data retrieval
        filter_data = {
            'date_from': start_date,
            'date_to': end_date,
            'order_status': selected_order_status if selected_order_status != 'all' else None
        }

        # Apply filters to get cached data
        filter_result = filter_service.apply_filters(filter_data)

        if filter_result.get('success', False):
            # Transform filter result to match expected orders_data format
            orders_data = {
                'orders': filter_result['orders'],
                'totalCount': filter_result['total_count'],
                'statusTotals': filter_result.get('status_totals', {}),
                'pagesFetched': 'Cached data'
            }
        else:
            # Fallback to API if filter service fails
            if start_date == end_date:
                # Single date - use existing API
                orders_data = locus_auth.get_orders(
                    config.BEARER_TOKEN,
                    'illa-frontdoor',
                    date=start_date,
                    fetch_all=fetch_all,
                    order_statuses=order_statuses
                )
            else:
                # Date range - aggregate data day by day
                orders_data = {'orders': [], 'totalCount': 0, 'statusTotals': {}}
                current_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()

                while current_date <= end_date_obj:
                    daily_data = locus_auth.get_orders(
                        config.BEARER_TOKEN,
                        'illa-frontdoor',
                        date=current_date.strftime('%Y-%m-%d'),
                        fetch_all=fetch_all,
                        order_statuses=order_statuses
                    )

                    if daily_data and daily_data.get('orders'):
                        orders_data['orders'].extend(daily_data['orders'])
                        orders_data['totalCount'] += len(daily_data['orders'])

                        # Aggregate status totals
                        for status, count in daily_data.get('statusTotals', {}).items():
                            orders_data['statusTotals'][status] = orders_data['statusTotals'].get(status, 0) + count

                    current_date += timedelta(days=1)

                orders_data['pagesFetched'] = f'Date range: {start_date} to {end_date}'

        # Enhance orders with validation summaries and GRN status
        if orders_data and orders_data.get('orders'):
            for order in orders_data['orders']:
                order_id = order.get('id')

                # Check if order has GRN document
                order['has_grn'] = has_grn_document(order)

                if order_id:
                    # Get validation summary for this order
                    validation_summary = ai_validator.get_stored_validation_result(order_id)
                    if validation_summary:
                        # Parse stored JSON fields if they're strings
                        try:
                            summary_data = json.loads(validation_summary.get('summary', '{}')) if isinstance(validation_summary.get('summary'), str) else validation_summary.get('summary', {})
                            discrepancies_data = json.loads(validation_summary.get('discrepancies', '[]')) if isinstance(validation_summary.get('discrepancies'), str) else validation_summary.get('discrepancies', [])
                        except json.JSONDecodeError:
                            summary_data = {}
                            discrepancies_data = []

                        # Default has_document to True for backward compatibility with older records
                        # Only set to False if explicitly stored as False
                        has_document = validation_summary.get('has_document')
                        if has_document is None:
                            has_document = True  # Default for older records

                        order['validation_summary'] = {
                            'has_validation': True,
                            'is_valid': validation_summary.get('is_valid', False),
                            'has_document': has_document,
                            'confidence_score': validation_summary.get('confidence_score', 0),
                            'validation_date': validation_summary.get('validation_date'),
                            'processing_time': validation_summary.get('processing_time', 0),
                            'summary': summary_data,
                            'discrepancies_count': len(discrepancies_data),
                            'gtins_verified': summary_data.get('gtins_verified', 0),
                            'gtins_matched': summary_data.get('gtins_matched', 0)
                        }
                    else:
                        order['validation_summary'] = {
                            'has_validation': False
                        }

        return render_template('dashboard.html',
                             orders_data=orders_data,
                             selected_date=selected_date,
                             date_from=date_from,
                             date_to=date_to,
                             date_display=date_display,
                             selected_order_status=selected_order_status,
                             username='Amin',
                             fetch_all=fetch_all)

    @app.route('/api/orders')
    def api_orders():
        date = request.args.get('date')
        fetch_all = request.args.get('all', 'true').lower() == 'true'
        order_status = request.args.get('order_status', 'all')

        # Parse order status filter
        order_statuses = None
        if order_status and order_status.lower() != 'all':
            order_statuses = [order_status.upper()]

        orders_data = locus_auth.get_orders(
            config.BEARER_TOKEN,
            'illa-frontdoor',
            date=date,
            fetch_all=fetch_all,
            order_statuses=order_statuses
        )

        return jsonify(orders_data or {'error': 'Failed to fetch orders'})

    @app.route('/api/refresh-orders', methods=['POST'])
    def refresh_orders():
        """Refresh orders by clearing cache and fetching fresh data from Locus API
        Handles single dates and date ranges with day-by-day processing"""
        try:
            # Get parameters from request body or query params
            request_data = {}
            try:
                if request.is_json and request.get_data():
                    request_data = request.get_json() or {}
            except Exception as json_error:
                logger.warning(f"Failed to parse JSON from request: {json_error}")
                request_data = {}

            date = request.args.get('date') or request_data.get('date') or datetime.now().strftime("%Y-%m-%d")
            date_from = request.args.get('date_from') or request_data.get('date_from')
            date_to = request.args.get('date_to') or request_data.get('date_to')
            order_status = request.args.get('order_status') or request_data.get('order_status', 'all')
            force_refresh = request_data.get('force_refresh', False)

            # Determine if this is a date range or single date
            if date_from and date_to:
                # Date range refresh - handle day by day
                logger.info(f"REFRESH REQUEST: Date range {date_from} to {date_to}")

                # Use the filter service to handle date range refresh
                filters_data = {
                    'date_from': date_from,
                    'date_to': date_to,
                    'order_status': order_status
                }

                result = filter_service.refresh_date_range_data(
                    date_from, date_to, filters_data, force_refresh, config
                )

                if result['success']:
                    return jsonify({
                        'success': True,
                        'message': f'✅ {result["message"]}',
                        'total_orders_refreshed': result['total_orders_refreshed'],
                        'dates_processed': result['dates_processed'],
                        'dates_successful': result['dates_successful'],
                        'dates_failed': result['dates_failed'],
                        'date_from': date_from,
                        'date_to': date_to,
                        'results': result['results']
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': f'❌ Error refreshing date range: {result.get("error", "Unknown error")}'
                    }), 500

            else:
                # Single date refresh (existing logic)
                # Parse order status filter
                order_statuses = None
                if order_status and order_status.lower() != 'all':
                    order_statuses = [order_status.upper()]

                status_msg = f"all statuses" if not order_statuses else ", ".join(order_statuses)
                logger.info(f"REFRESH REQUEST: Forcing fresh fetch for date {date} (statuses: {status_msg})")

                # Smart refresh: fetch fresh data and merge with database (no deletion)
                if force_refresh:
                    orders_data = locus_auth.refresh_orders_force_fresh(
                        config.BEARER_TOKEN,
                        'illa-frontdoor',
                        date=date,
                        fetch_all=True
                    )
                else:
                    orders_data = locus_auth.refresh_orders_smart_merge(
                        config.BEARER_TOKEN,
                        'illa-frontdoor',
                        date=date,
                        fetch_all=True,
                        order_statuses=order_statuses
                    )

                if orders_data:
                    total_count = orders_data.get('totalCount', 0)
                    status_totals = orders_data.get('statusTotals', {})

                    # Create summary message with status breakdown
                    status_breakdown = ""
                    if status_totals:
                        status_breakdown = " | Status breakdown: " + ", ".join([f"{status}: {count}" for status, count in status_totals.items()])

                    return jsonify({
                        'success': True,
                        'message': f'✅ Refreshed data from Locus API. Found {total_count} orders for {date}{status_breakdown}',
                        'total_orders_count': total_count,
                        'date': date,
                        'order_status': order_status,
                        'status_totals': status_totals,
                        'orders': orders_data.get('orders', [])
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Failed to refresh orders from API'
                    }), 500

        except Exception as e:
            logger.error(f"Error refreshing orders: {e}")
            return jsonify({
                'success': False,
                'message': f'Error refreshing orders: {str(e)}'
            }), 500

    @app.route('/order/<order_id>')
    def order_detail(order_id):
        """View detailed order information"""
        date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        data_source = "Database"  # Default assumption

        # First, try to get order from database to get enhanced fields
        db_order = Order.query.filter_by(id=order_id).first()

        # Try to fetch detailed order information, ALWAYS try task endpoint first (richer, more accurate data)
        order_detail_data = None

        # ALWAYS try task endpoint first as it has the most accurate status information
        order_detail_data = locus_auth.get_task_detail(
            config.BEARER_TOKEN,
            'illa-frontdoor',
            order_id
        )

        if order_detail_data:
            # Task API worked - this is the best source
            data_source = "Task API (Locus Direct)" if not db_order else "Database + Task API"
            # Transform task data to match expected order structure
            order_detail_data = transform_task_to_order_format(order_detail_data)
        else:
            # Fallback to order endpoint if task endpoint failed
            logger.warning(f"Task API failed for {order_id}, falling back to order API")
            order_detail_data = locus_auth.get_order_detail(
                config.BEARER_TOKEN,
                'illa-frontdoor',
                order_id
            )
            if order_detail_data:
                data_source = "Order API (Fallback)" if not db_order else "Database + Order API (Fallback)"

        if not order_detail_data:
            flash(f'Order {order_id} not found or failed to load from both API endpoints', 'error')
            return redirect(url_for('dashboard'))

        # Add data source indicator
        order_detail_data['_data_source'] = data_source
        order_detail_data['_from_database'] = db_order is not None

        # If order is not in database but we have API data, store it as backup
        if not db_order and order_detail_data:
            try:
                logger.info(f"Order {order_id} not found in database, storing as backup")
                store_order_from_api_data(order_detail_data, date)
                logger.info(f"Successfully stored order {order_id} in database")
            except Exception as e:
                logger.error(f"Failed to store order {order_id} in database: {e}")

        # Merge database fields into the API response if we have a database record
        if db_order:
            # ALWAYS prefer task API data for status if available (most accurate)
            if order_detail_data.get('_is_task_format'):
                # We have task data - keep the task status and use database for enhanced fields only
                task_status = order_detail_data.get('order_status')
                logger.info(f"Using task status '{task_status}' over database status '{db_order.order_status}'")

                # Ensure all status fields are consistent with task data
                order_detail_data['order_status'] = task_status
                order_detail_data['orderStatus'] = task_status
                order_detail_data['effective_status'] = task_status

                # For cancellation reason, prefer task data but enhance with database if missing
                if not order_detail_data.get('cancellation_reason') and db_order.cancellation_reason:
                    order_detail_data['cancellation_reason'] = db_order.cancellation_reason
            else:
                # No task data - use database for status
                order_detail_data['order_status'] = db_order.order_status
                order_detail_data['orderStatus'] = db_order.order_status
                order_detail_data['effective_status'] = db_order.order_status
                order_detail_data['cancellation_reason'] = db_order.cancellation_reason

            # Add other database fields regardless of source
            order_detail_data['completed_on'] = db_order.completed_on.isoformat() if db_order.completed_on else None
            order_detail_data['rider_name'] = db_order.rider_name or order_detail_data.get('orderMetadata', {}).get('tourDetail', {}).get('riderName')
            order_detail_data['rider_phone'] = db_order.rider_phone
            order_detail_data['vehicle_registration'] = db_order.vehicle_registration or order_detail_data.get('orderMetadata', {}).get('tourDetail', {}).get('vehicleRegistrationNumber')
            order_detail_data['location_name'] = db_order.location_name or order_detail_data.get('location', {}).get('name')
            order_detail_data['location_city'] = db_order.location_city or order_detail_data.get('location', {}).get('address', {}).get('city')
            order_detail_data['location_address'] = db_order.location_address or order_detail_data.get('location', {}).get('address', {}).get('formattedAddress')

            # Add other useful database fields
            order_detail_data['tour_id'] = db_order.tour_id
            order_detail_data['tour_name'] = db_order.tour_name
            order_detail_data['partially_delivered'] = db_order.partially_delivered
            order_detail_data['reassigned'] = db_order.reassigned
            order_detail_data['rejected'] = db_order.rejected
            order_detail_data['unassigned'] = db_order.unassigned
            order_detail_data['tardiness'] = db_order.tardiness
            order_detail_data['sla_status'] = db_order.sla_status
            order_detail_data['amount_collected'] = db_order.amount_collected
            order_detail_data['effective_tat'] = db_order.effective_tat

            # Add time tracking fields
            order_detail_data['eta_updated_on'] = db_order.eta_updated_on.isoformat() if db_order.eta_updated_on else None
            order_detail_data['tour_updated_on'] = db_order.tour_updated_on.isoformat() if db_order.tour_updated_on else None
            order_detail_data['initial_assignment_at'] = db_order.initial_assignment_at.isoformat() if db_order.initial_assignment_at else None
            order_detail_data['initial_assignment_by'] = db_order.initial_assignment_by

            # Parse and add JSON fields
            try:
                if db_order.skills:
                    order_detail_data['skills'] = json.loads(db_order.skills)
                if db_order.tags:
                    order_detail_data['tags'] = json.loads(db_order.tags)
                if db_order.custom_fields:
                    order_detail_data['custom_fields'] = json.loads(db_order.custom_fields)
            except json.JSONDecodeError:
                pass  # Keep original if parsing fails

        else:
            # No database record - ensure status fields are properly set from API data
            if order_detail_data.get('_is_task_format'):
                # Ensure all status fields are set for task data without database
                task_status = order_detail_data.get('order_status')
                order_detail_data['orderStatus'] = task_status
                order_detail_data['effective_status'] = task_status
                logger.info(f"No database record - using task status '{task_status}' for all status fields")

        # Enhance order with validation summary and GRN status (same logic as dashboard)
        order_detail_data['has_grn'] = has_grn_document(order_detail_data)

        # Get validation summary for this order
        validation_summary = ai_validator.get_stored_validation_result(order_id)
        if validation_summary:
            # Parse stored JSON fields if they're strings
            try:
                summary_data = json.loads(validation_summary.get('summary', '{}')) if isinstance(validation_summary.get('summary'), str) else validation_summary.get('summary', {})
                discrepancies_data = json.loads(validation_summary.get('discrepancies', '[]')) if isinstance(validation_summary.get('discrepancies'), str) else validation_summary.get('discrepancies', [])
            except json.JSONDecodeError:
                summary_data = {}
                discrepancies_data = []

            # Default has_document to True for backward compatibility with older records
            has_document = validation_summary.get('has_document')
            if has_document is None:
                has_document = True  # Default for older records

            order_detail_data['validation_summary'] = {
                'has_validation': True,
                'is_valid': validation_summary.get('is_valid', False),
                'confidence_score': validation_summary.get('confidence_score', 0.0),
                'discrepancies_count': len(discrepancies_data) if discrepancies_data else validation_summary.get('discrepancies_count', 0),
                'summary': summary_data,
                'discrepancies': discrepancies_data,
                'validation_date': validation_summary.get('validation_date'),
                'processing_time': validation_summary.get('processing_time', 0.0),
                'has_document': has_document,
                'gtins_verified': validation_summary.get('gtins_verified'),
                'gtins_matched': validation_summary.get('gtins_matched')
            }
        else:
            order_detail_data['validation_summary'] = {
                'has_validation': False
            }

        # Debug logging for status verification
        logger.info(f"Final order data for {order_id}:")
        logger.info(f"  - order_status: {order_detail_data.get('order_status')}")
        logger.info(f"  - orderStatus: {order_detail_data.get('orderStatus')}")
        logger.info(f"  - effective_status: {order_detail_data.get('effective_status')}")
        logger.info(f"  - cancellation_reason: {order_detail_data.get('cancellation_reason')}")
        logger.info(f"  - data_source: {order_detail_data.get('_data_source')}")
        logger.info(f"  - is_task_format: {order_detail_data.get('_is_task_format')}")

        return render_template('order_detail.html',
                             order=order_detail_data,
                             order_id=order_id,
                             date=date)

    @app.route('/validate-order/<order_id>', methods=['POST'])
    def validate_single_order(order_id):
        """Validate a single order against its GRN document"""
        try:
            # Get order detail
            order_detail_data = locus_auth.get_order_detail(
                config.BEARER_TOKEN,
                'illa-frontdoor',
                order_id
            )

            if not order_detail_data:
                return jsonify({
                    'success': False,
                    'error': f'Order {order_id} not found'
                })

            # Get GRN document URL - try multiple possible paths
            grn_url = None

            # Try different possible paths where the GRN might be stored
            possible_paths = [
                # Direct path
                ['orderMetadata', 'customerProofOfCompletion', 'Proof Of Delivery Document', 'Proof Of Delivery Document'],
                ['orderMetadata', 'customerProofOfCompletion', 'proofOfDeliveryDocument'],
                ['orderMetadata', 'customerProofOfCompletion', 'deliveryDocument'],
                # Alternative paths
                ['proofOfDelivery', 'document'],
                ['proofOfDelivery', 'documentUrl'],
                ['proofOfDelivery', 'deliveryDocument'],
                ['customerProofOfCompletion', 'deliveryDocument'],
                ['customerProofOfCompletion', 'document'],
            ]

            # Debug: Log the available proof keys
            proof_data = order_detail_data.get('orderMetadata', {}).get('customerProofOfCompletion', {})
            logger.info(f"Available proof keys for order {order_id}: {list(proof_data.keys())}")

            # Try each possible path
            for path in possible_paths:
                current_data = order_detail_data
                try:
                    for key in path:
                        current_data = current_data[key]
                    if isinstance(current_data, str) and current_data.startswith('http'):
                        grn_url = current_data
                        logger.info(f"Found GRN URL at path {' -> '.join(path)}: {grn_url}")
                        break
                except (KeyError, TypeError):
                    continue

            # If still no URL, try to find any URL in the proof data
            if not grn_url and proof_data:
                def find_urls_recursive(obj, path=""):
                    urls = []
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            new_path = f"{path}.{key}" if path else key
                            if isinstance(value, str) and value.startswith('http'):
                                urls.append((new_path, value))
                            elif isinstance(value, (dict, list)):
                                urls.extend(find_urls_recursive(value, new_path))
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj):
                            new_path = f"{path}[{i}]"
                            urls.extend(find_urls_recursive(item, new_path))
                    return urls

                found_urls = find_urls_recursive(proof_data)
                logger.info(f"Found URLs in proof data: {found_urls}")

                if found_urls:
                    grn_url = found_urls[0][1]  # Take the first URL found
                    logger.info(f"Using first found URL: {grn_url}")

            if not grn_url:
                # Enhanced error message with available data structure
                return jsonify({
                    'success': False,
                    'error': 'No GRN document URL found for this order',
                    'debug_info': {
                        'available_proof_keys': list(proof_data.keys()) if proof_data else [],
                        'orderMetadata_keys': list(order_detail_data.get('orderMetadata', {}).keys())
                    }
                })

            # Check if there's a stored validation result for this order and GRN
            stored_result = ai_validator.get_stored_validation_result(order_id, grn_url)

            # If force reprocess is requested, skip stored result
            force_reprocess = False
            try:
                if request.is_json:
                    json_data = request.get_json(silent=True)  # Don't raise exception on invalid JSON
                    if json_data:
                        force_reprocess = json_data.get('force_reprocess', False)
                elif request.form:
                    force_reprocess = request.form.get('force_reprocess', 'false').lower() == 'true'
            except Exception as e:
                logger.warning(f"Error parsing force_reprocess parameter: {e}")
                force_reprocess = False

            logger.info(f"Force reprocess requested: {force_reprocess} for order {order_id}")

            if stored_result and not force_reprocess:
                logger.info(f"Returning stored validation result for order {order_id}")

                # Parse stored data properly
                try:
                    extracted_items = json.loads(stored_result.get('extracted_items', '[]')) if isinstance(stored_result.get('extracted_items'), str) else stored_result.get('extracted_items', [])
                    discrepancies = json.loads(stored_result.get('discrepancies', '[]')) if isinstance(stored_result.get('discrepancies'), str) else stored_result.get('discrepancies', [])
                    summary = json.loads(stored_result.get('summary', '{}')) if isinstance(stored_result.get('summary'), str) else stored_result.get('summary', {})
                    gtin_verification = json.loads(stored_result.get('gtin_verification', '[]')) if isinstance(stored_result.get('gtin_verification'), str) else stored_result.get('gtin_verification', [])
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing stored validation data: {e}")
                    extracted_items, discrepancies, summary, gtin_verification = [], [], {}, []

                # Determine validation result
                has_document = stored_result.get('has_document', True)  # Default to True for backward compatibility
                is_valid = stored_result.get('is_valid', False)

                if not has_document:
                    validation_result = 'NO_DOCUMENT'
                elif is_valid:
                    validation_result = 'VALID'
                else:
                    validation_result = 'INVALID'

                return jsonify({
                    'success': True,
                    'is_valid': is_valid,
                    'validation_data': {
                        'has_document': has_document,
                        'validation_result': validation_result,
                        'confidence_score': stored_result.get('confidence_score', 0),
                        'extracted_items': extracted_items,
                        'discrepancies': discrepancies,
                        'summary': summary,
                        'gtin_verification': gtin_verification
                    },
                    'confidence_score': stored_result.get('confidence_score', 0),
                    'discrepancies': discrepancies,
                    'summary': summary,
                    'gtin_verification': gtin_verification,
                    'cached': True,
                    'validation_date': stored_result.get('validation_date'),
                    'processing_time': stored_result.get('processing_time', 0)
                })

            # If no stored result or force reprocess, validate using Google AI
            logger.info(f"Processing new validation for order {order_id}")
            logger.info(f"Using GRN URL: {grn_url}")

            try:
                validation_result = ai_validator.validate_grn_against_order(order_detail_data, grn_url)
                logger.info(f"Validation completed for order {order_id}, success: {validation_result.get('success', False)}")
                return jsonify(validation_result)
            except Exception as e:
                logger.error(f"Exception during validation for order {order_id}: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': f'Validation exception: {str(e)}',
                    'is_valid': False
                })

        except Exception as e:
            logger.error(f"Error validating order {order_id}: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception details: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({
                'success': False,
                'error': str(e)
            })

    @app.route('/validate-all-orders', methods=['POST'])
    def validate_all_orders():
        """Validate all orders for today against their GRN documents using parallel processing with cost optimization"""
        try:
            date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))

            # Get parameters from request
            max_workers = 20
            validate_mode = 'unvalidated_only'  # Default to cost-effective mode
            force_reprocess = False

            try:
                if request.is_json:
                    json_data = request.get_json(silent=True)
                    if json_data:
                        max_workers = min(max(int(json_data.get('max_workers', 20)), 1), 50)  # Cap between 1-50
                        validate_mode = json_data.get('validate_mode', 'unvalidated_only')  # 'all' or 'unvalidated_only'
                        force_reprocess = json_data.get('force_reprocess', False)
            except Exception:
                pass  # Use defaults

            logger.info(f"Starting batch validation with {max_workers} threads, mode: {validate_mode}")

            # Get all orders
            orders_data = locus_auth.get_orders(
                config.BEARER_TOKEN,
                'illa-frontdoor',
                date=date,
                fetch_all=True
            )

            if not orders_data or not orders_data.get('orders'):
                return jsonify({
                    'success': False,
                    'error': 'No orders found'
                })

            all_orders = orders_data['orders']

            # First, filter out orders without GRN documents
            orders_with_grn = []
            orders_without_grn = 0
            for order in all_orders:
                if has_grn_document(order):
                    orders_with_grn.append(order)
                else:
                    orders_without_grn += 1

            logger.info(f"Filtered out {orders_without_grn} orders without GRN documents")

            # Filter orders based on validation mode to minimize API costs
            orders_to_validate = []
            if validate_mode == 'unvalidated_only':
                logger.info("Filtering to only unvalidated orders to minimize API costs...")
                for order in orders_with_grn:
                    order_id = order.get('id')
                    if order_id:
                        # Quick check for stored validation result
                        stored_result = ai_validator.get_stored_validation_result(order_id)
                        if not stored_result or force_reprocess:
                            orders_to_validate.append(order)
            else:
                orders_to_validate = orders_with_grn

            total_orders = len(all_orders)
            total_orders_with_grn = len(orders_with_grn)
            orders_to_process = len(orders_to_validate)

            logger.info(f"Total orders: {total_orders}, Orders to validate: {orders_to_process}")

            if orders_to_process == 0:
                return jsonify({
                    'success': True,
                    'message': 'All orders already validated - no API calls needed!',
                    'total_orders': total_orders,
                    'processed': 0,
                    'errors': 0,
                    'skipped': total_orders,
                    'results': [],
                    'api_calls_saved': total_orders,
                    'threads_used': 0
                })

            validation_results = []
            processed = 0
            errors = 0
            progress_lock = threading.Lock()

            # Use ThreadPoolExecutor for parallel processing with rate limiting
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit validation tasks only for orders that need validation
                future_to_order = {
                    executor.submit(validate_single_order_worker, order, date, force_reprocess): order
                    for order in orders_to_validate
                }

                # Collect results as they complete
                for future in as_completed(future_to_order):
                    order = future_to_order[future]
                    try:
                        result = future.result()
                        with progress_lock:
                            validation_results.append(result)
                            if result.get('success', False):
                                processed += 1
                            else:
                                errors += 1

                            # Log progress every 10 completions
                            total_completed = processed + errors
                            if total_completed % 10 == 0 or total_completed == orders_to_process:
                                logger.info(f"Progress: {total_completed}/{orders_to_process} orders completed")

                    except Exception as e:
                        with progress_lock:
                            logger.error(f"Error processing future for order {order.get('id', 'unknown')}: {e}")
                            validation_results.append({
                                'order_id': order.get('id', 'unknown'),
                                'success': False,
                                'error': f'Thread execution error: {str(e)}',
                                'is_valid': False
                            })
                            errors += 1

            # Count API calls made vs cached results
            api_calls_made = sum(1 for result in validation_results if not result.get('from_cache', False))
            cached_results = sum(1 for result in validation_results if result.get('from_cache', False))
            skipped_orders = total_orders - orders_to_process
            skipped_no_grn = sum(1 for result in validation_results if result.get('skipped_no_grn', False))

            logger.info(f"Batch validation completed: {processed} processed, {errors} errors")
            logger.info(f"API optimization: {api_calls_made} API calls made, {cached_results} from cache, {skipped_orders} skipped")
            logger.info(f"Orders excluded: {orders_without_grn} without GRN documents")

            return jsonify({
                'success': True,
                'total_orders': total_orders,
                'orders_with_grn': total_orders_with_grn,
                'orders_without_grn': orders_without_grn,
                'processed': processed,
                'errors': errors,
                'skipped': skipped_orders,
                'results': validation_results,
                'threads_used': max_workers,
                'api_calls_made': api_calls_made,
                'cached_results': cached_results,
                'validate_mode': validate_mode
            })

        except Exception as e:
            logger.error(f"Error validating all orders: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })

    # API endpoints for testing compatibility
    @app.route('/api/login', methods=['POST'])
    def api_login():
        """API endpoint for login - returns session info"""
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                return jsonify({
                    'success': False,
                    'error': 'Username and password required'
                }), 400

            # For this demo, we'll use a simple validation
            # In production, this would validate against actual user database
            if username and password:
                return jsonify({
                    'success': True,
                    'message': 'Login successful',
                    'user': {
                        'username': username,
                        'role': 'user'
                    }
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'Invalid credentials'
                }), 401

        except Exception as e:
            logger.error(f"Login error: {e}")
            return jsonify({
                'success': False,
                'error': 'Server error'
            }), 500

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Web login page"""
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')

            if username and password:
                session['user'] = username
                flash('Login successful', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials', 'error')

        return render_template('login.html')

    @app.route('/logout')
    def logout():
        """Logout and clear session"""
        session.clear()
        flash('You have been logged out', 'info')
        return redirect(url_for('login'))

    @app.route('/api/orders/validation', methods=['POST'])
    def api_order_validation():
        """API endpoint for order validation workflow"""
        try:
            data = request.get_json()
            order_id = data.get('order_id')

            if not order_id:
                return jsonify({
                    'success': False,
                    'error': 'Order ID required'
                }), 400

            # Get order validation result
            validation_result = ai_validator.get_stored_validation_result(order_id)

            if validation_result:
                return jsonify({
                    'success': True,
                    'order_id': order_id,
                    'validation': validation_result
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'Order validation not found'
                }), 404

        except Exception as e:
            logger.error(f"Order validation API error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/image/grn-analysis', methods=['POST'])
    def api_image_grn_analysis():
        """API endpoint for GRN image analysis"""
        try:
            if 'image' not in request.files:
                return jsonify({
                    'success': False,
                    'error': 'No image file provided'
                }), 400

            file = request.files['image']
            if file.filename == '':
                return jsonify({
                    'success': False,
                    'error': 'No image file selected'
                }), 400

            # Process the image for GRN analysis
            # Read image data
            image_data = file.read()
            image = Image.open(io.BytesIO(image_data))

            # For demo purposes, return mock analysis result
            analysis_result = {
                'success': True,
                'image_size': image.size,
                'format': image.format,
                'extracted_data': {
                    'grn_number': 'GRN-2025-001',
                    'items_detected': 5,
                    'confidence_score': 0.85
                },
                'processing_time': '0.5s'
            }

            return jsonify(analysis_result), 200

        except ImportError:
            return jsonify({
                'success': False,
                'error': 'PIL module not available'
            }), 500
        except Exception as e:
            logger.error(f"Image analysis error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/data/export', methods=['GET'])
    def api_data_export():
        """API endpoint for data export functionality"""
        try:
            export_format = request.args.get('format', 'json')
            date_filter = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))

            # Get orders for the specified date
            orders_data = locus_auth.get_orders(
                config.BEARER_TOKEN,
                'illa-frontdoor',
                date=date_filter,
                fetch_all=True
            )

            if not orders_data or not orders_data.get('orders'):
                return jsonify({
                    'success': False,
                    'error': 'No data to export'
                }), 200

            export_data = {
                'export_date': datetime.now().isoformat(),
                'filter_date': date_filter,
                'format': export_format,
                'total_orders': len(orders_data['orders']),
                'orders': orders_data['orders']
            }

            if export_format.lower() == 'csv':
                # For CSV format, return appropriate headers
                response = jsonify(export_data)
                response.headers['Content-Type'] = 'application/json'
                response.headers['Content-Disposition'] = f'attachment; filename=orders_{date_filter}.json'
                return response

            return jsonify(export_data), 200

        except Exception as e:
            logger.error(f"Data export error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # Enhanced Filtering API Endpoints
    @app.route('/api/filters/available', methods=['GET'])
    def api_get_available_filters():
        """Get all available filter options"""
        try:
            filters = filter_service.get_available_filters()
            return jsonify({
                'success': True,
                'filters': filters,
                'message': 'Available filters retrieved successfully'
            }), 200
        except Exception as e:
            logger.error(f"Error getting available filters: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/orders/filter', methods=['POST'])
    def api_filter_orders():
        """Main filtering endpoint - returns filtered orders based on criteria"""
        try:
            # Get filter criteria from request
            filters_data = request.get_json() or {}

            # Log the filter request for debugging
            logger.info(f"Filter request: {filters_data}")

            # Apply filters using the filter service
            result = filter_service.apply_filters(filters_data)

            if not result.get('success', False):
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Unknown filtering error'),
                    'orders': [],
                    'total_count': 0
                }), 400

            # Enhance orders with validation summaries and GRN status
            enhanced_orders = []
            for order in result['orders']:
                # Add validation summary
                validation_summary = ai_validator.get_stored_validation_result(order['id'])
                if validation_summary:
                    order['validation_summary'] = {
                        'has_validation': True,
                        'is_valid': validation_summary.get('is_valid', False),
                        'has_document': validation_summary.get('has_document'),
                        'confidence_score': validation_summary.get('confidence_score', 0),
                        'discrepancies_count': len(validation_summary.get('discrepancies', [])),
                        'validation_date': validation_summary.get('validation_date'),
                        'processing_time': validation_summary.get('processing_time'),
                        'summary': validation_summary.get('summary', {}),
                        'gtins_verified': validation_summary.get('summary', {}).get('gtins_verified', 0),
                        'gtins_matched': validation_summary.get('summary', {}).get('gtins_matched', 0)
                    }
                else:
                    order['validation_summary'] = {
                        'has_validation': False,
                        'is_valid': False
                    }

                # Check GRN status (this requires the order detail data)
                # For now, we'll set a placeholder - in production, you might want to store this in DB
                order['has_grn'] = True  # Placeholder - would need to check actual order data

                enhanced_orders.append(order)

            result['orders'] = enhanced_orders

            return jsonify({
                'success': True,
                'orders': result['orders'],
                'total_count': result['total_count'],
                'page': result.get('page', 1),
                'per_page': result.get('per_page', 50),
                'total_pages': result.get('total_pages', 1),
                'status_totals': result.get('status_totals', {}),
                'applied_filters': result.get('applied_filters', {}),
                'message': f'Found {len(result["orders"])} orders matching filters'
            }), 200

        except Exception as e:
            logger.error(f"Error filtering orders: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'orders': [],
                'total_count': 0
            }), 500

    @app.route('/api/filters/options/<filter_type>', methods=['GET'])
    def api_get_filter_options(filter_type):
        """Get dynamic options for a specific filter type with search support"""
        try:
            # Validate filter type
            valid_filters = ['order_status', 'location_city', 'location_country_code',
                           'rider_name', 'client_id']

            if filter_type not in valid_filters:
                return jsonify({
                    'success': False,
                    'error': f'Invalid filter type: {filter_type}',
                    'options': []
                }), 400

            # Get search term and pagination parameters
            search_term = request.args.get('search', '').strip()
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 50)), 100)  # Max 100 items

            # Get options based on filter type with search
            options = []

            if filter_type == 'location_city':
                from models import db, Order
                query = db.session.query(Order.location_city.distinct().label('value')).filter(
                    Order.location_city.isnot(None)
                )
                if search_term:
                    query = query.filter(Order.location_city.ilike(f'%{search_term}%'))

                results = query.order_by('value').offset((page - 1) * per_page).limit(per_page).all()
                options = [{'value': r.value, 'label': r.value} for r in results if r.value]

            elif filter_type == 'rider_name':
                from models import db, Order
                query = db.session.query(Order.rider_name.distinct().label('value')).filter(
                    Order.rider_name.isnot(None)
                )
                if search_term:
                    query = query.filter(Order.rider_name.ilike(f'%{search_term}%'))

                results = query.order_by('value').offset((page - 1) * per_page).limit(per_page).all()
                options = [{'value': r.value, 'label': r.value} for r in results if r.value]

            elif filter_type == 'client_id':
                from models import db, Order
                query = db.session.query(Order.client_id.distinct().label('value')).filter(
                    Order.client_id.isnot(None)
                )
                if search_term:
                    query = query.filter(Order.client_id.ilike(f'%{search_term}%'))

                results = query.order_by('value').offset((page - 1) * per_page).limit(per_page).all()
                options = [{'value': r.value, 'label': r.value} for r in results if r.value]

            else:
                # For static options like order_status
                all_filters = filter_service.get_available_filters()
                for category in all_filters.values():
                    if filter_type in category:
                        all_options = category[filter_type].get('options', [])
                        if search_term:
                            options = [opt for opt in all_options if search_term.lower() in opt['label'].lower()]
                        else:
                            options = all_options
                        break

            return jsonify({
                'success': True,
                'filter_type': filter_type,
                'options': options,
                'count': len(options),
                'search_term': search_term,
                'page': page,
                'per_page': per_page
            }), 200

        except Exception as e:
            logger.error(f"Error getting filter options for {filter_type}: {e}")
            import traceback
            print(traceback.format_exc())
            return jsonify({
                'success': False,
                'error': str(e),
                'options': []
            }), 500

    # Tours API Endpoints
    @app.route('/tours')
    def tours_dashboard():
        """Tours dashboard page"""
        from datetime import datetime, timedelta
        from models import Tour

        # Get the date parameter - could be orders date or tour date
        selected_date = request.args.get('date')

        if selected_date:
            # If date is provided, assume it's an orders date and convert to tour date
            # (tours are created 1 day before orders)
            orders_date = datetime.strptime(selected_date, "%Y-%m-%d")
            tour_date = orders_date - timedelta(days=1)
            selected_date = tour_date.strftime("%Y-%m-%d")
        else:
            # Find the most recent tour date
            latest_tour = Tour.query.order_by(Tour.tour_date.desc()).first()
            if latest_tour and latest_tour.tour_date:
                # Extract date from tour_date (format: 2025-09-24-20-11-06)
                selected_date = latest_tour.tour_date[:10]
            else:
                # Fallback to yesterday (tours are usually planned the day before)
                yesterday = datetime.now() - timedelta(days=1)
                selected_date = yesterday.strftime("%Y-%m-%d")

        return render_template('tours.html',
                             selected_date=selected_date,
                             username='Amin')

    @app.route('/tour/<tour_id>')
    def tour_detail(tour_id):
        """View detailed tour information"""
        from app.tours import tour_service

        # Decode tour_id if it was URL encoded
        import urllib.parse
        tour_id = urllib.parse.unquote(tour_id)

        result = tour_service.get_tour_details(tour_id)

        if not result['success']:
            flash(f'Tour {tour_id} not found or failed to load', 'error')
            return redirect(url_for('tours_dashboard'))

        return render_template('tour_detail.html',
                             tour=result['tour'],
                             orders=result['orders'],
                             orders_count=result['orders_count'],
                             tour_id=tour_id)

    @app.route('/api/tours')
    def api_tours():
        """API endpoint to get tours with advanced filtering and pagination"""
        from app.tours import tour_service
        from datetime import datetime, timedelta

        # Get query parameters
        date = request.args.get('date')

        # Convert orders date to tour date if provided
        # Tours are created 1 day before the orders they contain
        if date:
            try:
                orders_date = datetime.strptime(date, "%Y-%m-%d")
                tour_date = orders_date - timedelta(days=1)
                date = tour_date.strftime("%Y-%m-%d")
            except ValueError:
                # If date format is invalid, keep original
                pass

        # Basic parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 100)  # Max 100
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort_by', 'tour_number')
        sort_order = request.args.get('sort_order', 'asc')

        # Advanced filtering parameters
        vehicle = request.args.get('vehicle', '').strip()
        rider = request.args.get('rider', '').strip()
        tour_number = request.args.get('tour_number', '').strip()
        cities = request.args.get('cities', '').strip()
        tour_status = request.args.get('tour_status', '').strip()
        company_owner = request.args.get('company_owner', '').strip()
        order_status_filter = request.args.get('order_status_filter', '').strip()

        # Get tours with advanced filtering
        result = tour_service.get_tours(
            date=date,
            page=page,
            per_page=per_page,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            vehicle=vehicle if vehicle else None,
            rider=rider if rider else None,
            tour_number=tour_number if tour_number else None,
            cities=cities if cities else None,
            tour_status=tour_status if tour_status else None,
            company_owner=company_owner if company_owner else None,
            order_status_filter=order_status_filter if order_status_filter else None
        )

        return jsonify(result)

    @app.route('/api/tours/filter-options')
    def api_tours_filter_options():
        """API endpoint to get available filter options for dropdowns"""
        from app.tours import tour_service
        from datetime import datetime, timedelta

        date = request.args.get('date')

        # Convert orders date to tour date if provided
        if date:
            try:
                orders_date = datetime.strptime(date, "%Y-%m-%d")
                tour_date = orders_date - timedelta(days=1)
                date = tour_date.strftime("%Y-%m-%d")
            except ValueError:
                # If date format is invalid, keep original
                pass

        result = tour_service.get_filter_options(date=date)
        return jsonify(result)

    @app.route('/api/tours/summary')
    def api_tours_summary():
        """API endpoint to get tour summary statistics"""
        from app.tours import tour_service
        from datetime import datetime, timedelta

        date = request.args.get('date')

        # Convert orders date to tour date if provided
        # Tours are created 1 day before the orders they contain
        if date:
            try:
                orders_date = datetime.strptime(date, "%Y-%m-%d")
                tour_date = orders_date - timedelta(days=1)
                date = tour_date.strftime("%Y-%m-%d")
            except ValueError:
                # If date format is invalid, keep original
                pass

        result = tour_service.get_tour_summary_stats(date=date)

        return jsonify(result)

    @app.route('/api/tours/refresh', methods=['POST'])
    def api_refresh_tours():
        """API endpoint to refresh tour data from orders"""
        from app.tours import tour_service

        try:
            date = request.args.get('date')
            result = tour_service.refresh_all_tour_data(date=date)

            if result['success']:
                return jsonify({
                    'success': True,
                    'message': result['message'],
                    'processed_orders': result['processed_orders'],
                    'updated_tours': result['updated_tours']
                })
            else:
                return jsonify({
                    'success': False,
                    'message': result.get('error', 'Unknown error')
                }), 500

        except Exception as e:
            logger.error(f"Error refreshing tours: {e}")
            return jsonify({
                'success': False,
                'message': f'Error refreshing tours: {str(e)}'
            }), 500

    @app.route('/api/tour/<tour_id>')
    def api_tour_detail(tour_id):
        """API endpoint to get detailed tour information"""
        from app.tours import tour_service

        # Decode tour_id if it was URL encoded
        import urllib.parse
        tour_id = urllib.parse.unquote(tour_id)

        result = tour_service.get_tour_details(tour_id)
        return jsonify(result)