from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import json

db = SQLAlchemy()

class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.String(255), primary_key=True)  # Locus Order ID
    client_id = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    order_status = db.Column(db.String(50), nullable=False)

    # Location data
    location_name = db.Column(db.String(255))
    location_address = db.Column(db.Text)
    location_city = db.Column(db.String(100))
    location_country_code = db.Column(db.String(10))

    # Location coordinates - NEW FIELDS
    location_latitude = db.Column(db.Float)  # Store latitude coordinates
    location_longitude = db.Column(db.Float)  # Store longitude coordinates

    # Tour/Delivery data
    tour_id = db.Column(db.String(255), index=True)  # Full tour ID from API
    tour_date = db.Column(db.String(20))  # Parsed date from tour ID
    tour_plan_id = db.Column(db.String(100))  # Parsed plan ID from tour ID
    tour_name = db.Column(db.String(50))  # Parsed tour name from tour ID
    tour_number = db.Column(db.Integer)  # Extracted number from tour name for sorting
    rider_name = db.Column(db.String(255))
    rider_id = db.Column(db.String(100))  # Rider ID from fleetInfo
    rider_phone = db.Column(db.String(20))  # Rider phone number
    vehicle_registration = db.Column(db.String(100))
    vehicle_id = db.Column(db.String(100))  # Vehicle ID
    vehicle_model = db.Column(db.String(255))  # Vehicle model name
    transporter_name = db.Column(db.String(255))  # Transporter name

    # Completion data
    completed_on = db.Column(db.DateTime)

    # Task-specific data
    task_source = db.Column(db.String(50))  # Source of the task
    plan_id = db.Column(db.String(255))  # Planning ID
    planned_tour_name = db.Column(db.String(255))  # Planned tour name
    sequence_in_batch = db.Column(db.Integer)  # Order sequence in batch
    partially_delivered = db.Column(db.Boolean, default=False)  # Partial delivery flag
    reassigned = db.Column(db.Boolean, default=False)  # Reassignment flag
    rejected = db.Column(db.Boolean, default=False)  # Rejection flag
    unassigned = db.Column(db.Boolean, default=False)  # Unassigned flag

    # Cancellation information
    cancellation_reason = db.Column(db.String(500))  # Reason for cancellation if order was cancelled

    # Performance metrics
    tardiness = db.Column(db.Float)  # Delay in delivery
    sla_status = db.Column(db.String(50))  # SLA compliance status
    amount_collected = db.Column(db.Float)  # Amount collected
    effective_tat = db.Column(db.Integer)  # Effective turn-around time
    allowed_dwell_time = db.Column(db.Integer)  # Allowed dwell time

    # Time tracking
    eta_updated_on = db.Column(db.DateTime)  # ETA update timestamp
    tour_updated_on = db.Column(db.DateTime)  # Tour update timestamp
    initial_assignment_at = db.Column(db.DateTime)  # Initial assignment time
    initial_assignment_by = db.Column(db.String(255))  # Who assigned initially

    # Additional metadata
    task_time_slot = db.Column(db.String(255))  # Task time slot as string
    skills = db.Column(db.Text)  # JSON string of required skills
    tags = db.Column(db.Text)  # JSON string of tags
    custom_fields = db.Column(db.Text)  # JSON string of custom fields

    # Raw order data from Locus API
    raw_data = db.Column(db.Text)  # JSON string

    # Editing support fields
    is_modified = db.Column(db.Boolean, default=False)  # Flag to indicate manual modifications
    modified_fields = db.Column(db.Text)  # JSON string of modified field names
    cancellation_images = db.Column(db.Text)  # JSON array of cancellation proof image URLs/paths
    proof_of_delivery_images = db.Column(db.Text)  # JSON array of delivery proof image URLs/paths
    last_modified_by = db.Column(db.String(255))  # Who made the last modification
    last_modified_at = db.Column(db.DateTime)  # When the last modification was made

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    line_items = db.relationship('OrderLineItem', backref='order', cascade='all, delete-orphan')
    # validations relationship removed due to FK constraint removal

    def __repr__(self):
        return f'<Order {self.id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'client_id': self.client_id,
            'date': self.date.isoformat() if self.date else None,
            'order_status': self.order_status,
            'location_name': self.location_name,
            'location_address': self.location_address,
            'location_city': self.location_city,
            'location_country_code': self.location_country_code,
            'location_latitude': self.location_latitude,
            'location_longitude': self.location_longitude,
            'tour_id': self.tour_id,
            'tour_date': self.tour_date,
            'tour_plan_id': self.tour_plan_id,
            'tour_name': self.tour_name,
            'tour_number': self.tour_number,
            'rider_name': self.rider_name,
            'rider_id': self.rider_id,
            'rider_phone': self.rider_phone,
            'vehicle_registration': self.vehicle_registration,
            'vehicle_id': self.vehicle_id,
            'vehicle_model': self.vehicle_model,
            'transporter_name': self.transporter_name,
            'completed_on': self.completed_on.isoformat() if self.completed_on else None,
            # Task-specific data
            'task_source': self.task_source,
            'plan_id': self.plan_id,
            'planned_tour_name': self.planned_tour_name,
            'sequence_in_batch': self.sequence_in_batch,
            'partially_delivered': self.partially_delivered,
            'reassigned': self.reassigned,
            'rejected': self.rejected,
            'unassigned': self.unassigned,
            # Cancellation information
            'cancellation_reason': self.cancellation_reason,
            # Performance metrics
            'tardiness': self.tardiness,
            'sla_status': self.sla_status,
            'amount_collected': self.amount_collected,
            'effective_tat': self.effective_tat,
            'allowed_dwell_time': self.allowed_dwell_time,
            # Time tracking
            'eta_updated_on': self.eta_updated_on.isoformat() if self.eta_updated_on else None,
            'tour_updated_on': self.tour_updated_on.isoformat() if self.tour_updated_on else None,
            'initial_assignment_at': self.initial_assignment_at.isoformat() if self.initial_assignment_at else None,
            'initial_assignment_by': self.initial_assignment_by,
            # Additional metadata
            'task_time_slot': self.task_time_slot,
            'skills': json.loads(self.skills) if self.skills else None,
            'tags': json.loads(self.tags) if self.tags else None,
            'custom_fields': json.loads(self.custom_fields) if self.custom_fields else None,
            'raw_data': json.loads(self.raw_data) if self.raw_data else None,
            # Editing support fields
            'is_modified': self.is_modified,
            'modified_fields': json.loads(self.modified_fields) if self.modified_fields else [],
            'cancellation_images': json.loads(self.cancellation_images) if self.cancellation_images else [],
            'proof_of_delivery_images': json.loads(self.proof_of_delivery_images) if self.proof_of_delivery_images else [],
            'last_modified_by': self.last_modified_by,
            'last_modified_at': self.last_modified_at.isoformat() if self.last_modified_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class OrderLineItem(db.Model):
    __tablename__ = 'order_line_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(255), db.ForeignKey('orders.id'), nullable=False)

    # Item data
    sku_id = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    quantity_unit = db.Column(db.String(50))

    # Transaction status
    transacted_quantity = db.Column(db.Integer)
    transaction_status = db.Column(db.String(50))

    # Editing support fields
    is_modified = db.Column(db.Boolean, default=False)  # Flag to indicate manual modifications
    last_modified_by = db.Column(db.String(255))  # Who made the last modification
    last_modified_at = db.Column(db.DateTime)  # When the last modification was made

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<OrderLineItem {self.sku_id} - {self.name}>'

