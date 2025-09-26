#!/usr/bin/env python3
"""
Database migration script to add live update columns to the orders table.
Run this script after updating the models.py file.
"""

import sqlite3
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_live_update_columns():
    """Add the new live update columns to the orders table"""

    # Database file path
    db_path = '/home/tony/locusassist/locusassist.db'

    if not os.path.exists(db_path):
        logger.error(f"Database file not found at {db_path}")
        return False

    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # List of columns to add
        columns_to_add = [
            ('effective_status', 'VARCHAR(50)'),
            ('status_updates', 'TEXT'),
            ('cancellation_reason', 'VARCHAR(500)'),
            ('last_status_update', 'DATETIME'),
            ('status_actor', 'VARCHAR(255)'),
            ('live_update_data', 'TEXT')
        ]

        logger.info("Adding live update columns to orders table...")

        # Get existing columns
        cursor.execute("PRAGMA table_info(orders)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        logger.info(f"Existing columns: {existing_columns}")

        # Add each column if it doesn't exist
        added_columns = []
        for column_name, column_type in columns_to_add:
            if column_name not in existing_columns:
                alter_sql = f"ALTER TABLE orders ADD COLUMN {column_name} {column_type}"
                logger.info(f"Executing: {alter_sql}")
                cursor.execute(alter_sql)
                added_columns.append(column_name)
            else:
                logger.info(f"Column {column_name} already exists, skipping")

        # Commit changes
        conn.commit()

        if added_columns:
            logger.info(f"Successfully added columns: {added_columns}")
        else:
            logger.info("All columns already exist")

        # Verify columns were added
        cursor.execute("PRAGMA table_info(orders)")
        new_columns = [row[1] for row in cursor.fetchall()]
        logger.info(f"New columns list: {new_columns}")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Error adding columns: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == '__main__':
    logger.info("Starting database migration to add live update columns...")
    success = add_live_update_columns()
    if success:
        logger.info("Migration completed successfully!")
    else:
        logger.error("Migration failed!")
        exit(1)