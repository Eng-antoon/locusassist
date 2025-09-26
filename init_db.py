#!/usr/bin/env python3
"""
Initialize the database with all tables
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import db, Tour, Order
from flask import Flask

def init_database():
    """Initialize database with all tables"""

    print("Initializing database...")

    # Create Flask app
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///locusassist.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        # Create all tables
        db.create_all()
        print("✅ All tables created successfully!")

        # Show created tables
        from sqlalchemy import text
        result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        tables = result.fetchall()

        print("\n📋 Created tables:")
        for table in tables:
            print(f"  - {table[0]}")

        # Show tours table schema if it exists
        try:
            result = db.session.execute(text("PRAGMA table_info(tours);"))
            columns = result.fetchall()
            print(f"\n📋 Tours table schema ({len(columns)} columns):")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
        except Exception as e:
            print(f"Could not show tours table schema: {e}")

if __name__ == '__main__':
    init_database()