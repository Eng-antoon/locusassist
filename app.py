#!/usr/bin/env python3
"""
LocusAssist - Logistics Management System
Main entry point for the refactored modular application
"""

import os
from app import create_app

if __name__ == '__main__':
    print("Starting LocusAssist...")

    # Get configuration environment
    config_name = os.environ.get('FLASK_ENV', 'development')

    # Create app using factory pattern
    app = create_app(config_name)

    # Run the application
    app.run(debug=True, host='0.0.0.0', port=8080)