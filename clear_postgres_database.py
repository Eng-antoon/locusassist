#!/usr/bin/env python3
"""
Script to clear all records from PostgreSQL database tables
"""

import os
import sys
import psycopg2
from psycopg2 import sql
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_postgres_database():
    """Clear all records from all tables in PostgreSQL database"""
    
    # Database configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:@localhost:5432/locus_assistant')
    
    logger.info("🗑️ CLEARING POSTGRESQL DATABASE")
    logger.info(f"Database URL: {DATABASE_URL}")
    
    try:
        # Connect to PostgreSQL database
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        logger.info("✅ Connected to PostgreSQL database")
        
        # Get all table names
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        logger.info(f"Found {len(table_names)} tables: {table_names}")
        
        if not table_names:
            logger.warning("No tables found in the database")
            return True
        
        # Disable foreign key checks temporarily
        logger.info("Disabling foreign key constraints...")
        cursor.execute("SET session_replication_role = replica;")
        
        # Clear all tables
        total_deleted = 0
        for table_name in table_names:
            try:
                # Get count before deletion
                cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table_name)))
                count_before = cursor.fetchone()[0]
                
                # Delete all records
                cursor.execute(sql.SQL("DELETE FROM {}").format(sql.Identifier(table_name)))
                deleted_count = cursor.rowcount
                
                logger.info(f"✅ Cleared table '{table_name}': {deleted_count} records deleted (was {count_before})")
                total_deleted += deleted_count
                
            except Exception as e:
                logger.error(f"❌ Error clearing table '{table_name}': {e}")
                continue
        
        # Re-enable foreign key checks
        logger.info("Re-enabling foreign key constraints...")
        cursor.execute("SET session_replication_role = DEFAULT;")
        
        # Reset sequences for tables with auto-incrementing IDs
        logger.info("Resetting sequences...")
        for table_name in table_names:
            try:
                # Check if table has an ID column
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = %s 
                    AND column_name = 'id' 
                    AND data_type IN ('integer', 'bigint', 'serial', 'bigserial')
                """, (table_name,))
                
                if cursor.fetchone():
                    # Reset sequence
                    sequence_name = f"{table_name}_id_seq"
                    cursor.execute(sql.SQL("SELECT setval(%s, 1, false)").format(), (sequence_name,))
                    logger.info(f"✅ Reset sequence for table '{table_name}'")
                    
            except Exception as e:
                # Sequence might not exist, that's okay
                logger.debug(f"Could not reset sequence for '{table_name}': {e}")
                continue
        
        # Commit all changes
        conn.commit()
        
        logger.info(f"🎉 SUCCESS: Cleared {total_deleted} total records from {len(table_names)} tables")
        
        # Verify tables are empty
        logger.info("Verifying tables are empty...")
        for table_name in table_names:
            cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table_name)))
            count = cursor.fetchone()[0]
            if count == 0:
                logger.info(f"✅ Table '{table_name}' is empty")
            else:
                logger.warning(f"⚠️ Table '{table_name}' still has {count} records")
        
        return True
        
    except psycopg2.Error as e:
        logger.error(f"❌ PostgreSQL error: {e}")
        if conn:
            conn.rollback()
        return False
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
        logger.info("Database connection closed")

def main():
    """Main function"""
    print("🗑️ POSTGRESQL DATABASE CLEARING SCRIPT")
    print("=" * 50)
    
    # Confirm before proceeding
    response = input("⚠️  WARNING: This will delete ALL records from ALL tables in the PostgreSQL database!\nAre you sure you want to continue? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("❌ Operation cancelled by user")
        return False
    
    print("\n🚀 Starting database clearing process...")
    
    try:
        success = clear_postgres_database()
        
        if success:
            print("\n✅ Database clearing completed successfully!")
            print("All tables have been emptied and sequences reset.")
        else:
            print("\n❌ Database clearing failed!")
            return False
            
    except KeyboardInterrupt:
        print("\n❌ Operation interrupted by user")
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
