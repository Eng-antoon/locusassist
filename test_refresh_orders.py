#!/usr/bin/env python3
"""
Test the refresh orders functionality to examine location coordinates and missing data
"""

import requests
import json
import logging
from app import create_app
from app.auth import LocusAuth
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_refresh_orders_api():
    """Test the refresh orders API call and examine the location data"""
    try:
        # Your provided access token
        access_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ik4wRTNNa1l3TlVGQk1EQkZOREEzTVRVMFEwSTJSRGxCUkRFelFqa3pOVFl4TWpZMlJUUkNNUSJ9.eyJsb2N1cy1hdHRyaWJ1dGVzIjp7ImN1c3RvbVZhbHVlcyI6eyJkYXRhQ2xpZW50SWQiOiJpbGxhLWZyb250ZG9vciJ9LCJwZXJzb25uZWxJZCI6ImlsbGEtZnJvbnRkb29yL3BlcnNvbm5lbC9BbWluIn0sImlzcyI6Imh0dHBzOi8vYWNjb3VudHMubG9jdXMtZGFzaGJvYXJkLmNvbS8iLCJzdWIiOiJhdXRoMHxwZXJzb25uZWxzfGlsbGEtZnJvbnRkb29yL3BlcnNvbm5lbC9BbWluIiwiYXVkIjpbImh0dHBzOi8vYXdzLXVzLWVhc3QtMS5sb2N1cy1hcGkuY29tIiwiaHR0cHM6Ly9sb2N1cy1hd3MtdXMtZWFzdC0xLmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NTg4MzA2NTIsImV4cCI6MTc1ODg3Mzg1Miwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6IkNMMm1sYnJMZ2Z3N2RTOGFkcDV4MzE5aXVQT0pySlZlIn0.jNIJoulmMmvfbS8R0_1NvF-kXlzmWtCBxbCJTAXPU0HE3b7q7Qwr5digjW58L5a3Ny8rNjNam3YaIvzhcV-itmcCmbI1LuuCBwPjNEMJwBMAVI6asiqGm0l2buX1k5roJsh7nK3b0HpY3ZTZqxurWO8CiO6dzNcYrPqUvYYCkBOkx_VSnaSD9ABQ0PZYb28wAB-EY2puB3itNAuB3PTAbjsI90fS7A55nJ1VcmFZFx9-xsQBVtusDAQyr4tICCRyzl-0FKeNl_e0_ytlboIrHIbe-76eHVgxSJdoxwYlLXSVEOjBwPbB3oRbfELEsoB7l3cFdbY34eX_Iskh9A3hjg"

        app = create_app('development')

        with app.app_context():
            from app.config import DevelopmentConfig
            config = DevelopmentConfig()
            auth = LocusAuth(config)

            logger.info("🔄 Testing refresh orders functionality...")

            # Test the refresh orders method directly - use yesterday's date for actual data
            from datetime import datetime, timedelta
            yesterday = datetime.now() - timedelta(days=1)
            date = yesterday.strftime("%Y-%m-%d")
            logger.info(f"📅 Testing refresh for date: {date}")

            # Call the smart merge refresh method (this is what gets called on refresh)
            orders_data = auth.refresh_orders_smart_merge(
                access_token=access_token,
                client_id="illa-frontdoor",
                team_id="101",
                date=date,
                fetch_all=True,
                order_statuses=None
            )

            if not orders_data or not orders_data.get('orders'):
                logger.error("❌ No orders data returned from refresh")
                return False

            orders = orders_data.get('orders', [])
            logger.info(f"📦 Found {len(orders)} orders from refresh")

            # Analyze the first few orders for location coordinate data
            logger.info("\n🗺️ LOCATION COORDINATES ANALYSIS")
            logger.info("=" * 50)

            sample_orders = orders[:5]  # Check first 5 orders
            location_coords_found = 0
            location_coords_missing = 0

            for i, order in enumerate(sample_orders, 1):
                logger.info(f"\n📍 Order {i}: {order.get('id')}")
                logger.info(f"   Status: {order.get('orderStatus')}")

                # Check location structure in API data
                location = order.get('location', {})
                if location:
                    logger.info(f"   Location name: {location.get('name', 'N/A')}")

                    # Check address
                    address = location.get('address', {})
                    if address:
                        formatted_address = address.get('formattedAddress', 'N/A')
                        city = address.get('city', 'N/A')
                        country = address.get('countryCode', 'N/A')
                        logger.info(f"   Address: {formatted_address}")
                        logger.info(f"   City: {city}")
                        logger.info(f"   Country: {country}")

                    # ⭐ CHECK FOR COORDINATES - THIS IS WHAT WE'RE LOOKING FOR
                    latLng = location.get('latLng', {})
                    if latLng and isinstance(latLng, dict):
                        lat = latLng.get('lat') or latLng.get('latitude')
                        lng = latLng.get('lng') or latLng.get('longitude')

                        if lat and lng:
                            logger.info(f"   ✅ COORDINATES FOUND: lat={lat}, lng={lng}")
                            location_coords_found += 1
                        else:
                            logger.info(f"   ❌ COORDINATES MISSING (latLng present but empty)")
                            logger.info(f"       latLng keys: {list(latLng.keys())}")
                            location_coords_missing += 1
                    else:
                        logger.info(f"   ❌ NO COORDINATES (no latLng field)")
                        location_coords_missing += 1

                    # Check all keys in location object
                    logger.info(f"   Location keys: {list(location.keys())}")
                else:
                    logger.info(f"   ❌ NO LOCATION DATA")
                    location_coords_missing += 1

            logger.info(f"\n📊 COORDINATES SUMMARY:")
            logger.info(f"   Orders with coordinates: {location_coords_found}/{len(sample_orders)}")
            logger.info(f"   Orders missing coordinates: {location_coords_missing}/{len(sample_orders)}")

            # Now check what's stored in the database vs what's available in API
            logger.info(f"\n💾 DATABASE vs API COMPARISON")
            logger.info("=" * 50)

            from models import Order

            for i, order in enumerate(sample_orders, 1):
                order_id = order.get('id')
                logger.info(f"\n🔍 Order {i}: {order_id}")

                # Check what's in database
                db_order = Order.query.filter_by(id=order_id).first()
                if db_order:
                    logger.info(f"   Database location fields:")
                    logger.info(f"     - location_name: {db_order.location_name}")
                    logger.info(f"     - location_address: {db_order.location_address}")
                    logger.info(f"     - location_city: {db_order.location_city}")
                    logger.info(f"     - location_country_code: {db_order.location_country_code}")
                    logger.info(f"   ❌ NO COORDINATE FIELDS IN DATABASE")
                else:
                    logger.info(f"   ❌ Order not found in database")

                # Check what's available in API
                location = order.get('location', {})
                if location:
                    latLng = location.get('latLng', {})
                    if latLng:
                        lat = latLng.get('lat') or latLng.get('latitude')
                        lng = latLng.get('lng') or latLng.get('longitude')
                        logger.info(f"   API location coordinates available:")
                        logger.info(f"     - lat: {lat}")
                        logger.info(f"     - lng: {lng}")
                    else:
                        logger.info(f"   ❌ No coordinates in API response")

            # Check all fields available in API vs stored in database
            logger.info(f"\n📋 MISSING FIELDS ANALYSIS")
            logger.info("=" * 50)

            if orders:
                sample_order = orders[0]
                logger.info(f"🔍 Analyzing order: {sample_order.get('id')}")

                # Flatten the order structure to see all available fields
                def flatten_dict(d, parent_key='', sep='.'):
                    items = []
                    if isinstance(d, dict):
                        for k, v in d.items():
                            new_key = f"{parent_key}{sep}{k}" if parent_key else k
                            if isinstance(v, dict):
                                items.extend(flatten_dict(v, new_key, sep=sep).items())
                            elif isinstance(v, list) and v and isinstance(v[0], dict):
                                # For lists of dicts, just show the structure of first item
                                items.append((f"{new_key}[]", f"List of {len(v)} items"))
                                if v:
                                    items.extend(flatten_dict(v[0], f"{new_key}[0]", sep=sep).items())
                            else:
                                items.append((new_key, v))
                    return dict(items)

                flattened = flatten_dict(sample_order)

                # Show location-related fields
                location_fields = {k: v for k, v in flattened.items() if 'location' in k.lower() or 'address' in k.lower() or 'lat' in k.lower() or 'lng' in k.lower() or 'coord' in k.lower()}

                logger.info(f"🗺️ Location-related fields in API response:")
                for field, value in location_fields.items():
                    logger.info(f"   {field}: {value}")

                # Show all top-level fields
                logger.info(f"\n📄 All top-level fields in API response:")
                top_level_fields = list(sample_order.keys())
                for field in sorted(top_level_fields):
                    field_type = type(sample_order.get(field)).__name__
                    logger.info(f"   {field}: {field_type}")

            logger.info(f"\n✅ Refresh orders analysis completed!")
            return True

    except Exception as e:
        logger.error(f"❌ Error during refresh orders test: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("🔄 REFRESH ORDERS API ANALYSIS")
    print("=" * 60)

    success = test_refresh_orders_api()
    if success:
        print("\n🎉 Refresh orders analysis completed!")
    else:
        print("\n❌ Refresh orders analysis failed!")