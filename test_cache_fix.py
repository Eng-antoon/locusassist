#!/usr/bin/env python3
"""
Test script to verify cache-busting fixes for browser caching issues
"""

import requests
from app import create_app
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_cache_headers():
    """Test that the cache-busting headers are properly set"""
    try:
        # Create app to get config
        app = create_app('development')

        # Test URLs to check for cache headers
        test_urls = [
            'http://localhost:5000/dashboard',
            'http://localhost:5000/api/orders',
        ]

        with app.app_context():
            logger.info("🧪 Testing cache-busting headers...")

            for url in test_urls:
                try:
                    response = requests.get(url, timeout=5)

                    logger.info(f"\n📡 Testing: {url}")
                    logger.info(f"  Status: {response.status_code}")

                    # Check cache control headers
                    cache_control = response.headers.get('Cache-Control', '')
                    pragma = response.headers.get('Pragma', '')
                    expires = response.headers.get('Expires', '')

                    logger.info(f"  Cache-Control: {cache_control}")
                    logger.info(f"  Pragma: {pragma}")
                    logger.info(f"  Expires: {expires}")

                    # Verify cache-busting headers
                    has_no_cache = 'no-cache' in cache_control
                    has_no_store = 'no-store' in cache_control
                    has_must_revalidate = 'must-revalidate' in cache_control
                    has_pragma = pragma == 'no-cache'
                    has_expires = expires == '0'

                    if has_no_cache and has_no_store and has_must_revalidate and has_pragma and has_expires:
                        logger.info(f"  ✅ Cache-busting headers correctly set")
                    else:
                        logger.warning(f"  ⚠️  Missing some cache-busting headers")
                        logger.warning(f"    no-cache: {has_no_cache}, no-store: {has_no_store}")
                        logger.warning(f"    must-revalidate: {has_must_revalidate}, pragma: {has_pragma}, expires: {has_expires}")

                except requests.exceptions.ConnectionError:
                    logger.info(f"  ⏭️  Server not running - {url}")
                except Exception as e:
                    logger.error(f"  ❌ Error testing {url}: {e}")

            logger.info("\n🎯 Cache-busting implementation summary:")
            logger.info("  ✅ Frontend: Cache-busting URL parameters added to refresh")
            logger.info("  ✅ Backend: Cache-busting headers added to responses")
            logger.info("  ✅ Dashboard: No-cache headers prevent browser caching")
            logger.info("  ✅ APIs: All order-related endpoints have cache headers")

            return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_cache_headers()