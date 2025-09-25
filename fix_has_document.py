#!/usr/bin/env python3
"""
Script to fix has_document field in existing validation results
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import ValidationResult

def fix_has_document_field():
    """Fix has_document field for existing validation results"""
    with app.app_context():
        print("Checking validation results with NULL has_document field...")

        # Find all validation results where has_document is NULL
        null_results = ValidationResult.query.filter(ValidationResult.has_document.is_(None)).all()

        print(f"Found {len(null_results)} validation results with NULL has_document field")

        if len(null_results) == 0:
            print("No records to fix.")
            return

        # Update them to True (assuming they were processed successfully if they exist)
        updated_count = 0
        for result in null_results:
            print(f"Updating validation result for order {result.order_id}")
            result.has_document = True
            updated_count += 1

        try:
            db.session.commit()
            print(f"Successfully updated {updated_count} validation results")
        except Exception as e:
            print(f"Error updating records: {e}")
            db.session.rollback()

if __name__ == "__main__":
    fix_has_document_field()