"""
Database migration to add comprehensive editing support with modification tracking
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app import create_app
from models import db

def add_editing_support_fields():
    """Add fields to support comprehensive Tour and Order editing"""

    # SQL statements to add new fields
    sql_statements = [
        # Orders table - Add modification tracking and image fields
        """
        ALTER TABLE orders ADD COLUMN IF NOT EXISTS is_modified BOOLEAN DEFAULT FALSE;
        """,
        """
        ALTER TABLE orders ADD COLUMN IF NOT EXISTS modified_fields TEXT; -- JSON string of modified field names
        """,
        """
        ALTER TABLE orders ADD COLUMN IF NOT EXISTS cancellation_images TEXT; -- JSON array of image URLs/paths
        """,
        """
        ALTER TABLE orders ADD COLUMN IF NOT EXISTS proof_of_delivery_images TEXT; -- JSON array of image URLs/paths
        """,
        """
        ALTER TABLE orders ADD COLUMN IF NOT EXISTS last_modified_by VARCHAR(255);
        """,
        """
        ALTER TABLE orders ADD COLUMN IF NOT EXISTS last_modified_at TIMESTAMP;
        """,

        # Tours table - Add modification tracking
        """
        ALTER TABLE tours ADD COLUMN IF NOT EXISTS is_modified BOOLEAN DEFAULT FALSE;
        """,
        """
        ALTER TABLE tours ADD COLUMN IF NOT EXISTS modified_fields TEXT; -- JSON string of modified field names
        """,
        """
        ALTER TABLE tours ADD COLUMN IF NOT EXISTS last_modified_by VARCHAR(255);
        """,
        """
        ALTER TABLE tours ADD COLUMN IF NOT EXISTS last_modified_at TIMESTAMP;
        """,

        # Order Line Items table - Add modification tracking
        """
        ALTER TABLE order_line_items ADD COLUMN IF NOT EXISTS is_modified BOOLEAN DEFAULT FALSE;
        """,
        """
        ALTER TABLE order_line_items ADD COLUMN IF NOT EXISTS last_modified_at TIMESTAMP;
        """,
        """
        ALTER TABLE order_line_items ADD COLUMN IF NOT EXISTS last_modified_by VARCHAR(255);
        """,

        # Add indexes for performance
        """
        CREATE INDEX IF NOT EXISTS idx_orders_is_modified ON orders(is_modified);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_tours_is_modified ON tours(is_modified);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_orders_last_modified_at ON orders(last_modified_at);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_tours_last_modified_at ON tours(last_modified_at);
        """
    ]

    try:
        for sql in sql_statements:
            db.session.execute(text(sql))

        db.session.commit()
        print("✅ Successfully added editing support fields to database")
        return True

    except Exception as e:
        print(f"❌ Error adding editing support fields: {e}")
        db.session.rollback()
        return False

if __name__ == "__main__":
    # Create Flask app and run migration within app context
    app = create_app('development')
    with app.app_context():
        add_editing_support_fields()