#!/usr/bin/env python3
"""
Test script to verify pagination fix for date ranges
"""

from app import create_app
from app.config import DevelopmentConfig
from app.auth import LocusAuth
from app import filter_service
from models import db, Order
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_pagination_fix():
    """Test the pagination fix for date ranges"""
    try:
        app = create_app('development')
        config = DevelopmentConfig()

        with app.app_context():
            logger.info("🧪 Testing pagination fix for date ranges...")

            # Test dates
            date_from = '2025-09-23'
            date_to = '2025-09-24'

            # First refresh both dates to ensure we have data
            auth = LocusAuth(config)

            logger.info(f"📥 Refreshing data for date range {date_from} to {date_to}...")

            # Use the refresh endpoint logic
            result = filter_service.refresh_date_range_data(
                date_from, date_to,
                {'date_from': date_from, 'date_to': date_to, 'order_status': 'all'},
                force_refresh=False, config=config
            )

            if result.get('success'):
                logger.info(f"✅ Refresh successful: {result['total_orders_refreshed']} orders refreshed")
            else:
                logger.error(f"❌ Refresh failed: {result.get('error', 'Unknown error')}")
                return False

            # Now test the dashboard filtering logic
            logger.info("🔍 Testing dashboard filtering with date range...")

            # Test old pagination (50 per page)
            filter_data_old = {
                'date_from': date_from,
                'date_to': date_to,
                'order_status': None,
                'page': 1,
                'per_page': 50
            }

            result_old = filter_service.apply_filters(filter_data_old)

            # Test new pagination (500 per page for date ranges)
            filter_data_new = {
                'date_from': date_from,
                'date_to': date_to,
                'order_status': None,
                'page': 1,
                'per_page': 500
            }

            result_new = filter_service.apply_filters(filter_data_new)

            logger.info("📊 RESULTS:")
            logger.info(f"  Old pagination (50/page): {len(result_old.get('orders', []))} orders shown, {result_old.get('total_count', 0)} total")
            logger.info(f"  New pagination (500/page): {len(result_new.get('orders', []))} orders shown, {result_new.get('total_count', 0)} total")

            # Check date distribution in results
            if result_old.get('orders'):
                old_dates = {}
                for order in result_old['orders']:
                    date = order.get('date', 'unknown')
                    old_dates[date] = old_dates.get(date, 0) + 1
                logger.info(f"  Old - Dates shown: {old_dates}")

            if result_new.get('orders'):
                new_dates = {}
                for order in result_new['orders']:
                    date = order.get('date', 'unknown')
                    new_dates[date] = new_dates.get(date, 0) + 1
                logger.info(f"  New - Dates shown: {new_dates}")

            # Check status totals
            logger.info(f"  Status totals (old): {result_old.get('status_totals', {})}")
            logger.info(f"  Status totals (new): {result_new.get('status_totals', {})}")

            return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_pagination_fix()