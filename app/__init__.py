import logging
from flask import Flask
from models import db
from app.config import config
from app.utils import init_db_connection
from app.routes import register_routes

def create_app(config_name=None):
    """Flask app factory"""
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static')

    # Load configuration
    if config_name is None:
        import os
        config_name = os.environ.get('FLASK_ENV', 'default')

    app.config.from_object(config[config_name])

    # Initialize database
    db.init_app(app)

    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Register routes
    register_routes(app, config[config_name])

    # Initialize database tables
    with app.app_context():
        if init_db_connection(app):
            logger.info("Database initialized successfully")
        else:
            logger.warning("Database initialization failed. Some features may not work correctly.")

    logger.info("LocusAssist application created successfully")
    return app