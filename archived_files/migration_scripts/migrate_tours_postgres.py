#!/usr/bin/env python3
"""
Database migration script to add new columns to tours table in PostgreSQL
Run this script to add the cancelled_orders and tour_status columns
"""

import os
import sys
import psycopg2
from datetime import datetime

def migrate_tours_table():
    """Add cancelled_orders and tour_status columns to tours table"""

    # Database configuration from environment or defaults
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:@localhost:5432/locus_assistant')

    print(f"Migrating database: {DATABASE_URL}")

    try:
        # Connect to database
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Check if the tours table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename = 'tours'
            );
        """)

        tours_exists = cursor.fetchone()[0]

        if not tours_exists:
            print("❌ Tours table does not exist. Please ensure the database is initialized first.")
            return

        # Check if columns already exist
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='tours'
            AND table_schema='public';
        """)

        columns = [row[0] for row in cursor.fetchall()]
        print(f"Current columns in tours table: {columns}")

        # Add cancelled_orders column if it doesn't exist
        if 'cancelled_orders' not in columns:
            print("Adding cancelled_orders column...")
            cursor.execute("ALTER TABLE tours ADD COLUMN cancelled_orders INTEGER DEFAULT 0")
            print("✓ cancelled_orders column added")
        else:
            print("✓ cancelled_orders column already exists")

        # Add tour_status column if it doesn't exist
        if 'tour_status' not in columns:
            print("Adding tour_status column...")
            cursor.execute("ALTER TABLE tours ADD COLUMN tour_status VARCHAR(20) DEFAULT 'WAITING'")
            print("✓ tour_status column added")
        else:
            print("✓ tour_status column already exists")

        # Update existing tour records to have proper status
        print("Updating existing tour statuses...")

        # Get all tours and recalculate their status
        cursor.execute("""
            SELECT tour_id, total_orders, completed_orders, pending_orders
            FROM tours
            WHERE tour_status IS NULL OR tour_status = 'WAITING'
        """)

        tours_to_update = cursor.fetchall()

        for tour_id, total_orders, completed_orders, pending_orders in tours_to_update:
            # Calculate cancelled orders
            cursor.execute("""
                SELECT COUNT(*) FROM orders
                WHERE tour_id = %s AND order_status = 'CANCELLED'
            """, (tour_id,))

            cancelled_count_result = cursor.fetchone()
            cancelled_count = cancelled_count_result[0] if cancelled_count_result else 0

            cursor.execute("""
                SELECT COUNT(*) FROM orders
                WHERE tour_id = %s AND order_status = 'COMPLETED'
            """, (tour_id,))

            completed_count_result = cursor.fetchone()
            completed_count = completed_count_result[0] if completed_count_result else 0

            cursor.execute("""
                SELECT COUNT(*) FROM orders
                WHERE tour_id = %s AND order_status = 'WAITING'
            """, (tour_id,))

            waiting_count_result = cursor.fetchone()
            waiting_count = waiting_count_result[0] if waiting_count_result else 0

            # Calculate new status
            if total_orders == 0:
                status = 'WAITING'
            elif cancelled_count == total_orders:
                status = 'CANCELLED'
            elif completed_count + cancelled_count == total_orders:
                status = 'COMPLETED'
            elif waiting_count == total_orders:
                status = 'WAITING'
            else:
                status = 'ONGOING'

            # Update the tour
            cursor.execute("""
                UPDATE tours
                SET cancelled_orders = %s,
                    completed_orders = %s,
                    pending_orders = %s,
                    tour_status = %s
                WHERE tour_id = %s
            """, (cancelled_count, completed_count, total_orders - completed_count - cancelled_count, status, tour_id))

            print(f"Updated tour {tour_id}: {cancelled_count} cancelled, {completed_count} completed, status: {status}")

        # Commit changes
        conn.commit()
        print(f"✓ Migration completed successfully! Updated {len(tours_to_update)} tours.")

    except Exception as e:
        print(f"❌ Error during migration: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Starting PostgreSQL tours table migration...")
    migrate_tours_table()
    print("Migration finished.")