"""
Data Protection Service
Handles protecting manually modified fields from API overwrites
"""

import json
import logging
from datetime import datetime, timezone
from models import Order, OrderLineItem, db

logger = logging.getLogger(__name__)

class DataProtectionService:
    """Service for protecting manually modified data from API overwrites"""

    def __init__(self):
        pass

    def is_field_modified(self, record, field_name):
        """Check if a specific field has been manually modified"""
        try:
            if not record.is_modified or not record.modified_fields:
                return False

            modified_fields = json.loads(record.modified_fields) if isinstance(record.modified_fields, str) else record.modified_fields
            return field_name in modified_fields if isinstance(modified_fields, list) else False

        except (json.JSONDecodeError, AttributeError):
            return False

    def get_protected_fields(self, record):
        """Get list of fields that are protected from API updates"""
        try:
            if not record.is_modified or not record.modified_fields:
                return []

            modified_fields = json.loads(record.modified_fields) if isinstance(record.modified_fields, str) else record.modified_fields
            return modified_fields if isinstance(modified_fields, list) else []

        except (json.JSONDecodeError, AttributeError):
            return []

    def safe_update_order(self, existing_order, order_data, client_id, order_date):
        """Safely update order record, respecting manually modified fields"""
        try:
            logger.info(f"Safe updating order {existing_order.id} (is_modified: {existing_order.is_modified})")

            # Get list of protected fields
            protected_fields = self.get_protected_fields(existing_order)
            if protected_fields:
                logger.info(f"Order {existing_order.id} has {len(protected_fields)} protected fields: {protected_fields}")

            # Always update raw_data and updated_at (system fields)
            existing_order.raw_data = json.dumps(order_data)
            existing_order.updated_at = datetime.now(timezone.utc)

            # Basic fields with protection
            if not self.is_field_modified(existing_order, 'order_status'):
                existing_order.order_status = order_data.get('orderStatus', existing_order.order_status)
            else:
                logger.info(f"Protected field 'order_status' from API update for order {existing_order.id}")

            # Location data with field-level protection
            location = order_data.get('location')
            if location and isinstance(location, dict):
                if not self.is_field_modified(existing_order, 'location_name'):
                    existing_order.location_name = location.get('name', existing_order.location_name)

                address = location.get('address')
                if address and isinstance(address, dict):
                    if not self.is_field_modified(existing_order, 'location_address'):
                        existing_order.location_address = address.get('formattedAddress', existing_order.location_address)
                    if not self.is_field_modified(existing_order, 'location_city'):
                        existing_order.location_city = address.get('city', existing_order.location_city)
                    if not self.is_field_modified(existing_order, 'location_country_code'):
                        existing_order.location_country_code = address.get('countryCode', existing_order.location_country_code)

                # Coordinates - only update if not manually modified
                latLng = location.get('latLng', {})
                if latLng and isinstance(latLng, dict):
                    lat = latLng.get('lat') or latLng.get('latitude')
                    lng = latLng.get('lng') or latLng.get('longitude')

                    if not self.is_field_modified(existing_order, 'location_latitude') and lat is not None:
                        try:
                            existing_order.location_latitude = float(lat)
                            logger.info(f"[COORDINATES] Protected update latitude {lat} for order {existing_order.id}")
                        except (ValueError, TypeError):
                            logger.warning(f"[COORDINATES] Invalid latitude value: {lat}")

                    if not self.is_field_modified(existing_order, 'location_longitude') and lng is not None:
                        try:
                            existing_order.location_longitude = float(lng)
                            logger.info(f"[COORDINATES] Protected update longitude {lng} for order {existing_order.id}")
                        except (ValueError, TypeError):
                            logger.warning(f"[COORDINATES] Invalid longitude value: {lng}")

            # Enhanced fields with protection
            protected_field_mappings = {
                'rider_name': 'rider_name',
                'rider_id': 'rider_id',
                'rider_phone': 'rider_phone',
                'vehicle_registration': 'vehicle_registration',
                'vehicle_id': 'vehicle_id',
                'vehicle_model': 'vehicle_model',
                'transporter_name': 'transporter_name',
                'task_source': 'task_source',
                'plan_id': 'plan_id',
                'planned_tour_name': 'planned_tour_name',
                'sequence_in_batch': 'sequence_in_batch',
                'partially_delivered': 'partially_delivered',
                'reassigned': 'reassigned',
                'rejected': 'rejected',
                'unassigned': 'unassigned',
                'tardiness': 'tardiness',
                'sla_status': 'sla_status',
                'amount_collected': 'amount_collected',
                'effective_tat': 'effective_tat',
                'allowed_dwell_time': 'allowed_dwell_time',
                'task_time_slot': 'task_time_slot',
                'cancellation_reason': 'cancellation_reason'
            }

            for field_key, attr_name in protected_field_mappings.items():
                if field_key in order_data and not self.is_field_modified(existing_order, attr_name):
                    setattr(existing_order, attr_name, order_data.get(field_key))
                elif self.is_field_modified(existing_order, attr_name):
                    logger.debug(f"Protected field '{attr_name}' from API update for order {existing_order.id}")

            # Handle JSON fields with protection
            json_field_mappings = {
                'skills': 'skills',
                'tags': 'tags',
                'custom_fields': 'custom_fields'
            }

            for field_key, attr_name in json_field_mappings.items():
                if field_key in order_data and not self.is_field_modified(existing_order, attr_name):
                    value = order_data.get(field_key)
                    if field_key in ['skills', 'tags']:
                        setattr(existing_order, attr_name, json.dumps(value if isinstance(value, list) else []))
                    elif field_key == 'custom_fields':
                        setattr(existing_order, attr_name, json.dumps(value if isinstance(value, dict) else {}))

            # Handle special assignment field
            if 'initial_assignment_by' in order_data and not self.is_field_modified(existing_order, 'initial_assignment_by'):
                assignment_by = order_data.get('initial_assignment_by')
                existing_order.initial_assignment_by = json.dumps(assignment_by) if isinstance(assignment_by, dict) else assignment_by

            # Handle datetime fields with protection
            datetime_field_mappings = {
                'eta_updated_on': 'eta_updated_on',
                'tour_updated_on': 'tour_updated_on',
                'initial_assignment_at': 'initial_assignment_at'
            }

            for field_key, attr_name in datetime_field_mappings.items():
                if field_key in order_data and order_data.get(field_key) and not self.is_field_modified(existing_order, attr_name):
                    try:
                        setattr(existing_order, attr_name, datetime.fromisoformat(order_data[field_key].replace('Z', '+00:00')))
                    except:
                        logger.warning(f"Could not parse datetime field {field_key} for order {existing_order.id}")

            # Handle completion time from metadata
            order_metadata = order_data.get('orderMetadata')
            if order_metadata and isinstance(order_metadata, dict) and not self.is_field_modified(existing_order, 'completed_on'):
                completion_time = order_metadata.get('homebaseCompleteOn')
                if completion_time:
                    try:
                        existing_order.completed_on = datetime.fromisoformat(completion_time.replace('Z', '+00:00'))
                    except:
                        pass

            # Handle tour data with protection
            self._safe_update_tour_fields(existing_order, order_data)

            # Handle line items with protection
            self._safe_update_line_items(existing_order, order_data)

            logger.info(f"Successfully performed safe update for order {existing_order.id}")

        except Exception as e:
            logger.error(f"Error in safe update for order {existing_order.id}: {e}")
            raise

    def _safe_update_tour_fields(self, existing_order, order_data):
        """Safely update tour-related fields with protection"""
        try:
            # Extract tour data from metadata
            order_metadata = order_data.get('orderMetadata')
            if not order_metadata or not isinstance(order_metadata, dict):
                return

            tour_detail = order_metadata.get('tourDetail')
            if not tour_detail or not isinstance(tour_detail, dict):
                return

            # Update tour ID and related fields if not modified
            tour_id = tour_detail.get('tourId')
            if tour_id and not self.is_field_modified(existing_order, 'tour_id'):
                from models import Tour
                existing_order.tour_id = tour_id

                # Parse tour ID components
                tour_date, plan_id, tour_name, tour_number = Tour.parse_tour_id(tour_id)
                if tour_date:
                    if not self.is_field_modified(existing_order, 'tour_date'):
                        existing_order.tour_date = tour_date
                    if not self.is_field_modified(existing_order, 'tour_plan_id'):
                        existing_order.tour_plan_id = plan_id
                    if not self.is_field_modified(existing_order, 'tour_name'):
                        existing_order.tour_name = tour_name
                    if not self.is_field_modified(existing_order, 'tour_number'):
                        existing_order.tour_number = tour_number or 0

            # Update rider name and vehicle from tour detail if not modified
            if not self.is_field_modified(existing_order, 'rider_name') and tour_detail.get('riderName'):
                existing_order.rider_name = tour_detail.get('riderName')
            if not self.is_field_modified(existing_order, 'vehicle_registration') and tour_detail.get('vehicleRegistrationNumber'):
                existing_order.vehicle_registration = tour_detail.get('vehicleRegistrationNumber')

        except Exception as e:
            logger.error(f"Error updating tour fields for order {existing_order.id}: {e}")

    def _safe_update_line_items(self, existing_order, order_data):
        """Safely update line items with protection"""
        try:
            # Check if line items have been manually modified
            if self.is_field_modified(existing_order, 'line_items'):
                logger.info(f"Line items for order {existing_order.id} were manually modified - skipping API update")
                return

            # If not manually modified, update line items normally
            from models import OrderLineItem

            # Remove old line items
            OrderLineItem.query.filter_by(order_id=existing_order.id).delete()

            # Add new line items
            line_items = order_data.get('lineItems', [])
            for item in line_items:
                line_item = OrderLineItem(
                    order_id=existing_order.id,
                    sku_id=item.get('skuId', ''),
                    name=item.get('name', ''),
                    quantity=item.get('quantity', 0),
                    quantity_unit=item.get('quantityUnit', ''),
                    transacted_quantity=item.get('transactedQuantity'),
                    transaction_status=item.get('transactionStatus', '')
                )
                db.session.add(line_item)

            logger.info(f"Updated {len(line_items)} line items for order {existing_order.id}")

        except Exception as e:
            logger.error(f"Error updating line items for order {existing_order.id}: {e}")

    def log_protection_summary(self, order_id, total_fields_checked, protected_fields_count):
        """Log a summary of data protection actions"""
        if protected_fields_count > 0:
            logger.info(f"Data Protection Summary for Order {order_id}: Protected {protected_fields_count} out of {total_fields_checked} fields from API overwrite")
        else:
            logger.debug(f"Data Protection Summary for Order {order_id}: No protected fields, updated {total_fields_checked} fields from API")

# Global service instance
data_protection_service = DataProtectionService()