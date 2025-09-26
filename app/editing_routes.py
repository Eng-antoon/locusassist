"""
Editing Routes for Tours and Orders
Handles comprehensive editing functionality with modification tracking
"""

import json
import logging
from datetime import datetime, timezone
from flask import request, jsonify, flash, redirect, url_for
from models import db, Order, Tour, OrderLineItem
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

class EditingService:
    """Service for handling Tour and Order editing operations"""

    def __init__(self):
        pass

    def track_field_modification(self, record, field_name, new_value, modified_by):
        """Track a field modification in the database"""
        try:
            # Get current modified fields
            modified_fields = []
            if record.modified_fields:
                modified_fields = json.loads(record.modified_fields)
            elif not isinstance(modified_fields, list):
                modified_fields = []

            # Add field to modified list if not already there
            if field_name not in modified_fields:
                modified_fields.append(field_name)

            # Update record
            record.modified_fields = json.dumps(modified_fields)
            record.is_modified = True
            record.last_modified_by = modified_by
            record.last_modified_at = datetime.now(timezone.utc)

            logger.info(f"Tracked modification of field '{field_name}' for {type(record).__name__} {record.id}")
            return True

        except Exception as e:
            logger.error(f"Error tracking field modification: {e}")
            return False

    def update_tour_data(self, tour_id, update_data, modified_by, propagate_to_orders=True):
        """Update tour data with modification tracking"""
        try:
            tour = Tour.query.filter_by(tour_id=tour_id).first()
            if not tour:
                return {'success': False, 'error': 'Tour not found'}

            updated_fields = []
            original_data = {}

            # Update each provided field
            for field_name, new_value in update_data.items():
                if hasattr(tour, field_name):
                    old_value = getattr(tour, field_name)
                    original_data[field_name] = old_value

                    # Only update if value changed
                    if old_value != new_value:
                        # Special logic for tour_status changes
                        if field_name == 'tour_status':
                            # If changing from CANCELLED to non-CANCELLED, clear cancellation reason
                            if old_value == 'CANCELLED' and new_value != 'CANCELLED':
                                if hasattr(tour, 'cancellation_reason') and tour.cancellation_reason:
                                    original_data['cancellation_reason'] = tour.cancellation_reason
                                    setattr(tour, 'cancellation_reason', None)
                                    self.track_field_modification(tour, 'cancellation_reason', None, modified_by)
                                    updated_fields.append('cancellation_reason')

                        setattr(tour, field_name, new_value)
                        self.track_field_modification(tour, field_name, new_value, modified_by)
                        updated_fields.append(field_name)
                        logger.info(f"Updated tour {tour_id} field '{field_name}': '{old_value}' → '{new_value}'")

            # Save tour changes
            db.session.commit()

            # Propagate changes to all orders in this tour if requested
            propagated_orders = 0
            if propagate_to_orders:
                # Always propagate tour data to orders to ensure consistency
                # Include all core tour fields that should be synced, not just updated ones
                core_tour_fields = ['rider_name', 'rider_id', 'rider_phone', 'vehicle_registration',
                                   'vehicle_id', 'tour_name', 'tour_number', 'tour_status', 'cancellation_reason']

                # Combine updated fields with all core fields for comprehensive update
                fields_to_propagate = list(set(updated_fields + core_tour_fields))
                logger.info(f"Propagating fields: {fields_to_propagate}")

            if propagate_to_orders and fields_to_propagate:
                # Find orders linked to this tour using multiple approaches
                orders = []

                logger.info(f"Starting to find orders linked to tour {tour_id}")

                # Method 1: Direct tour_id match (if populated)
                direct_orders = Order.query.filter_by(tour_id=tour_id).all()
                if direct_orders:
                    orders.extend(direct_orders)
                    logger.info(f"Found {len(direct_orders)} orders with direct tour_id match")

                # Method 2: Find by rider/vehicle combination (always check this method too)
                tour_rider = getattr(tour, 'rider_name', None)
                tour_vehicle = getattr(tour, 'vehicle_registration', None)
                tour_rider_id = getattr(tour, 'rider_id', None)
                tour_vehicle_id = getattr(tour, 'vehicle_id', None)

                # Multiple rider/vehicle matching strategies
                if tour_rider and tour_vehicle:
                    indirect_orders = Order.query.filter(
                        Order.rider_name == tour_rider,
                        Order.vehicle_registration == tour_vehicle
                    ).all()

                    # Add orders that aren't already in the list
                    for order in indirect_orders:
                        if order not in orders:
                            orders.append(order)

                    logger.info(f"Found {len(indirect_orders)} additional orders by rider_name + vehicle_registration match")

                # Method 3: Match by rider_id and vehicle_id if available
                if tour_rider_id and tour_vehicle_id:
                    id_based_orders = Order.query.filter(
                        Order.rider_id == tour_rider_id,
                        Order.vehicle_id == tour_vehicle_id
                    ).all()

                    for order in id_based_orders:
                        if order not in orders:
                            orders.append(order)

                    logger.info(f"Found {len(id_based_orders)} additional orders by rider_id + vehicle_id match")

                # Method 4: Match by tour_name and tour_number
                tour_name = getattr(tour, 'tour_name', None)
                tour_number = getattr(tour, 'tour_number', None)

                if tour_name:
                    name_based_orders = Order.query.filter(Order.tour_name == tour_name).all()
                    for order in name_based_orders:
                        if order not in orders:
                            orders.append(order)
                    logger.info(f"Found {len(name_based_orders)} additional orders by tour_name match")

                logger.info(f"Found {len(orders)} total unique orders to propagate tour changes to")

                for order in orders:
                    order_updated = False
                    for field_name in fields_to_propagate:
                        # Map tour fields to order fields
                        order_field_map = {
                            'rider_name': 'rider_name',
                            'rider_id': 'rider_id',
                            'rider_phone': 'rider_phone',
                            'vehicle_registration': 'vehicle_registration',
                            'vehicle_id': 'vehicle_id',
                            'tour_name': 'tour_name',
                            'tour_number': 'tour_number',
                            'tour_status': 'order_status',  # Tour status maps to order status
                            'cancellation_reason': 'cancellation_reason'
                        }

                        if field_name in order_field_map and hasattr(order, order_field_map[field_name]):
                            # Get the updated value from the tour
                            tour_new_value = getattr(tour, field_name)
                            old_order_value = getattr(order, order_field_map[field_name])

                            # ALWAYS override order data with tour data - no fallback protection
                            # Force update even if values are the same to ensure consistency
                            if True:  # Always update to override any old/stale data
                                # Special handling for tour status changes - also handle order cancellation reason
                                if field_name == 'tour_status':
                                    # If tour status changed from CANCELLED to non-CANCELLED, clear order cancellation reason too
                                    if old_order_value == 'CANCELLED' and tour_new_value != 'CANCELLED':
                                        if hasattr(order, 'cancellation_reason') and order.cancellation_reason:
                                            setattr(order, 'cancellation_reason', None)
                                            self.track_field_modification(order, 'cancellation_reason', None, f"Tour Update: {modified_by}")
                                            logger.info(f"Cleared order {order.id} cancellation_reason due to tour status change")

                                setattr(order, order_field_map[field_name], tour_new_value)
                                # Track the field modification
                                self.track_field_modification(order, order_field_map[field_name], tour_new_value, f"Tour Update: {modified_by}")
                                order_updated = True
                                logger.info(f"FORCED propagation of {field_name} to order {order.id}: '{old_order_value}' → '{tour_new_value}'")

                    if order_updated:
                        propagated_orders += 1

                db.session.commit()

            return {
                'success': True,
                'message': f'Tour updated successfully. {len(updated_fields)} fields modified.',
                'updated_fields': updated_fields,
                'propagated_orders': propagated_orders,
                'original_data': original_data
            }

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error updating tour {tour_id}: {e}")
            return {'success': False, 'error': f'Database error: {str(e)}'}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating tour {tour_id}: {e}")
            return {'success': False, 'error': str(e)}

    def update_order_data(self, order_id, update_data, modified_by):
        """Update order data with modification tracking"""
        try:
            order = Order.query.filter_by(id=order_id).first()
            if not order:
                return {'success': False, 'error': 'Order not found'}

            updated_fields = []
            original_data = {}

            # Handle special fields first
            special_updates = {}

            # Handle cancellation images
            if 'cancellation_images' in update_data:
                images = update_data.pop('cancellation_images')
                if isinstance(images, list):
                    special_updates['cancellation_images'] = json.dumps(images)
                elif isinstance(images, str):
                    special_updates['cancellation_images'] = images
                else:
                    logger.warning(f"Invalid cancellation_images format: {type(images)}")

            # Handle proof of delivery images
            if 'proof_of_delivery_images' in update_data:
                images = update_data.pop('proof_of_delivery_images')
                if isinstance(images, list):
                    special_updates['proof_of_delivery_images'] = json.dumps(images)
                elif isinstance(images, str):
                    special_updates['proof_of_delivery_images'] = images
                else:
                    logger.warning(f"Invalid proof_of_delivery_images format: {type(images)}")

            # Update regular fields
            for field_name, new_value in update_data.items():
                if hasattr(order, field_name):
                    old_value = getattr(order, field_name)
                    original_data[field_name] = old_value

                    # Only update if value changed
                    if old_value != new_value:
                        setattr(order, field_name, new_value)
                        self.track_field_modification(order, field_name, new_value, modified_by)
                        updated_fields.append(field_name)
                        logger.info(f"Updated order {order_id} field '{field_name}': '{old_value}' → '{new_value}'")

                        # Special handling for order_status changes
                        if field_name == 'order_status':
                            # If status changed from CANCELLED to something else, clear cancellation reason
                            if old_value == 'CANCELLED' and new_value != 'CANCELLED':
                                if hasattr(order, 'cancellation_reason') and order.cancellation_reason:
                                    original_data['cancellation_reason'] = order.cancellation_reason
                                    setattr(order, 'cancellation_reason', None)
                                    self.track_field_modification(order, 'cancellation_reason', None, modified_by)
                                    updated_fields.append('cancellation_reason')
                                    logger.info(f"Cleared cancellation_reason due to status change from CANCELLED to {new_value}")

            # Update special fields
            for field_name, new_value in special_updates.items():
                if hasattr(order, field_name):
                    old_value = getattr(order, field_name)
                    original_data[field_name] = old_value

                    if old_value != new_value:
                        setattr(order, field_name, new_value)
                        self.track_field_modification(order, field_name, new_value, modified_by)
                        updated_fields.append(field_name)
                        logger.info(f"Updated order {order_id} field '{field_name}' with special handling")

            # Save changes
            db.session.commit()

            return {
                'success': True,
                'message': f'Order updated successfully. {len(updated_fields)} fields modified.',
                'updated_fields': updated_fields,
                'original_data': original_data
            }

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error updating order {order_id}: {e}")
            return {'success': False, 'error': f'Database error: {str(e)}'}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating order {order_id}: {e}")
            return {'success': False, 'error': str(e)}

    def update_order_line_items(self, order_id, line_items_data, modified_by):
        """Update order line items stored in orderMetadata JSON"""
        try:
            order = Order.query.filter_by(id=order_id).first()
            if not order:
                return {'success': False, 'error': 'Order not found'}

            results = {
                'added': 0,
                'updated': 0,
                'deleted': 0,
                'errors': []
            }

            # Get existing orderMetadata from raw_data
            raw_data = json.loads(order.raw_data) if order.raw_data else {}
            order_metadata = raw_data.get('orderMetadata', {})

            # Initialize lineItems if not present
            if 'lineItems' not in order_metadata:
                order_metadata['lineItems'] = []

            # Replace all line items with the new ones
            new_line_items = []

            for item_data in line_items_data:
                try:
                    # Create new line item in the expected JSON format
                    new_item = {
                        'id': item_data.get('sku_id', ''),
                        'name': item_data.get('name', ''),
                        'description': item_data.get('description', ''),
                        'quantity': int(item_data.get('quantity', 0)),
                        'weightPerUnit': {
                            'unit': 'KG',
                            'value': float(item_data.get('weight_per_unit', 0)) if item_data.get('weight_per_unit') else 0
                        },
                        'volumePerUnit': {
                            'unit': 'CM',
                            'value': float(item_data.get('volume_per_unit', 0)) if item_data.get('volume_per_unit') else 0
                        },
                        'quantityUnit': item_data.get('quantity_unit', 'PIECES'),
                        'handlingUnit': item_data.get('handling_unit', 'PIECES'),
                        'transactionStatus': {
                            'orderedQuantity': int(item_data.get('quantity', 0)),
                            'transactedQuantity': 0,
                            'status': 'NOT_DELIVERED'
                        }
                    }

                    new_line_items.append(new_item)
                    results['added'] += 1

                except Exception as e:
                    results['errors'].append(f"Error processing item {item_data.get('sku_id', 'unknown')}: {str(e)}")
                    logger.error(f"Error processing line item: {e}")

            # Update the orderMetadata with new line items
            order_metadata['lineItems'] = new_line_items

            # Save modified orderMetadata back to raw_data
            raw_data['orderMetadata'] = order_metadata
            order.raw_data = json.dumps(raw_data)

            # Update order modification tracking
            self.track_field_modification(order, 'line_items', f"Updated {results['added']} line items", modified_by)

            db.session.commit()

            logger.info(f"Updated line items for order {order_id}: {results['added']} items by {modified_by}")

            return {
                'success': True,
                'message': f'Line items updated: {results["added"]} added, 0 updated, 0 deleted',
                'results': results
            }

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error updating line items for order {order_id}: {e}")
            return {'success': False, 'error': f'Database error: {str(e)}'}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating line items for order {order_id}: {e}")
            return {'success': False, 'error': str(e)}

