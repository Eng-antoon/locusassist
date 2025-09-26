#!/usr/bin/env python3
"""
Migrate data from SQLite to PostgreSQL and remove SQLite databases
"""

import logging
import sqlite3
import os
from app import create_app
from models import db, Order, OrderLineItem, ValidationResult, DashboardStats, Tour
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_sqlite_data():
    """Check what data exists in SQLite databases"""
    sqlite_files = [
        '/home/tony/locusassist/locus_assistant.db',
        '/home/tony/locusassist/instance/locusassist.db'
    ]

    data_found = False

    for sqlite_path in sqlite_files:
        if not os.path.exists(sqlite_path):
            continue

        logger.info(f"🔍 Checking SQLite database: {sqlite_path}")

        try:
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()

            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence';")
            tables = cursor.fetchall()

            if not tables:
                logger.info(f"   No tables found in {sqlite_path}")
                conn.close()
                continue

            logger.info(f"   Found {len(tables)} tables:")

            total_records = 0
            for (table_name,) in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                logger.info(f"     - {table_name}: {count} records")
                total_records += count

            if total_records > 0:
                data_found = True
                logger.info(f"   📊 Total records in {sqlite_path}: {total_records}")
            else:
                logger.info(f"   ✅ No data in {sqlite_path}")

            conn.close()

        except Exception as e:
            logger.error(f"   ❌ Error checking {sqlite_path}: {e}")

    return data_found

