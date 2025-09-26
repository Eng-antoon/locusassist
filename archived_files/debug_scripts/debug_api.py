#!/usr/bin/env python3
"""
Debug script to test API order fetching
"""

import sys
import os
import logging
import json
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.auth import LocusAuth
from app.config import Config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_api_connection():
    """Test API connection and order fetching"""

    print("🔧 Debug: Testing API Order Fetching")
    print("=" * 50)

    try:
        # Initialize components
        config = Config()
        locus_auth = LocusAuth(config)

        print(f"🌐 API URL: {locus_auth.api_url}")
        print(f"🔑 Bearer Token: {config.BEARER_TOKEN[:20]}..." if config.BEARER_TOKEN else "❌ No Bearer Token")

        # Test different scenarios
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        test_cases = [
            {
                "name": "All Orders (Today)",
                "params": {
                    "date": today,
                    "fetch_all": True,
                    "order_statuses": None
                }
            },
            {
                "name": "All Orders (Yesterday)",
                "params": {
                    "date": yesterday,
                    "fetch_all": True,
                    "order_statuses": None
                }
            },
            {
                "name": "Completed Orders Only (Today)",
                "params": {
                    "date": today,
                    "fetch_all": True,
                    "order_statuses": ["COMPLETED"]
                }
            },
            {
                "name": "Completed Orders Only (Yesterday)",
                "params": {
                    "date": yesterday,
                    "fetch_all": True,
                    "order_statuses": ["COMPLETED"]
                }
            }
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📋 Test {i}: {test_case['name']}")
            print("-" * 30)

            try:
                # Disable caching for debug - always force fresh fetch
                test_params = test_case['params'].copy()
                test_params['force_refresh'] = True

                orders_data = locus_auth.get_orders(
                    config.BEARER_TOKEN,
                    'illa-frontdoor',
                    **test_params
                )

                if orders_data:
                    total_count = orders_data.get('totalCount', 0)
                    orders_count = len(orders_data.get('orders', []))
                    pages_fetched = orders_data.get('pagesFetched', 'N/A')
                    status_totals = orders_data.get('statusTotals', {})

                    print(f"✅ Success!")
                    print(f"   📊 Total Count: {total_count}")
                    print(f"   📄 Orders Retrieved: {orders_count}")
                    print(f"   📑 Pages Fetched: {pages_fetched}")

                    if status_totals:
                        print(f"   🏷️  Status Breakdown:")
                        for status, count in status_totals.items():
                            print(f"      {status}: {count}")

                    if orders_count > 0:
                        sample_order = orders_data['orders'][0]
                        print(f"   🔍 Sample Order ID: {sample_order.get('id', 'N/A')}")
                        print(f"   🔍 Sample Order Status: {sample_order.get('orderStatus', 'N/A')}")

                else:
                    print("❌ No data returned")

            except Exception as e:
                print(f"❌ Error: {str(e)}")
                logger.exception(f"Error in test case {i}")

        print(f"\n🎯 Debug completed!")
        return True

    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        logger.exception("Fatal error in API test")
        return False

if __name__ == "__main__":
    success = test_api_connection()
    if success:
        print("✅ API debug test completed!")
        sys.exit(0)
    else:
        print("❌ API debug test failed!")
        sys.exit(1)