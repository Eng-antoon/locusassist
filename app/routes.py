from flask import render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
import io

from models import ValidationResult
from app.auth import LocusAuth
from app.validators import GoogleAIValidator
from app.utils import rate_limit_api_call, api_rate_limiter

logger = logging.getLogger(__name__)

def register_routes(app, config):
    """Register all Flask routes"""

    # Initialize auth and validator
    locus_auth = LocusAuth(config)
    ai_validator = GoogleAIValidator(config)

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
        # Get today's date for default filter
        today = datetime.now().strftime("%Y-%m-%d")
        selected_date = request.args.get('date', today)

        # Validate date format
        try:
            datetime.strptime(selected_date, "%Y-%m-%d")
        except ValueError:
            # If invalid date, redirect with error message
            flash(f"Invalid date format: {selected_date}. Please use YYYY-MM-DD format.", "error")
            return redirect(url_for('dashboard', date=today))

        fetch_all = request.args.get('all', 'true').lower() == 'true'  # Default to fetch all

        # Fetch all orders using bearer token
        orders_data = locus_auth.get_orders(
            config.BEARER_TOKEN,
            'illa-frontdoor',
            date=selected_date,
            fetch_all=fetch_all
        )

        # Enhance orders with validation summaries
        if orders_data and orders_data.get('orders'):
            for order in orders_data['orders']:
                order_id = order.get('id')
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
                             username='Amin',
                             fetch_all=fetch_all)

    @app.route('/api/orders')
    def api_orders():
        date = request.args.get('date')
        fetch_all = request.args.get('all', 'true').lower() == 'true'

        orders_data = locus_auth.get_orders(
            config.BEARER_TOKEN,
            'illa-frontdoor',
            date=date,
            fetch_all=fetch_all
        )

        return jsonify(orders_data or {'error': 'Failed to fetch orders'})

    @app.route('/order/<order_id>')
    def order_detail(order_id):
        """View detailed order information"""
        date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))

        # Fetch detailed order information using the new endpoint
        order_detail_data = locus_auth.get_order_detail(
            config.BEARER_TOKEN,
            'illa-frontdoor',
            order_id
        )

        if not order_detail_data:
            flash(f'Order {order_id} not found or failed to load', 'error')
            return redirect(url_for('dashboard'))

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

            # Filter orders based on validation mode to minimize API costs
            orders_to_validate = []
            if validate_mode == 'unvalidated_only':
                logger.info("Filtering to only unvalidated orders to minimize API costs...")
                for order in all_orders:
                    order_id = order.get('id')
                    if order_id:
                        # Quick check for stored validation result
                        stored_result = ai_validator.get_stored_validation_result(order_id)
                        if not stored_result or force_reprocess:
                            orders_to_validate.append(order)
            else:
                orders_to_validate = all_orders

            total_orders = len(all_orders)
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

            logger.info(f"Batch validation completed: {processed} processed, {errors} errors")
            logger.info(f"API optimization: {api_calls_made} API calls made, {cached_results} from cache, {skipped_orders} skipped")

            return jsonify({
                'success': True,
                'total_orders': total_orders,
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