def migrate_sqlite_to_postgres():
    """Migrate data from SQLite to PostgreSQL"""
    try:
        app = create_app('development')

        with app.app_context():
            logger.info("🔄 Starting SQLite to PostgreSQL migration...")

            # Check current PostgreSQL data
            postgres_orders = Order.query.count()
            postgres_validations = ValidationResult.query.count()
            postgres_tours = Tour.query.count()

            logger.info(f"📊 Current PostgreSQL data:")
            logger.info(f"   - Orders: {postgres_orders}")
            logger.info(f"   - Validations: {postgres_validations}")
            logger.info(f"   - Tours: {postgres_tours}")

            # Connect to SQLite
            sqlite_path = '/home/tony/locusassist/instance/locusassist.db'
            if not os.path.exists(sqlite_path):
                logger.info("✅ No SQLite data to migrate")
                return True

            sqlite_conn = sqlite3.connect(sqlite_path)
            sqlite_conn.row_factory = sqlite3.Row  # Enable column access by name
            sqlite_cursor = sqlite_conn.cursor()

            # Check if we need to migrate
            sqlite_cursor.execute("SELECT COUNT(*) FROM orders")
            sqlite_order_count = sqlite_cursor.fetchone()[0]

            logger.info(f"📊 SQLite data found:")
            logger.info(f"   - Orders: {sqlite_order_count}")

            if sqlite_order_count == 0:
                logger.info("✅ No SQLite data to migrate")
                sqlite_conn.close()
                return True

            # Migrate Orders
            logger.info("🔄 Migrating orders...")
            migrated_orders = 0
            skipped_orders = 0

            sqlite_cursor.execute("SELECT * FROM orders")
            sqlite_orders = sqlite_cursor.fetchall()

            for sqlite_order in sqlite_orders:
                try:
                    # Check if order already exists in PostgreSQL
                    existing_order = Order.query.filter_by(id=sqlite_order['id']).first()

                    if existing_order:
                        # Update existing order with any missing coordinate data
                        if (existing_order.location_latitude is None and
                            sqlite_order['location_latitude'] is not None):
                            existing_order.location_latitude = sqlite_order['location_latitude']
                            existing_order.location_longitude = sqlite_order['location_longitude']
                            logger.info(f"   📍 Updated coordinates for {sqlite_order['id']}")
                        skipped_orders += 1
                        continue

                    # Create new order in PostgreSQL
                    new_order = Order(
                        id=sqlite_order['id'],
                        client_id=sqlite_order['client_id'],
                        date=datetime.strptime(sqlite_order['date'], '%Y-%m-%d').date() if sqlite_order['date'] else None,
                        order_status=sqlite_order['order_status'],
                        location_name=sqlite_order['location_name'],
                        location_address=sqlite_order['location_address'],
                        location_city=sqlite_order['location_city'],
                        location_country_code=sqlite_order['location_country_code'],
                        location_latitude=sqlite_order['location_latitude'],
                        location_longitude=sqlite_order['location_longitude'],
                        tour_id=sqlite_order['tour_id'],
                        tour_date=sqlite_order['tour_date'],
                        tour_plan_id=sqlite_order['tour_plan_id'],
                        tour_name=sqlite_order['tour_name'],
                        tour_number=sqlite_order['tour_number'],
                        rider_name=sqlite_order['rider_name'],
                        rider_id=sqlite_order['rider_id'],
                        rider_phone=sqlite_order['rider_phone'],
                        vehicle_registration=sqlite_order['vehicle_registration'],
                        vehicle_id=sqlite_order['vehicle_id'],
                        vehicle_model=sqlite_order['vehicle_model'],
                        transporter_name=sqlite_order['transporter_name'],
                        completed_on=datetime.fromisoformat(sqlite_order['completed_on']) if sqlite_order['completed_on'] else None,
                        task_source=sqlite_order['task_source'],
                        plan_id=sqlite_order['plan_id'],
                        planned_tour_name=sqlite_order['planned_tour_name'],
                        sequence_in_batch=sqlite_order['sequence_in_batch'],
                        partially_delivered=bool(sqlite_order['partially_delivered']),
                        reassigned=bool(sqlite_order['reassigned']),
                        rejected=bool(sqlite_order['rejected']),
                        unassigned=bool(sqlite_order['unassigned']),
                        cancellation_reason=sqlite_order['cancellation_reason'],
                        tardiness=sqlite_order['tardiness'],
                        sla_status=sqlite_order['sla_status'],
                        amount_collected=sqlite_order['amount_collected'],
                        effective_tat=sqlite_order['effective_tat'],
                        allowed_dwell_time=sqlite_order['allowed_dwell_time'],
                        eta_updated_on=datetime.fromisoformat(sqlite_order['eta_updated_on']) if sqlite_order['eta_updated_on'] else None,
                        tour_updated_on=datetime.fromisoformat(sqlite_order['tour_updated_on']) if sqlite_order['tour_updated_on'] else None,
                        initial_assignment_at=datetime.fromisoformat(sqlite_order['initial_assignment_at']) if sqlite_order['initial_assignment_at'] else None,
                        initial_assignment_by=sqlite_order['initial_assignment_by'],
                        task_time_slot=sqlite_order['task_time_slot'],
                        skills=sqlite_order['skills'],
                        tags=sqlite_order['tags'],
                        custom_fields=sqlite_order['custom_fields'],
                        raw_data=sqlite_order['raw_data']
                    )

                    db.session.add(new_order)
                    migrated_orders += 1

                    if migrated_orders % 100 == 0:
                        db.session.commit()
                        logger.info(f"   ✅ Migrated {migrated_orders} orders...")

                except Exception as e:
                    logger.error(f"   ❌ Error migrating order {sqlite_order['id']}: {e}")
                    continue

            # Migrate ValidationResults
            logger.info("🔄 Migrating validation results...")
            migrated_validations = 0

            try:
                sqlite_cursor.execute("SELECT * FROM validation_results")
                sqlite_validations = sqlite_cursor.fetchall()

                for sqlite_validation in sqlite_validations:
                    try:
                        # Check if validation already exists
                        existing_validation = ValidationResult.query.filter_by(
                            order_id=sqlite_validation['order_id'],
                            grn_image_url=sqlite_validation['grn_image_url']
                        ).first()

                        if existing_validation:
                            continue

                        new_validation = ValidationResult(
                            order_id=sqlite_validation['order_id'],
                            validation_date=datetime.fromisoformat(sqlite_validation['validation_date']) if sqlite_validation['validation_date'] else datetime.now(),
                            grn_image_url=sqlite_validation['grn_image_url'],
                            is_valid=bool(sqlite_validation['is_valid']),
                            has_document=bool(sqlite_validation['has_document']) if sqlite_validation['has_document'] is not None else None,
                            confidence_score=sqlite_validation['confidence_score'],
                            extracted_items=sqlite_validation['extracted_items'],
                            discrepancies=sqlite_validation['discrepancies'],
                            summary=sqlite_validation['summary'],
                            gtin_verification=sqlite_validation['gtin_verification'],
                            ai_response=sqlite_validation['ai_response'],
                            is_reprocessed=bool(sqlite_validation['is_reprocessed']),
                            processing_time=sqlite_validation['processing_time']
                        )

                        db.session.add(new_validation)
                        migrated_validations += 1

                    except Exception as e:
                        logger.error(f"   ❌ Error migrating validation {sqlite_validation['id']}: {e}")
                        continue

            except Exception as e:
                logger.warning(f"No validation_results table in SQLite or error: {e}")

            # Commit all changes
            db.session.commit()

            logger.info(f"✅ Migration completed:")
            logger.info(f"   - Orders migrated: {migrated_orders}")
            logger.info(f"   - Orders skipped (already exist): {skipped_orders}")
            logger.info(f"   - Validations migrated: {migrated_validations}")

            sqlite_conn.close()
            return True

    except Exception as e:
        logger.error(f"❌ Error during migration: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def remove_sqlite_files():
    """Remove SQLite database files after successful migration"""
    sqlite_files = [
        '/home/tony/locusassist/locus_assistant.db',
        '/home/tony/locusassist/instance/locusassist.db'
    ]

    removed_files = []
    for sqlite_path in sqlite_files:
        if os.path.exists(sqlite_path):
            try:
                # Create backup first
                backup_path = f"{sqlite_path}.backup"
                os.rename(sqlite_path, backup_path)
                logger.info(f"📦 Backed up {sqlite_path} to {backup_path}")
                removed_files.append(sqlite_path)
            except Exception as e:
                logger.error(f"❌ Error backing up {sqlite_path}: {e}")

    return removed_files

def main():
    """Main migration process"""
    logger.info("🗄️ SQLITE TO POSTGRESQL MIGRATION")
    logger.info("=" * 60)

    # Step 1: Check what SQLite data exists
    has_sqlite_data = check_sqlite_data()

    if not has_sqlite_data:
        logger.info("✅ No SQLite data found to migrate")
        return

    # Step 2: Migrate data
    logger.info("\n" + "=" * 60)
    migration_success = migrate_sqlite_to_postgres()

    if not migration_success:
        logger.error("❌ Migration failed!")
        return

    # Step 3: Verify PostgreSQL data
    logger.info("\n" + "=" * 60)
    logger.info("🔍 Verifying PostgreSQL data after migration...")

    app = create_app('development')
    with app.app_context():
        final_orders = Order.query.count()
        final_validations = ValidationResult.query.count()
        final_tours = Tour.query.count()
        orders_with_coords = Order.query.filter(
            Order.location_latitude.isnot(None),
            Order.location_longitude.isnot(None)
        ).count()

        logger.info(f"📊 Final PostgreSQL data:")
        logger.info(f"   - Orders: {final_orders}")
        logger.info(f"   - Orders with coordinates: {orders_with_coords}")
        logger.info(f"   - Validations: {final_validations}")
        logger.info(f"   - Tours: {final_tours}")

    # Step 4: Remove SQLite files (backup them)
    logger.info("\n" + "=" * 60)
    logger.info("🗑️ Backing up and removing SQLite files...")
    removed_files = remove_sqlite_files()

    if removed_files:
        logger.info(f"✅ SQLite files backed up:")
        for file in removed_files:
            logger.info(f"   - {file} -> {file}.backup")

    logger.info("\n🎉 MIGRATION COMPLETED SUCCESSFULLY!")
    logger.info("Your data is now fully in PostgreSQL and SQLite files are backed up.")

if __name__ == '__main__':
    main()