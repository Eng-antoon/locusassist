#!/usr/bin/env python3
"""
Script to check what tables exist in the database
"""

import sqlite3
import os

def check_tables():
    """Check what tables exist in the database"""

    # Database path
    db_path = os.path.join(os.path.dirname(__file__), 'locus_assistant.db')

    print(f"Checking database: {db_path}")

    if not os.path.exists(db_path):
        print("❌ Database file does not exist")
        return

    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        if tables:
            print("📋 Tables in database:")
            for table in tables:
                print(f"  - {table[0]}")

                # Show table structure
                cursor.execute(f"PRAGMA table_info({table[0]})")
                columns = cursor.fetchall()
                print(f"    Columns: {len(columns)}")
                for col in columns:
                    print(f"      • {col[1]} ({col[2]})")
                print()
        else:
            print("❌ No tables found in database")

    except Exception as e:
        print(f"❌ Error checking database: {e}")

    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_tables()