class ValidationResult(db.Model):
    __tablename__ = 'validation_results'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(255), nullable=False)  # Removed FK constraint to allow standalone validation results

    # Validation metadata
    validation_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    grn_image_url = db.Column(db.Text)

    # Results
    is_valid = db.Column(db.Boolean, nullable=False)
    has_document = db.Column(db.Boolean)  # Whether image contains a document
    confidence_score = db.Column(db.Float)

    # AI Response data (JSON strings)
    extracted_items = db.Column(db.Text)  # JSON array of extracted items
    discrepancies = db.Column(db.Text)   # JSON array of discrepancies
    summary = db.Column(db.Text)         # JSON object with summary stats
    gtin_verification = db.Column(db.Text)  # JSON array of GTIN verifications
    ai_response = db.Column(db.Text)     # Raw AI response

    # Processing flags
    is_reprocessed = db.Column(db.Boolean, default=False)
    processing_time = db.Column(db.Float)  # Time taken in seconds

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<ValidationResult {self.order_id} - {"Valid" if self.is_valid else "Invalid"}>'

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'validation_date': self.validation_date.isoformat() if self.validation_date else None,
            'grn_image_url': self.grn_image_url,
            'is_valid': self.is_valid,
            'has_document': self.has_document,
            'confidence_score': self.confidence_score,
            'extracted_items': json.loads(self.extracted_items) if self.extracted_items else [],
            'discrepancies': json.loads(self.discrepancies) if self.discrepancies else [],
            'summary': json.loads(self.summary) if self.summary else {},
            'gtin_verification': json.loads(self.gtin_verification) if self.gtin_verification else [],
            'ai_response': self.ai_response,
            'is_reprocessed': self.is_reprocessed,
            'processing_time': self.processing_time,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class DashboardStats(db.Model):
    __tablename__ = 'dashboard_stats'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)

    # Order statistics
    total_orders = db.Column(db.Integer, default=0)
    completed_orders = db.Column(db.Integer, default=0)
    pending_orders = db.Column(db.Integer, default=0)

    # Validation statistics
    validated_orders = db.Column(db.Integer, default=0)
    valid_grns = db.Column(db.Integer, default=0)
    invalid_grns = db.Column(db.Integer, default=0)
    grns_with_issues = db.Column(db.Integer, default=0)

    # GTIN statistics
    total_gtins_verified = db.Column(db.Integer, default=0)
    gtins_matched = db.Column(db.Integer, default=0)

    # Document detection statistics
    documents_detected = db.Column(db.Integer, default=0)
    no_documents_detected = db.Column(db.Integer, default=0)

    # Average scores
    avg_confidence_score = db.Column(db.Float, default=0.0)
    avg_processing_time = db.Column(db.Float, default=0.0)

    # Timestamps
    last_updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<DashboardStats {self.date}>'

    def to_dict(self):
        return {
            'date': self.date.isoformat() if self.date else None,
            'total_orders': self.total_orders,
            'completed_orders': self.completed_orders,
            'pending_orders': self.pending_orders,
            'validated_orders': self.validated_orders,
            'valid_grns': self.valid_grns,
            'invalid_grns': self.invalid_grns,
            'grns_with_issues': self.grns_with_issues,
            'total_gtins_verified': self.total_gtins_verified,
            'gtins_matched': self.gtins_matched,
            'documents_detected': self.documents_detected,
            'no_documents_detected': self.no_documents_detected,
            'avg_confidence_score': self.avg_confidence_score,
            'avg_processing_time': self.avg_processing_time,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

class Tour(db.Model):
    __tablename__ = 'tours'

    id = db.Column(db.Integer, primary_key=True)
    tour_id = db.Column(db.String(255), unique=True, nullable=False, index=True)  # Full tour ID
    tour_date = db.Column(db.String(20), nullable=False, index=True)  # Parsed date from tour ID
    tour_plan_id = db.Column(db.String(100), nullable=False, index=True)  # Parsed plan ID
    tour_name = db.Column(db.String(50), nullable=False)  # Parsed tour name
    tour_number = db.Column(db.Integer, nullable=False, index=True)  # Extracted number for sorting

    # Tour metadata
    rider_name = db.Column(db.String(255))
    vehicle_registration = db.Column(db.String(100))
    tour_start_time = db.Column(db.DateTime)
    tour_end_time = db.Column(db.DateTime)

    # Statistics
    total_orders = db.Column(db.Integer, default=0)
    completed_orders = db.Column(db.Integer, default=0)
    cancelled_orders = db.Column(db.Integer, default=0)
    pending_orders = db.Column(db.Integer, default=0)

    # Tour status (WAITING, ONGOING, CANCELLED, COMPLETED)
    tour_status = db.Column(db.String(20), default='WAITING')

    # Location summary
    delivery_cities = db.Column(db.Text)  # JSON array of cities
    delivery_areas = db.Column(db.Text)  # JSON array of areas/locations

    # Editing support fields
    is_modified = db.Column(db.Boolean, default=False)  # Flag to indicate manual modifications
    modified_fields = db.Column(db.Text)  # JSON string of modified field names
    last_modified_by = db.Column(db.String(255))  # Who made the last modification
    last_modified_at = db.Column(db.DateTime)  # When the last modification was made

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Tour {self.tour_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'tour_id': self.tour_id,
            'tour_date': self.tour_date,
            'tour_plan_id': self.tour_plan_id,
            'tour_name': self.tour_name,
            'tour_number': self.tour_number,
            'rider_name': self.rider_name,
            'vehicle_registration': self.vehicle_registration,
            'tour_start_time': self.tour_start_time.isoformat() if self.tour_start_time else None,
            'tour_end_time': self.tour_end_time.isoformat() if self.tour_end_time else None,
            'total_orders': self.total_orders,
            'completed_orders': self.completed_orders,
            'cancelled_orders': self.cancelled_orders,
            'pending_orders': self.pending_orders,
            'tour_status': self.tour_status,
            'delivery_cities': json.loads(self.delivery_cities) if self.delivery_cities else [],
            'delivery_areas': json.loads(self.delivery_areas) if self.delivery_areas else [],
            # Editing support fields
            'is_modified': self.is_modified,
            'modified_fields': json.loads(self.modified_fields) if self.modified_fields else [],
            'last_modified_by': self.last_modified_by,
            'last_modified_at': self.last_modified_at.isoformat() if self.last_modified_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def parse_tour_id(tour_id):
        """Parse a tour ID like '2024-09-23-21-15-02*a80a216bd3f74818a5eab97046270932*tour-79'"""
        if not tour_id:
            return None, None, None, None

        try:
            parts = tour_id.split('*')
            if len(parts) != 3:
                return None, None, None, None

            tour_date = parts[0]  # '2024-09-23-21-15-02'
            plan_id = parts[1]    # 'a80a216bd3f74818a5eab97046270932'
            tour_name = parts[2]  # 'tour-79'

            # Extract tour number for sorting
            tour_number = None
            if tour_name.startswith('tour-'):
                try:
                    tour_number = int(tour_name.split('-')[1])
                except (IndexError, ValueError):
                    tour_number = 0

            return tour_date, plan_id, tour_name, tour_number
        except Exception:
            return None, None, None, None