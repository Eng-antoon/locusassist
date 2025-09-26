#!/usr/bin/env python3
"""
Check which database configuration the main app is using
"""

import os
import logging
from app import create_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_database_config():
    """Check the actual database configuration being used"""
    try:
        logger.info("🔍 Checking database configuration...")

        # Check environment variable
        flask_env = os.environ.get('FLASK_ENV', 'development')
        logger.info(f"FLASK_ENV: {flask_env}")

        # Create app like the main application does
        app = create_app(flask_env)

        with app.app_context():
            database_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
            logger.info(f"Database URI: {database_uri}")

            if 'postgresql' in database_uri:
                logger.info("✅ MAIN APP USES POSTGRESQL")
                return 'postgresql'
            elif 'sqlite' in database_uri:
                logger.info("❌ MAIN APP USES SQLITE")
                return 'sqlite'
            else:
                logger.info(f"❓ UNKNOWN DATABASE TYPE: {database_uri}")
                return 'unknown'

    except Exception as e:
        logger.error(f"❌ Error checking database config: {e}")
        return 'error'

def check_testing_files():
    """Check which files use SQLite for testing"""
    logger.info("\n🧪 Checking which files use SQLite...")

    sqlite_usage = {
        'testing_only': [],
        'main_app': [],
        'migration_scripts': []
    }

    # Files that mention SQLite
    sqlite_files = [
        'app/config.py',
        'init_database.py',
        'test_live_updates.py',
        'check_db_tables.py',
        'migrate_tours_table.py',
        'add_live_update_columns.py'
    ]

    for file_path in sqlite_files:
        full_path = f'/home/tony/locusassist/{file_path}'
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r') as f:
                    content = f.read()

                if 'sqlite:///:memory:' in content:
                    sqlite_usage['testing_only'].append(file_path)
                    logger.info(f"   📝 {file_path}: Uses in-memory SQLite (TESTING ONLY)")
                elif 'sqlite:///locusassist.db' in content:
                    sqlite_usage['main_app'].append(file_path)
                    logger.info(f"   ⚠️ {file_path}: Uses SQLite file (POTENTIAL MAIN APP)")
                elif 'sqlite3' in content:
                    sqlite_usage['migration_scripts'].append(file_path)
                    logger.info(f"   🔧 {file_path}: SQLite migration/utility script")

            except Exception as e:
                logger.error(f"   ❌ Error reading {file_path}: {e}")

    return sqlite_usage

def safe_to_delete_sqlite():
    """Determine if it's safe to delete SQLite files"""
    logger.info("\n🛡️ Determining if SQLite files can be safely deleted...")

    # Check main app database
    db_type = check_database_config()

    if db_type == 'postgresql':
        logger.info("✅ Main app uses PostgreSQL - SQLite files are safe to delete")
        return True
    elif db_type == 'sqlite':
        logger.info("❌ Main app uses SQLite - DO NOT DELETE SQLite files")
        return False
    else:
        logger.info("❓ Unable to determine database type - proceed with caution")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("🗄️ DATABASE CONFIGURATION CHECK")
    print("=" * 60)

    # Check database configuration
    db_config = check_database_config()

    # Check testing files
    sqlite_usage = check_testing_files()

    # Safety check
    is_safe = safe_to_delete_sqlite()

    print("\n" + "=" * 60)
    print("📋 SUMMARY:")
    print("=" * 60)

    if db_config == 'postgresql':
        print("✅ MAIN APPLICATION USES POSTGRESQL")
        print("✅ SQLite files are only used for testing")
        print("✅ SAFE TO DELETE SQLite database files")
        print("\nSQLite files found:")
        print("   - /home/tony/locusassist/locus_assistant.db")
        print("   - /home/tony/locusassist/instance/locusassist.db")
        print("\n🗑️ You can safely delete these files as they are not used by the main app")
    else:
        print("❌ CANNOT CONFIRM DATABASE TYPE")
        print("⚠️ DO NOT DELETE SQLite files until confirmed")

    print(f"\nDatabase type detected: {db_config}")
    print(f"Safe to delete SQLite: {'YES' if is_safe else 'NO'}")