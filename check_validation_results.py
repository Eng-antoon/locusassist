#!/usr/bin/env python3
"""
Script to check validation results in the database
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import ValidationResult

def check_validation_results():
    """Check validation results in database"""
    with app.app_context():
        print("Checking all validation results...")

        # Get all validation results
        results = ValidationResult.query.all()

        print(f"Found {len(results)} validation results total")

        if len(results) == 0:
            print("No validation results found.")
            return

        # Group by has_document value
        has_document_counts = {}
        sample_results = []

        for result in results:
            has_doc_value = result.has_document
            if has_doc_value not in has_document_counts:
                has_document_counts[has_doc_value] = 0
            has_document_counts[has_doc_value] += 1

            # Keep first few results as samples
            if len(sample_results) < 3:
                sample_results.append(result)

        print("\nhas_document field distribution:")
        for value, count in has_document_counts.items():
            print(f"  {value}: {count} records")

        print("\nSample results:")
        for result in sample_results:
            print(f"  Order {result.order_id}: has_document={result.has_document}, is_valid={result.is_valid}")

if __name__ == "__main__":
    check_validation_results()