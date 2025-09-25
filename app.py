#!/usr/bin/env python3
"""
LocusAssist - Logistics Management System
Main entry point for the refactored modular application
"""

import os
import sys
import argparse
from app import create_app

if __name__ == '__main__':
    print("Starting LocusAssist...")

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='LocusAssist Application')
    parser.add_argument('--port', type=int, default=8081, help='Port to run the server on')
    args = parser.parse_args()

    # Get configuration environment
    config_name = os.environ.get('FLASK_ENV', 'development')

    # Create app using factory pattern
    app = create_app(config_name)

    print(f"Running on port {args.port}")
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=args.port)