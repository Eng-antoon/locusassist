#!/usr/bin/env python3
"""
Migration: Add rider_id and rider_phone fields to tours table
"""

import sqlite3
import os
import sys

def run_migration():
    """Add rider_id and rider_phone columns to tours table"""
    try:
        # Get the database path
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'locusassist.db')

        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("Adding rider_id and rider_phone columns to tours table...")

        # Add rider_id column
        try:
            cursor.execute("ALTER TABLE tours ADD COLUMN rider_id VARCHAR(100)")
            print("✅ Added rider_id column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("⚠️ rider_id column already exists")
            else:
                raise e

        # Add rider_phone column
        try:
            cursor.execute("ALTER TABLE tours ADD COLUMN rider_phone VARCHAR(20)")
            print("✅ Added rider_phone column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("⚠️ rider_phone column already exists")
            else:
                raise e

        # Commit changes
        conn.commit()
        print("✅ Migration completed successfully!")

        # Show current tours table schema
        cursor.execute("PRAGMA table_info(tours)")
        columns = cursor.fetchall()
        print("\n📋 Current tours table schema:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)