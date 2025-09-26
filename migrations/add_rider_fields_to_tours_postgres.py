#!/usr/bin/env python3
"""
Migration: Add rider_id and rider_phone fields to tours table (PostgreSQL)
"""

import os
import sys
import psycopg2
from psycopg2 import sql

def run_migration():
    """Add rider_id and rider_phone columns to tours table"""

    # Database configuration from environment or defaults
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:@localhost:5432/locus_assistant')

    print(f"Migrating database: {DATABASE_URL}")
    print("Adding rider_id and rider_phone columns to tours table...")

    try:
        # Connect to database
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Check if the tours table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'tours'
            );
        """)

        table_exists = cursor.fetchone()[0]
        if not table_exists:
            print("❌ tours table does not exist. Please create the table first.")
            return False

        # Check if rider_id column already exists
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'tours' AND column_name = 'rider_id';
        """)

        rider_id_exists = cursor.fetchone() is not None

        # Check if rider_phone column already exists
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'tours' AND column_name = 'rider_phone';
        """)

        rider_phone_exists = cursor.fetchone() is not None

        # Add rider_id column if it doesn't exist
        if not rider_id_exists:
            cursor.execute("ALTER TABLE tours ADD COLUMN rider_id VARCHAR(100);")
            print("✅ Added rider_id column")
        else:
            print("⚠️ rider_id column already exists")

        # Add rider_phone column if it doesn't exist
        if not rider_phone_exists:
            cursor.execute("ALTER TABLE tours ADD COLUMN rider_phone VARCHAR(20);")
            print("✅ Added rider_phone column")
        else:
            print("⚠️ rider_phone column already exists")

        # Commit changes
        conn.commit()
        print("✅ Migration completed successfully!")

        # Show current tours table schema
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'tours'
            ORDER BY ordinal_position;
        """)

        columns = cursor.fetchall()
        print("\n📋 Current tours table schema:")
        for col in columns:
            col_name, data_type, max_length = col
            if max_length:
                print(f"  - {col_name} ({data_type}({max_length}))")
            else:
                print(f"  - {col_name} ({data_type})")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()
            conn.close()
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if 'conn' in locals() and conn:
            conn.close()
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)