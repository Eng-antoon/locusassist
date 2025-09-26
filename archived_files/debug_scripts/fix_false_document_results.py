#!/usr/bin/env python3
"""
Script to fix validation results that incorrectly have has_document=False
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import ValidationResult

def fix_false_document_results():
    """Fix validation results that have has_document=False but should be True"""
    with app.app_context():
        print("Checking validation results with has_document=False...")

        # Find all validation results where has_document is False
        false_results = ValidationResult.query.filter(ValidationResult.has_document == False).all()

        print(f"Found {len(false_results)} validation results with has_document=False")

        if len(false_results) == 0:
            print("No records to fix.")
            return

        # For debugging, let's see what these contain
        for result in false_results:
            print(f"\nOrder {result.order_id}:")
            print(f"  has_document: {result.has_document}")
            print(f"  is_valid: {result.is_valid}")
            print(f"  confidence_score: {result.confidence_score}")
            print(f"  GRN URL: {result.grn_image_url}")

            # Check if there are extracted_items or discrepancies
            extracted_items = result.extracted_items
            discrepancies = result.discrepancies

            print(f"  extracted_items length: {len(extracted_items) if extracted_items else 0}")
            print(f"  discrepancies length: {len(discrepancies) if discrepancies else 0}")

            # If there are extracted items or discrepancies, the document was likely readable
            if (extracted_items and len(extracted_items) > 0) or (discrepancies and len(discrepancies) > 0):
                print(f"  -> This order has validation data, updating has_document to True")
                result.has_document = True
            else:
                print(f"  -> This order appears to truly have no document detected")

        try:
            db.session.commit()
            print(f"\nUpdated validation results saved to database")
        except Exception as e:
            print(f"Error updating records: {e}")
            db.session.rollback()

if __name__ == "__main__":
    fix_false_document_results()