def register_editing_routes(app):
    """Register all editing routes"""
    editing_service = EditingService()

    @app.route('/api/tours/<tour_id>/edit', methods=['PUT'])
    def api_edit_tour(tour_id):
        """API endpoint to edit tour data"""
        try:
            if not request.is_json:
                return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 400

            data = request.get_json()
            modified_by = data.get('modified_by', 'Unknown User')
            update_data = data.get('data', {})
            propagate_to_orders = data.get('propagate_to_orders', True)

            # Validate required data
            if not update_data:
                return jsonify({'success': False, 'error': 'No update data provided'}), 400

            # Import urllib.parse for URL decoding
            import urllib.parse
            tour_id = urllib.parse.unquote(tour_id)

            result = editing_service.update_tour_data(
                tour_id=tour_id,
                update_data=update_data,
                modified_by=modified_by,
                propagate_to_orders=propagate_to_orders
            )

            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"Error in tour editing API: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/orders/<order_id>/edit', methods=['PUT'])
    def api_edit_order(order_id):
        """API endpoint to edit order data"""
        try:
            if not request.is_json:
                return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 400

            data = request.get_json()
            modified_by = data.get('modified_by', 'Unknown User')
            update_data = data.get('data', {})

            # Validate required data
            if not update_data:
                return jsonify({'success': False, 'error': 'No update data provided'}), 400

            result = editing_service.update_order_data(
                order_id=order_id,
                update_data=update_data,
                modified_by=modified_by
            )

            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"Error in order editing API: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/orders/<order_id>/line-items/edit', methods=['PUT'])
    def api_edit_order_line_items(order_id):
        """API endpoint to edit order line items"""
        try:
            if not request.is_json:
                return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 400

            data = request.get_json()
            modified_by = data.get('modified_by', 'Unknown User')
            line_items_data = data.get('line_items', [])

            # Validate required data
            if not line_items_data and not data.get('deleted_item_ids'):
                return jsonify({'success': False, 'error': 'No line items data provided'}), 400

            result = editing_service.update_order_line_items(
                order_id=order_id,
                line_items_data=line_items_data,
                modified_by=modified_by
            )

            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"Error in line items editing API: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/orders/<order_id>/images/upload', methods=['POST'])
    def api_upload_order_images(order_id):
        """API endpoint to upload images for orders (cancellation or proof of delivery)"""
        try:
            # Check if request has files
            if 'images' not in request.files:
                return jsonify({'success': False, 'error': 'No images provided'}), 400

            images = request.files.getlist('images')
            image_type = request.form.get('type', 'proof_of_delivery')  # 'cancellation' or 'proof_of_delivery'
            modified_by = request.form.get('modified_by', 'Unknown User')

            if not images or all(f.filename == '' for f in images):
                return jsonify({'success': False, 'error': 'No images selected'}), 400

            # Validate image type
            if image_type not in ['cancellation', 'proof_of_delivery']:
                return jsonify({'success': False, 'error': 'Invalid image type'}), 400

            # Create uploads directory if it doesn't exist
            import os
            upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads', 'orders', order_id)
            os.makedirs(upload_dir, exist_ok=True)

            uploaded_files = []
            for image in images:
                if image and image.filename:
                    # Generate secure filename
                    import uuid
                    from werkzeug.utils import secure_filename

                    filename_base = secure_filename(image.filename)
                    name, ext = os.path.splitext(filename_base)
                    secure_name = f"{image_type}_{uuid.uuid4().hex[:8]}_{name}{ext}"

                    file_path = os.path.join(upload_dir, secure_name)
                    image.save(file_path)

                    # Generate URL path for database storage
                    image_url = f"/static/uploads/orders/{order_id}/{secure_name}"
                    uploaded_files.append(image_url)

                    logger.info(f"Uploaded image: {image_url}")

            if not uploaded_files:
                return jsonify({'success': False, 'error': 'No images were successfully uploaded'}), 400

            # Update order with new image URLs
            order = Order.query.filter_by(id=order_id).first()
            if not order:
                return jsonify({'success': False, 'error': 'Order not found'}), 404

            # Add to existing images
            if image_type == 'cancellation':
                existing_images = json.loads(order.cancellation_images) if order.cancellation_images else []
                existing_images.extend(uploaded_files)
                update_data = {'cancellation_images': existing_images}
            else:
                existing_images = json.loads(order.proof_of_delivery_images) if order.proof_of_delivery_images else []
                existing_images.extend(uploaded_files)
                update_data = {'proof_of_delivery_images': existing_images}

            # Update order
            result = editing_service.update_order_data(
                order_id=order_id,
                update_data=update_data,
                modified_by=modified_by
            )

            if result['success']:
                return jsonify({
                    'success': True,
                    'message': f'Successfully uploaded {len(uploaded_files)} {image_type} images',
                    'uploaded_files': uploaded_files,
                    'total_images': len(existing_images)
                }), 200
            else:
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"Error uploading images for order {order_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/orders/<order_id>/images/<image_type>/<int:image_index>/delete', methods=['DELETE'])
    def api_delete_order_image(order_id, image_type, image_index):
        """API endpoint to delete a specific image"""
        try:
            if image_type not in ['cancellation', 'proof_of_delivery']:
                return jsonify({'success': False, 'error': 'Invalid image type'}), 400

            modified_by = request.args.get('modified_by', 'Unknown User')

            order = Order.query.filter_by(id=order_id).first()
            if not order:
                return jsonify({'success': False, 'error': 'Order not found'}), 404

            # Get current images
            if image_type == 'cancellation':
                images = json.loads(order.cancellation_images) if order.cancellation_images else []
                field_name = 'cancellation_images'
            else:
                images = json.loads(order.proof_of_delivery_images) if order.proof_of_delivery_images else []
                field_name = 'proof_of_delivery_images'

            # Validate index
            if image_index < 0 or image_index >= len(images):
                return jsonify({'success': False, 'error': 'Invalid image index'}), 400

            # Remove image from list
            removed_image = images.pop(image_index)

            # Update order
            update_data = {field_name: images}
            result = editing_service.update_order_data(
                order_id=order_id,
                update_data=update_data,
                modified_by=modified_by
            )

            if result['success']:
                # Try to delete physical file
                try:
                    import os
                    if removed_image.startswith('/static/'):
                        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), removed_image.lstrip('/'))
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            logger.info(f"Deleted physical file: {file_path}")
                except Exception as e:
                    logger.warning(f"Could not delete physical file {removed_image}: {e}")

                return jsonify({
                    'success': True,
                    'message': f'Image deleted successfully',
                    'deleted_image': removed_image,
                    'remaining_images': len(images)
                }), 200
            else:
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"Error deleting image for order {order_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/orders/<order_id>/modification-status')
    def api_get_order_modification_status(order_id):
        """Get modification status for an order"""
        try:
            order = Order.query.filter_by(id=order_id).first()
            if not order:
                return jsonify({'success': False, 'error': 'Order not found'}), 404

            modified_fields = []
            if order.modified_fields:
                modified_fields = json.loads(order.modified_fields)

            return jsonify({
                'success': True,
                'is_modified': order.is_modified or False,
                'modified_fields': modified_fields,
                'last_modified_by': order.last_modified_by,
                'last_modified_at': order.last_modified_at.isoformat() if order.last_modified_at else None,
                'cancellation_images': json.loads(order.cancellation_images) if order.cancellation_images else [],
                'proof_of_delivery_images': json.loads(order.proof_of_delivery_images) if order.proof_of_delivery_images else []
            }), 200

        except Exception as e:
            logger.error(f"Error getting modification status for order {order_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/tours/<tour_id>/modification-status')
    def api_get_tour_modification_status(tour_id):
        """Get modification status for a tour"""
        try:
            import urllib.parse
            tour_id = urllib.parse.unquote(tour_id)

            tour = Tour.query.filter_by(tour_id=tour_id).first()
            if not tour:
                return jsonify({'success': False, 'error': 'Tour not found'}), 404

            modified_fields = []
            if tour.modified_fields:
                modified_fields = json.loads(tour.modified_fields)

            return jsonify({
                'success': True,
                'is_modified': tour.is_modified or False,
                'modified_fields': modified_fields,
                'last_modified_by': tour.last_modified_by,
                'last_modified_at': tour.last_modified_at.isoformat() if tour.last_modified_at else None
            }), 200

        except Exception as e:
            logger.error(f"Error getting modification status for tour {tour_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/orders/<order_id>/transactions/edit', methods=['PUT'])
    def api_update_order_transactions(order_id):
        """Update order transaction details"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400

            modified_by = data.get('modified_by', 'Unknown User')
            transactions = data.get('transactions', [])

            if not transactions:
                return jsonify({'success': False, 'error': 'No transaction data provided'}), 400

            # Find the order
            order = Order.query.filter_by(id=order_id).first()
            if not order:
                return jsonify({'success': False, 'error': 'Order not found'}), 404

            # Update transaction details in raw_data (orderMetadata)
            raw_data = json.loads(order.raw_data) if order.raw_data else {}
            order_metadata = raw_data.get('orderMetadata', {})

            if not order_metadata or not order_metadata.get('lineItems'):
                return jsonify({'success': False, 'error': 'No line items found in order'}), 400

            updated_items = 0
            line_items = order_metadata.get('lineItems', [])

            # Create a mapping from transaction ID to update data
            transaction_updates = {str(txn['id']): txn for txn in transactions}

            # Update each line item's transaction status
            for item in line_items:
                item_id = str(item.get('id', ''))
                if item_id in transaction_updates:
                    update_data = transaction_updates[item_id]

                    # Update transaction status fields
                    if 'transactionStatus' not in item:
                        item['transactionStatus'] = {}

                    transaction_status = item['transactionStatus']

                    if 'ordered_quantity' in update_data:
                        transaction_status['orderedQuantity'] = update_data['ordered_quantity']

                    if 'transacted_quantity' in update_data:
                        transaction_status['transactedQuantity'] = update_data['transacted_quantity']

                    if 'transacted_weight' in update_data and update_data['transacted_weight']:
                        if 'transactedWeight' not in transaction_status:
                            transaction_status['transactedWeight'] = {}
                        transaction_status['transactedWeight']['value'] = update_data['transacted_weight']
                        # Keep existing unit or default to 'kg'
                        if 'unit' not in transaction_status['transactedWeight']:
                            transaction_status['transactedWeight']['unit'] = 'kg'

                    if 'status' in update_data:
                        transaction_status['status'] = update_data['status']

                    updated_items += 1

            # Update the order's raw_data with the modified metadata
            raw_data['orderMetadata'] = order_metadata
            order.raw_data = json.dumps(raw_data)

            # Mark the order as modified and track the fields
            track_field_modification(order, 'transaction_details', modified_by)

            # Save changes
            db.session.commit()

            logger.info(f"Updated transaction details for order {order_id}: {updated_items} items updated by {modified_by}")

            return jsonify({
                'success': True,
                'message': f'Updated {updated_items} transaction items',
                'updated_items': updated_items
            }), 200

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating transaction details for order {order_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500