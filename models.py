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

    # Tour/Delivery data
    rider_name = db.Column(db.String(255))
    vehicle_registration = db.Column(db.String(100))

    # Completion data
    completed_on = db.Column(db.DateTime)

    # Raw order data from Locus API
    raw_data = db.Column(db.Text)  # JSON string

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
            'rider_name': self.rider_name,
            'vehicle_registration': self.vehicle_registration,
            'completed_on': self.completed_on.isoformat() if self.completed_on else None,
            'raw_data': json.loads(self.raw_data) if self.raw_data else None,
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