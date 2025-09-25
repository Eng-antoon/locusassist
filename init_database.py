#!/usr/bin/env python3
"""
Initialize the database with updated models including live update columns.
"""

import sys
import os

# Add the current directory to the Python path so we can import our modules
sys.path.insert(0, '/home/tony/locusassist')

from flask import Flask
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app_and_db():
    """Create Flask app and initialize database"""
    app = Flask(__name__)

    # Configure the database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///locusassist.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Import and initialize the database
    from models import db

    # Initialize the database with the app
    db.init_app(app)

    # Create all tables
    with app.app_context():
        logger.info("Creating database tables...")
        db.create_all()
        logger.info("Database tables created successfully!")

        # List all tables to confirm
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        logger.info(f"Created tables: {tables}")

        # Check orders table columns
        if 'orders' in tables:
            columns = inspector.get_columns('orders')
            column_names = [col['name'] for col in columns]
            logger.info(f"Orders table columns: {column_names}")

            # Check if live update columns are present
            live_update_columns = ['effective_status', 'status_updates', 'cancellation_reason',
                                 'last_status_update', 'status_actor', 'live_update_data']
            missing_columns = [col for col in live_update_columns if col not in column_names]
            if missing_columns:
                logger.warning(f"Missing live update columns: {missing_columns}")
            else:
                logger.info("All live update columns are present!")

    return True

if __name__ == '__main__':
    logger.info("Initializing database with updated models...")
    try:
        success = create_app_and_db()
        if success:
            logger.info("Database initialization completed successfully!")
        else:
            logger.error("Database initialization failed!")
            exit(1)
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        exit(1)