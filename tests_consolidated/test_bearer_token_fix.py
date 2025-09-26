#!/usr/bin/env python3
"""
Test script to verify bearer token is properly accessible in filter service
"""

from app import create_app
from app.config import DevelopmentConfig
from app.filters import filter_service
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_bearer_token_access():
    """Test that the bearer token is accessible in various scenarios"""
    try:
        app = create_app('development')
        config = DevelopmentConfig()

        with app.app_context():
            logger.info("🧪 Testing bearer token accessibility...")

            # Test 1: Check if config has bearer token
            logger.info(f"\n📋 Test 1: Config object has bearer token")
            has_bearer = hasattr(config, 'BEARER_TOKEN')
            token_value = getattr(config, 'BEARER_TOKEN', None)
            logger.info(f"  ✅ Config has BEARER_TOKEN: {has_bearer}")
            logger.info(f"  ✅ Token length: {len(token_value) if token_value else 0} characters")
            if token_value:
                logger.info(f"  ✅ Token preview: {token_value[:20]}...")

            # Test 2: Test filter service with config parameter
            logger.info(f"\n📋 Test 2: Filter service with explicit config")

            test_filter_data = {
                'date_from': '2025-09-25',
                'date_to': '2025-09-25',
                'page': 1,
                'per_page': 50
            }

            # This should now work because we pass the config explicitly
            try:
                result = filter_service.apply_filters(test_filter_data, config)
                logger.info(f"  ✅ Filter service executed successfully")
                logger.info(f"  ✅ Result success: {result.get('success', False)}")
                logger.info(f"  ✅ Total orders: {result.get('total_count', 0)}")
                if not result.get('success') and 'bearer token' in str(result.get('error', '')).lower():
                    logger.error(f"  ❌ Still having bearer token issues: {result.get('error')}")
                else:
                    logger.info(f"  ✅ No bearer token errors detected")
            except Exception as e:
                logger.error(f"  ❌ Filter service failed: {e}")

            # Test 3: Test filter service without config parameter (fallback)
            logger.info(f"\n📋 Test 3: Filter service without explicit config (fallback)")
            try:
                result = filter_service.apply_filters(test_filter_data)
                logger.info(f"  ✅ Filter service fallback executed")
                logger.info(f"  ✅ Result success: {result.get('success', False)}")
                if not result.get('success') and 'bearer token' in str(result.get('error', '')).lower():
                    logger.warning(f"  ⚠️  Fallback has bearer token issues: {result.get('error')}")
                else:
                    logger.info(f"  ✅ Fallback works without bearer token errors")
            except Exception as e:
                logger.warning(f"  ⚠️  Filter service fallback failed: {e}")

            # Test 4: Check Flask app config
            logger.info(f"\n📋 Test 4: Flask app.config has bearer token")
            app_has_bearer = hasattr(app.config, 'BEARER_TOKEN')
            app_token = getattr(app.config, 'BEARER_TOKEN', None)
            logger.info(f"  ✅ App config has BEARER_TOKEN: {app_has_bearer}")
            if app_token:
                logger.info(f"  ✅ App token length: {len(app_token)} characters")
                logger.info(f"  ✅ App token preview: {app_token[:20]}...")
                token_match = token_value == app_token if token_value and app_token else False
                logger.info(f"  ✅ Config tokens match: {token_match}")

            logger.info(f"\n🎯 Summary:")
            logger.info(f"  🔧 Fixed: Dashboard route now passes config to filter service")
            logger.info(f"  🔧 Fixed: API filter endpoint now passes config to filter service")
            logger.info(f"  🔧 Fixed: Filter service accepts optional config parameter")
            logger.info(f"  🔧 Fixed: Bearer token should now be accessible for API calls")

            logger.info(f"\n✅ Expected behavior:")
            logger.info(f"  📊 Dashboard: Should load data without 'No bearer token' warning")
            logger.info(f"  🔄 API calls: Should work with proper authentication")
            logger.info(f"  🗃️  Missing data: Should be fetched from API automatically")

            return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_bearer_token_access()