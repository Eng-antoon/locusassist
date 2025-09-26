from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import requests
import json
from datetime import datetime, timedelta, date
import logging
import os
import base64
from PIL import Image
import io
from demo_data import demo_orders_data
from models import db, Order, OrderLineItem, ValidationResult, DashboardStats
import time
import difflib
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import asyncio

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Global rate limiting for Google API calls
# Google Gemini API has limits: 15 requests per minute for free tier, 1000 for paid
# We'll use a conservative approach: max 10 concurrent API calls + small delays
api_rate_limiter = threading.Semaphore(10)  # Max 10 concurrent API calls
api_call_times = []  # Track API call timing for rate limiting
api_timing_lock = threading.Lock()

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:@localhost:5432/locus_assistant')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

def rate_limit_api_call():
    """Rate limit Google API calls to respect billing limits"""
    with api_timing_lock:
        current_time = time.time()
        # Remove API calls older than 60 seconds
        global api_call_times
        api_call_times = [t for t in api_call_times if current_time - t < 60]

        # If we've made more than 12 calls in the last minute, add delay
        if len(api_call_times) >= 12:
            sleep_time = 60 - (current_time - api_call_times[0]) + 1
            if sleep_time > 0:
                logger.info(f"Rate limiting: sleeping {sleep_time:.1f} seconds to respect API limits")
                time.sleep(sleep_time)

        # Record this API call
        api_call_times.append(current_time)

def create_tables():
    """Create database tables if they don't exist"""
    with app.app_context():
        db.create_all()
        logger.info("Database tables created successfully")

def init_db_connection():
    """Initialize database connection and create tables"""
    try:
        create_tables()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

# Bearer token provided by user
BEARER_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ik4wRTNNa1l3TlVGQk1EQkZOREEzTVRVMFEwSTJSRGxCUkRFelFqa3pOVFl4TWpZMlJUUkNNUSJ9.eyJsb2N1cy1hdHRyaWJ1dGVzIjp7ImN1c3RvbVZhbHVlcyI6eyJkYXRhQ2xpZW50SWQiOiJpbGxhLWZyb250ZG9vciJ9LCJwZXJzb25uZWxJZCI6ImlsbGEtZnJvbnRkb29yL3BlcnNvbm5lbC9BbWluIn0sImlzcyI6Imh0dHBzOi8vYWNjb3VudHMubG9jdXMtZGFzaGJvYXJkLmNvbS8iLCJzdWIiOiJhdXRoMHxwZXJzb25uZWxzfGlsbGEtZnJvbnRkb29yL3BlcnNvbm5lbC9BbWluIiwiYXVkIjpbImh0dHBzOi8vYXdzLXVzLWVhc3QtMS5sb2N1cy1hcGkuY29tIiwiaHR0cHM6Ly9sb2N1cy1hd3MtdXMtZWFzdC0xLmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NTg4NzQxMjIsImV4cCI6MTc1ODkxNzMyMiwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6IkNMMm1sYnJMZ2Z3N2RTOGFkcDV4MzE5aXVQT0pySlZlIn0.lZGb9MynHmGDDUsPTT6PMfCosS3Dkzwd6vBEsneW3pn_w4rJjkby-jMSo8ljBrMhc9AypY43bX8Kfs86FZ2j3NNo_lUi9epSur1GyZf11S8GiH_lXlcHk-Kf-a47vimzo-ccmMJ-15UMYK9ekbWRUeg1-2Dbm-ENXkgIT-T58qh9FN7qf7zqOgPOFyLwBdCQLFF7su3Opzm7TTW1VLrt0_CBfczq_bcJ9sdl_iTYCTXlIBIwdeoqTwYXZoW7O9Ndprl9sp__h3_6QLHXnrdtEw8H3vcpeDc-Cke4iZZNvDdq8f3gIwEQVLyEAkrT_hpZfYFYDnc8xy0SQnQhiZ1mJw"

# Google AI Studio Configuration
# To set your API key, create a file called .env in this directory with:
# GOOGLE_AI_API_KEY=your_actual_api_key_here
# Or set it as an environment variable: export GOOGLE_AI_API_KEY=your_key
GOOGLE_AI_API_KEY = "AIzaSyAj4Y69sbfXSNKHHSu0YOot2R9kLOmFhQI"

if not GOOGLE_AI_API_KEY:
    logger.warning("Google AI API key not found. Please set GOOGLE_AI_API_KEY environment variable or add it to .env file")

GOOGLE_AI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LocusAuth:
    def __init__(self):
        self.base_url = "https://dash.locus-api.com"
        self.auth_url = "https://accounts.locus-dashboard.com"
        self.api_url = "https://oms.locus-api.com"

    def get_personnel_info(self, username):
        """Get minimal personnel information"""
        try:
            url = f"{self.base_url}/v1/minimal-personnel?username={username}"
            headers = {
                "accept": "application/json",
                "accept-language": "en-US,en;q=0.9",
            }

            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting personnel info: {e}")
            return None

    def authenticate(self, username, password, personnel_data):
        """Authenticate with username and password"""
        try:
            url = f"{self.auth_url}/usernamepassword/login"
            headers = {
                "accept": "*/*",
                "content-type": "application/json",
            }

            payload = {
                "client_id": "CL2mlbrLgfw7dS8adp5x319iuPOJrJVe",
                "redirect_uri": "https://illa-frontdoor.locus-dashboard.com/#/login/callback",
                "tenant": "locus-aws-us-east-1",
                "response_type": "token",
                "scope": "openid profile email",
                "audience": "https://aws-us-east-1.locus-api.com",
                "username": personnel_data['passwordAuthDetails']['identifier'],
                "password": password,
                "connection": personnel_data['passwordAuthDetails']['connectionName']
            }

            response = requests.post(url, headers=headers, json=payload)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error during authentication: {e}")
            return False

    def get_access_token(self, auth_code=None):
        """Get access token"""
        try:
            url = f"{self.auth_url}/oauth/token"
            headers = {
                "accept": "*/*",
                "content-type": "application/json",
            }

            payload = {
                "client_id": "CL2mlbrLgfw7dS8adp5x319iuPOJrJVe",
                "code_verifier": "2b8EepRuY0LWdMgV~zzqBGZi4C6Zqx41iaC1N-Y1xQl",
                "grant_type": "authorization_code",
                "code": auth_code or "zuXiEANHkI_wTBtjS8fJfMgU_FZAAKegi14w6eem4cuMb",
                "redirect_uri": "https://illa-frontdoor.locus-dashboard.com/#/login/callback"
            }

            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
            return None

    def cache_orders_to_database(self, orders_data, client_id, date_str):
        """Cache orders data to database"""
        try:
            order_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            if not orders_data or not orders_data.get('orders'):
                logger.info("No orders data to cache")
                return

            orders = orders_data.get('orders', [])
            logger.info(f"Caching {len(orders)} orders to database for date {date_str}")

            for order_data in orders:
                try:
                    order_id = order_data.get('id')
                    if not order_id:
                        continue

                    # Check if order already exists
                    existing_order = Order.query.filter_by(id=order_id, date=order_date).first()
                    if existing_order:
                        # Update existing order
                        existing_order.order_status = order_data.get('orderStatus', '')
                        existing_order.raw_data = json.dumps(order_data)
                        existing_order.updated_at = datetime.now()
                    else:
                        # Create new order
                        order = Order(
                            id=order_id,
                            client_id=client_id,
                            date=order_date,
                            order_status=order_data.get('orderStatus', ''),
                            raw_data=json.dumps(order_data)
                        )

                        # Extract location data
                        location = order_data.get('location', {})
                        if location:
                            order.location_name = location.get('name')
                            address = location.get('address', {})
                            order.location_address = address.get('formattedAddress')
                            order.location_city = address.get('city')
                            order.location_country_code = address.get('countryCode')

                        # Extract tour/delivery data
                        tour_detail = order_data.get('orderMetadata', {}).get('tourDetail', {})
                        if tour_detail:
                            order.rider_name = tour_detail.get('riderName')
                            order.vehicle_registration = tour_detail.get('vehicleRegistrationNumber')

                        # Extract completion data
                        completion_time = order_data.get('orderMetadata', {}).get('homebaseCompleteOn')
                        if completion_time:
                            try:
                                order.completed_on = datetime.fromisoformat(completion_time.replace('Z', '+00:00'))
                            except:
                                pass

                        db.session.add(order)

                        # Cache line items
                        line_items = order_data.get('orderMetadata', {}).get('lineItems', [])
                        for item_data in line_items:
                            line_item = OrderLineItem(
                                order_id=order_id,
                                sku_id=item_data.get('id', ''),
                                name=item_data.get('name', ''),
                                quantity=item_data.get('quantity', 0),
                                quantity_unit=item_data.get('quantityUnit', ''),
                                transacted_quantity=item_data.get('transactionStatus', {}).get('transactedQuantity', 0),
                                transaction_status=item_data.get('transactionStatus', {}).get('status', '')
                            )
                            db.session.add(line_item)

                except Exception as e:
                    logger.error(f"Error caching order {order_data.get('id', 'unknown')}: {e}")
                    continue

            db.session.commit()
            logger.info(f"Successfully cached {len(orders)} orders to database")

        except Exception as e:
            logger.error(f"Error caching orders to database: {e}")
            db.session.rollback()

    def get_orders_from_database(self, client_id, date_str):
        """Get cached orders from database"""
        try:
            order_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            orders = Order.query.filter_by(client_id=client_id, date=order_date).all()

            if not orders:
                return None

            logger.info(f"Found {len(orders)} cached orders for date {date_str}")

            # Convert to API format
            orders_data = []
            for order in orders:
                try:
                    order_dict = json.loads(order.raw_data) if order.raw_data else {}
                    orders_data.append(order_dict)
                except:
                    logger.error(f"Error parsing cached order data for {order.id}")
                    continue

            return {
                "orders": orders_data,
                "totalCount": len(orders_data),
                "cached": True
            }

        except Exception as e:
            logger.error(f"Error getting cached orders: {e}")
            return None

    def get_orders(self, access_token, client_id="illa-frontdoor", team_id="101", date=None, fetch_all=False):
        """Fetch orders data - can fetch all pages or single page. Uses database caching."""
        try:
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")

            # First, try to get from database cache
            cached_orders = self.get_orders_from_database(client_id, date)
            if cached_orders:
                logger.info(f"Returning {len(cached_orders['orders'])} cached orders for {date}")
                return cached_orders

            # If no cached data, fetch from API
            logger.info(f"No cached orders found for {date}. Fetching from API...")
            url = f"{self.api_url}/v1/client/{client_id}/order-search?include=LOCATION%2CHOMEBASE&countsOnly=false"
            headers = {
                "accept": "application/json",
                "authorization": f"Bearer {access_token}",
                "content-type": "application/json",
                "l-custom-user-agent": "cerebro",
            }

            if not date:
                date = datetime.now().strftime("%Y-%m-%d")

            next_date = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

            def get_page(page_num):
                payload = {
                    "page": page_num,
                    "size": 50,
                    "sortingInfo": [],
                    "filters": [
                        {
                            "name": "orderStatus",
                            "operation": "EQUALS",
                            "value": None,
                            "values": ["COMPLETED"],
                            "allowEmptyOrNull": False,
                            "caseSensitive": False
                        },
                        {
                            "name": "teamId",
                            "operation": "EQUALS",
                            "value": None,
                            "values": [team_id],
                            "allowEmptyOrNull": False,
                            "caseSensitive": True
                        },
                        {
                            "name": "date",
                            "operation": "GREATER_THAN_OR_EQUAL_TO",
                            "value": date,
                            "values": [],
                            "allowEmptyOrNull": False,
                            "caseSensitive": False
                        },
                        {
                            "name": "date",
                            "operation": "LESSER_THAN",
                            "value": next_date,
                            "values": [],
                            "allowEmptyOrNull": False,
                            "caseSensitive": False
                        }
                    ],
                    "complexFilters": None
                }

                response = requests.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    return response.json()
                return None

            if not fetch_all:
                # Return single page
                page_data = get_page(1)
                if page_data:
                    # Cache the fetched data
                    self.cache_orders_to_database(page_data, client_id, date)
                return page_data

            # Fetch all pages
            all_orders = []
            page = 1
            total_fetched = 0

            logger.info(f"Starting to fetch all orders for date: {date}")

            while True:
                logger.info(f"Fetching page {page}...")
                page_data = get_page(page)

                if not page_data or not page_data.get('orders'):
                    logger.info(f"No more orders found at page {page}")
                    break

                orders_in_page = len(page_data['orders'])
                all_orders.extend(page_data['orders'])
                total_fetched += orders_in_page

                logger.info(f"Page {page}: {orders_in_page} orders (Total: {total_fetched})")

                # If we got less than 50 orders, we've reached the end
                if orders_in_page < 50:
                    logger.info(f"Reached end of data at page {page}")
                    break

                page += 1

                # Safety limit to prevent infinite loops
                if page > 100:
                    logger.warning("Reached page limit of 100, stopping")
                    break

            logger.info(f"Total orders fetched: {total_fetched}")

            # Create response data
            response_data = {
                "orders": all_orders,
                "totalCount": total_fetched,
                "pagesFetched": page - 1
            }

            # Cache the fetched data
            if all_orders:
                self.cache_orders_to_database(response_data, client_id, date)

            return response_data

        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return None

    def get_order_detail(self, access_token, client_id, order_id):
        """Fetch detailed order information by order ID"""
        try:
            url = f"{self.api_url}/v1/client/{client_id}/order/{order_id}?include=HOMEBASE%2CLOCATION%2CSKU"
            headers = {
                "accept": "application/json",
                "authorization": f"Bearer {access_token}",
                "l-custom-user-agent": "cerebro",
            }

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error fetching order detail {order_id}: HTTP {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting order detail {order_id}: {e}")
            return None

class GS1Validator:
    def __init__(self):
        pass

    def get_product_info(self, gtin):
        """Fetch product information from GS1 Verified database"""
        try:
            logger.info(f"Fetching GS1 product info for GTIN: {gtin}")

            # GS1 Verified API endpoint
            url = "https://www.gs1.org/services/verified-by-gs1/results"

            headers = {
                "accept": "application/json, text/javascript, */*; q=0.01",
                "accept-language": "en-US,en;q=0.9",
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Linux"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "x-requested-with": "XMLHttpRequest"
            }

            # Prepare form data for GTIN search
            form_data = {
                "search_type": "gtin",
                "gtin": gtin,
                "gln": "",
                "country": "",
                "street_address": "",
                "postal_code": "",
                "city": "",
                "company_name": "",
                "other_key_type": "",
                "other_key": "",
                "_triggering_element_name": "gtin_submit",
                "_triggering_element_value": "Search",
                "_drupal_ajax": "1"
            }

            # Make the request
            response = requests.post(url, headers=headers, data=form_data, timeout=10)

            if response.status_code == 200:
                result = response.json()

                # Parse the response to extract product information
                product_info = self.parse_gs1_response(result, gtin)
                return product_info
            else:
                logger.error(f"GS1 API error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error fetching GS1 data for GTIN {gtin}: {e}")
            return None

    def parse_gs1_response(self, response_data, gtin):
        """Parse GS1 API response to extract product information"""
        try:
            # Look for the HTML content in the response
            for item in response_data:
                if item.get('command') == 'insert' and 'data' in item:
                    html_content = item['data']

                    # Extract product information using regex or HTML parsing
                    import re

                    # Extract product name
                    product_name_match = re.search(r'<h3[^>]*>([^<]+)</h3>', html_content)
                    product_name = product_name_match.group(1).strip() if product_name_match else None

                    # Extract brand names (both Arabic and English)
                    brand_names = {}
                    # English brand name
                    brand_en_match = re.search(r'Brand name.*?<strong[^>]*>\(en\)\s*([^<]+)</strong>', html_content, re.DOTALL)
                    if brand_en_match:
                        brand_names['english'] = brand_en_match.group(1).strip()

                    # Arabic brand name
                    brand_ar_match = re.search(r'Brand name.*?<strong[^>]*>\(ar\)\s*([^<]+)</strong>', html_content, re.DOTALL)
                    if brand_ar_match:
                        brand_names['arabic'] = brand_ar_match.group(1).strip()

                    # Extract product descriptions (both languages)
                    product_names = {}
                    # English product description
                    product_en_match = re.search(r'Product description.*?<strong[^>]*>\(en\)\s*([^<]+)</strong>', html_content, re.DOTALL)
                    if product_en_match:
                        product_names['english'] = product_en_match.group(1).strip()

                    # Arabic product description
                    product_ar_match = re.search(r'Product description.*?<strong[^>]*>\(ar\)\s*([^<]+)</strong>', html_content, re.DOTALL)
                    if product_ar_match:
                        product_names['arabic'] = product_ar_match.group(1).strip()

                    # If no bilingual match, try single product name
                    if not product_names and product_name:
                        product_names['primary'] = product_name

                    # Extract company name
                    company_match = re.search(r'registered to.*?<strong[^>]*>([^<]+)</strong>', html_content)
                    company_name = company_match.group(1).strip() if company_match else None

                    # Extract product category
                    category_match = re.search(r'Global product category.*?<strong[^>]*>([^<]+)</strong>', html_content)
                    category = category_match.group(1).strip() if category_match else None

                    # Extract net content
                    content_match = re.search(r'Net content.*?<strong[^>]*>([^<]+)</strong>', html_content)
                    net_content = content_match.group(1).strip() if content_match else None

                    if product_names or brand_names:
                        return {
                            'gtin': gtin,
                            'product_names': product_names,
                            'brand_names': brand_names,
                            'product_name': product_names.get('english') or product_names.get('primary') or '',  # For backward compatibility
                            'brand_name': brand_names.get('english') or '',  # For backward compatibility
                            'company_name': company_name,
                            'category': category,
                            'net_content': net_content,
                            'verified': True
                        }

            return None

        except Exception as e:
            logger.error(f"Error parsing GS1 response: {e}")
            return None

class GoogleAIValidator:
    def __init__(self):
        self.api_key = GOOGLE_AI_API_KEY
        self.api_url = GOOGLE_AI_API_URL
        self.gs1_validator = GS1Validator()

        # UoM conversion mappings
        self.uom_conversions = {
            'box': ['boxes', 'carton', 'cartons', 'case', 'cases'],
            'unit': ['units', 'piece', 'pieces', 'pcs', 'pc'],
            'kg': ['kilogram', 'kilograms', 'kilo', 'kilos'],
            'g': ['gram', 'grams', 'gm'],
            'l': ['liter', 'liters', 'litre', 'litres'],
            'ml': ['milliliter', 'milliliters', 'millilitre', 'millilitres']
        }

        # Common package multipliers
        self.package_patterns = {
            r'\((\d+)\+(\d+)\)\*(\d+)': lambda m: (int(m[1]) + int(m[2])) * int(m[3]),  # (5+1)*4
            r'(\d+)\*(\d+)': lambda m: int(m[1]) * int(m[2]),  # 2*10
            r'(\d+)x(\d+)': lambda m: int(m[1]) * int(m[2]),  # 6x12
        }

    def normalize_unit(self, unit_str):
        """Normalize unit of measurement to standard form"""
        if not unit_str:
            return 'unit'

        unit_lower = unit_str.lower().strip()

        for standard_unit, variations in self.uom_conversions.items():
            if unit_lower == standard_unit or unit_lower in variations:
                return standard_unit

        return unit_lower

    def parse_package_quantity(self, quantity_str):
        """Parse package configuration strings like (5+1)*4 to calculate total quantity"""
        import re

        if not quantity_str:
            return None, None

        quantity_str = str(quantity_str).strip()

        # Try to extract just the number first
        number_match = re.search(r'(\d+(?:\.\d+)?)', quantity_str)
        base_quantity = float(number_match.group(1)) if number_match else 0

        # Try package patterns
        for pattern, calculator in self.package_patterns.items():
            match = re.search(pattern, quantity_str)
            if match:
                calculated_qty = calculator(match)
                logger.info(f"Parsed package '{quantity_str}' -> {calculated_qty} units")
                return calculated_qty, 'calculated'

        return base_quantity, 'direct'

    def convert_quantity_units(self, from_qty, from_unit, to_unit, product_context=None):
        """Convert quantities between different units of measurement"""
        try:
            from_unit_norm = self.normalize_unit(from_unit)
            to_unit_norm = self.normalize_unit(to_unit)

            if from_unit_norm == to_unit_norm:
                return from_qty, 1.0  # Same unit, no conversion needed

            # Handle box to unit conversions (common case)
            if from_unit_norm == 'box' and to_unit_norm == 'unit':
                # Try to infer items per box from product context or use common ratios
                if product_context:
                    # Look for patterns in product name/sku that might indicate pack size
                    import re
                    pack_matches = re.findall(r'(\d+)(?:x|X|\*)(\d+)', str(product_context))
                    if pack_matches:
                        pack_size = int(pack_matches[0][0]) * int(pack_matches[0][1])
                        return from_qty * pack_size, pack_size

                # Default assumptions for common products
                default_multiplier = 12  # Assume 12 units per box as common
                logger.warning(f"Using default box->unit conversion: 1 box = {default_multiplier} units")
                return from_qty * default_multiplier, default_multiplier

            elif from_unit_norm == 'unit' and to_unit_norm == 'box':
                # Reverse conversion
                default_divisor = 12
                return from_qty / default_divisor, 1/default_divisor

            # Weight conversions
            elif from_unit_norm == 'kg' and to_unit_norm == 'g':
                return from_qty * 1000, 1000
            elif from_unit_norm == 'g' and to_unit_norm == 'kg':
                return from_qty / 1000, 1/1000

            # Volume conversions
            elif from_unit_norm == 'l' and to_unit_norm == 'ml':
                return from_qty * 1000, 1000
            elif from_unit_norm == 'ml' and to_unit_norm == 'l':
                return from_qty / 1000, 1/1000

            # If no conversion available, return original with note
            logger.warning(f"No conversion available from {from_unit} to {to_unit}")
            return from_qty, None

        except Exception as e:
            logger.error(f"Error converting {from_qty} {from_unit} to {to_unit}: {e}")
            return from_qty, None

    def validate_quantities_with_uom(self, validation_data, order_items):
        """Enhanced quantity validation with UoM conversion support"""
        try:
            logger.info("Starting enhanced quantity validation with UoM support")

            extracted_items = validation_data.get('extracted_items', [])
            enhanced_discrepancies = list(validation_data.get('discrepancies', []))
            conversions_attempted = 0
            successful_conversions = 0

            for extracted_item in extracted_items:
                matched_sku = extracted_item.get('matched_order_sku')
                if not matched_sku:
                    continue

                # Find corresponding order item
                order_item = next((item for item in order_items if item['sku_id'] == matched_sku), None)
                if not order_item:
                    continue

                extracted_qty = extracted_item.get('extracted_quantity', 0)
                extracted_unit = extracted_item.get('extracted_unit', 'unit')
                order_qty = order_item.get('quantity', 0)
                order_unit = order_item.get('unit', 'unit')

                # Parse package configurations if present
                package_config = extracted_item.get('package_config')
                if package_config:
                    parsed_qty, parse_method = self.parse_package_quantity(package_config)
                    if parsed_qty:
                        extracted_qty = parsed_qty
                        logger.info(f"Used package configuration: {package_config} -> {parsed_qty}")

                # Try UoM conversion
                converted_qty = extracted_qty
                conversion_ratio = None

                try:
                    converted_qty, conversion_ratio = self.convert_quantity_units(
                        float(extracted_qty),
                        extracted_unit,
                        order_unit,
                        product_context=f"{order_item.get('name', '')} {matched_sku}"
                    )
                    conversions_attempted += 1

                    if conversion_ratio is not None:
                        logger.info(f"UoM conversion: {extracted_qty} {extracted_unit} -> {converted_qty} {order_unit} (ratio: {conversion_ratio})")
                except Exception as e:
                    logger.error(f"UoM conversion failed: {e}")

                # Check for quantity match after conversion
                order_qty_float = float(order_qty)
                tolerance = max(1, order_qty_float * 0.05)  # 5% tolerance or minimum 1 unit

                if abs(converted_qty - order_qty_float) <= tolerance:
                    # Quantities match within tolerance
                    extracted_item['quantity_equivalent'] = converted_qty
                    extracted_item['status'] = 'MATCHED'
                    if conversion_ratio:
                        successful_conversions += 1
                else:
                    # Quantity mismatch
                    extracted_item['status'] = 'QUANTITY_MISMATCH'

                    # Determine severity
                    percentage_diff = abs(converted_qty - order_qty_float) / order_qty_float * 100
                    if percentage_diff > 20:
                        severity = 'HIGH'
                    elif percentage_diff > 10:
                        severity = 'MEDIUM'
                    else:
                        severity = 'LOW'

                    enhanced_discrepancies.append({
                        'type': 'QUANTITY_MISMATCH',
                        'description': f'Quantity mismatch for {matched_sku}',
                        'expected': f'{order_qty} {order_unit}',
                        'actual': f'{extracted_qty} {extracted_unit}' + (f' (≈{converted_qty:.1f} {order_unit})' if conversion_ratio else ''),
                        'sku_id': matched_sku,
                        'severity': severity,
                        'percentage_diff': round(percentage_diff, 1)
                    })

            # Update validation data
            validation_data['discrepancies'] = enhanced_discrepancies
            validation_data['uom_analysis'] = {
                'conversions_attempted': conversions_attempted,
                'successful_conversions': successful_conversions,
                'unresolved_uom_issues': conversions_attempted - successful_conversions
            }

            logger.info(f"UoM validation complete: {successful_conversions}/{conversions_attempted} successful conversions")
            return validation_data

        except Exception as e:
            logger.error(f"Error in UoM validation: {e}")
            return validation_data

    def download_image(self, image_url):
        """Download image from URL and convert to base64"""
        try:
            logger.info(f"Attempting to download image from: {image_url}")

            headers = {
                "authorization": f"Bearer {BEARER_TOKEN}",
                "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "accept": "*/*"
            }

            response = requests.get(image_url, headers=headers, timeout=30)
            logger.info(f"Image download response status: {response.status_code}")

            response.raise_for_status()

            # Check if we got actual image content
            if not response.content:
                logger.error("Downloaded content is empty")
                return None, None

            logger.info(f"Downloaded image size: {len(response.content)} bytes")

            # Convert to base64
            image_base64 = base64.b64encode(response.content).decode('utf-8')

            # Detect image format from content-type header or URL
            image_format = 'jpeg'  # default
            content_type = response.headers.get('content-type', '').lower()

            if 'png' in content_type or image_url.lower().endswith('.png'):
                image_format = 'png'
            elif 'pdf' in content_type or image_url.lower().endswith('.pdf'):
                image_format = 'pdf'
            elif 'jpeg' in content_type or 'jpg' in content_type or image_url.lower().endswith('.jpg') or image_url.lower().endswith('.jpeg'):
                image_format = 'jpeg'

            logger.info(f"Detected image format: {image_format}")
            return image_base64, image_format

        except requests.RequestException as e:
            logger.error(f"HTTP error downloading image from {image_url}: {e}")
            return None, None
        except Exception as e:
            logger.error(f"Unexpected error downloading image from {image_url}: {e}")
            return None, None

    def fix_json_response(self, json_str):
        """Fix common JSON formatting issues in AI responses"""
        try:
            # First, try to find where the JSON might be truncated
            # Look for incomplete strings or objects

            # Remove any trailing incomplete content
            lines = json_str.split('\n')
            fixed_lines = []

            for i, line in enumerate(lines):
                # Skip empty lines
                if not line.strip():
                    continue

                # Check if this line starts a string but doesn't end it properly
                if '"' in line:
                    quote_count = line.count('"')
                    # If odd number of quotes, the string might be incomplete
                    if quote_count % 2 == 1 and i == len(lines) - 1:
                        # This is likely an incomplete string at the end
                        break

                fixed_lines.append(line)

            json_str = '\n'.join(fixed_lines)

            # Try to find the last complete JSON object/array
            brace_count = 0
            bracket_count = 0
            in_string = False
            escape_next = False
            last_complete_pos = -1

            for i, char in enumerate(json_str):
                if escape_next:
                    escape_next = False
                    continue

                if char == '\\':
                    escape_next = True
                    continue

                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue

                if in_string:
                    continue

                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                elif char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1

                # If we have balanced braces/brackets, this might be a complete JSON
                if brace_count == 0 and bracket_count == 0 and char in '}]':
                    last_complete_pos = i

            if last_complete_pos > -1:
                json_str = json_str[:last_complete_pos + 1]

            # Additional cleanup - don't replace newlines in JSON strings as it corrupts them

            # Fix common Unicode issues
            json_str = json_str.encode('utf-8', errors='replace').decode('utf-8')

            return json_str

        except Exception as e:
            logger.error(f"Error fixing JSON response: {e}")
            return json_str

    def create_fallback_response(self, partial_response):
        """Create a fallback response when JSON parsing fails"""
        try:
            import re

            # Try to extract key information using regex
            validation_result = "INVALID"
            confidence_score = 0.5
            discrepancies = []
            summary = {}

            # Look for validation result
            if "VALID" in partial_response.upper():
                if "INVALID" in partial_response.upper():
                    validation_result = "INVALID"
                else:
                    validation_result = "VALID"

            # Try to extract confidence score
            confidence_match = re.search(r'"confidence_score":\s*([0-9.]+)', partial_response)
            if confidence_match:
                try:
                    confidence_score = float(confidence_match.group(1))
                except ValueError:
                    pass

            # Try to extract discrepancies from partial text
            discrepancy_patterns = [
                r'"type":\s*"([^"]+)"[^}]*"description":\s*"([^"]+)"',
                r'"description":\s*"([^"]+)"[^}]*"type":\s*"([^"]+)"'
            ]

            for pattern in discrepancy_patterns:
                matches = re.findall(pattern, partial_response)
                for match in matches:
                    if len(match) == 2:
                        if 'type' in pattern and pattern.index('type') < pattern.index('description'):
                            discrepancies.append({
                                "type": match[0],
                                "description": match[1]
                            })
                        else:
                            discrepancies.append({
                                "type": match[1],
                                "description": match[0]
                            })

            # Try to extract summary counts
            total_items_match = re.search(r'"total_items_found":\s*([0-9]+)', partial_response)
            expected_items_match = re.search(r'"total_items_expected":\s*([0-9]+)', partial_response)
            matched_items_match = re.search(r'"items_matched":\s*([0-9]+)', partial_response)

            if total_items_match or expected_items_match or matched_items_match:
                summary = {
                    "total_items_found": int(total_items_match.group(1)) if total_items_match else 0,
                    "total_items_expected": int(expected_items_match.group(1)) if expected_items_match else 0,
                    "items_matched": int(matched_items_match.group(1)) if matched_items_match else 0,
                    "items_with_discrepancies": len(discrepancies)
                }

            # Only return fallback if we extracted something useful
            if discrepancies or summary:
                logger.info(f"Created fallback response with {len(discrepancies)} discrepancies")
                return {
                    'success': True,
                    'is_valid': validation_result == 'VALID',
                    'confidence_score': confidence_score,
                    'discrepancies': discrepancies,
                    'summary': summary,
                    'ai_response': partial_response,
                    'fallback': True
                }

            return None

        except Exception as e:
            logger.error(f"Error creating fallback response: {e}")
            return None

    def normalize_text_for_matching(self, text):
        """Advanced text normalization for better Arabic/English matching"""
        if not text:
            return ""

        # Convert to lowercase
        text = text.lower().strip()

        # Remove common Arabic diacritics
        arabic_diacritics = "ًٌٍَُِّْ"
        for diacritic in arabic_diacritics:
            text = text.replace(diacritic, "")

        # Normalize common Arabic letter variations
        text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        text = text.replace("ة", "ه")  # Ta marbuta to ha
        text = text.replace("ي", "ى")  # Alif maksura normalization

        # Remove punctuation and special characters but keep Arabic and alphanumeric
        import re
        text = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', text)

        # Normalize whitespace
        text = ' '.join(text.split())

        return text

    def extract_meaningful_words(self, text):
        """Extract meaningful words, filtering out common stopwords"""
        if not text:
            return set()

        # Arabic stopwords (common ones)
        arabic_stopwords = {'من', 'في', 'على', 'إلى', 'مع', 'هذا', 'هذه', 'ذلك', 'التي', 'الذي', 'كل', 'بعض'}

        # English stopwords (common ones)
        english_stopwords = {'the', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'a', 'an'}

        words = set(text.split())

        # Filter out stopwords and very short words (but keep 2-letter words for Arabic)
        meaningful_words = {word for word in words
                          if len(word) > 1 and
                          word not in arabic_stopwords and
                          word not in english_stopwords}

        return meaningful_words

    def calculate_bilingual_match(self, extracted_name, gs1_product):
        """Advanced bilingual matching for Arabic/English product names"""
        try:
            import difflib

            if not extracted_name or not gs1_product:
                return False, 0.0

            # Use advanced normalization
            extracted_name_normalized = self.normalize_text_for_matching(extracted_name)

            # Get all possible names to match against
            match_candidates = []

            # Add all GS1 names
            product_names = gs1_product.get('product_names', {})
            brand_names = gs1_product.get('brand_names', {})

            # Add English names with normalization
            if product_names.get('english'):
                match_candidates.append(('product_en', self.normalize_text_for_matching(product_names['english'])))
            if brand_names.get('english'):
                match_candidates.append(('brand_en', self.normalize_text_for_matching(brand_names['english'])))

            # Add Arabic names with normalization
            if product_names.get('arabic'):
                match_candidates.append(('product_ar', self.normalize_text_for_matching(product_names['arabic'])))
            if brand_names.get('arabic'):
                match_candidates.append(('brand_ar', self.normalize_text_for_matching(brand_names['arabic'])))

            # Add primary name for backward compatibility
            if product_names.get('primary'):
                match_candidates.append(('primary', self.normalize_text_for_matching(product_names['primary'])))

            # Add backward compatibility names
            if gs1_product.get('product_name'):
                match_candidates.append(('legacy_product', self.normalize_text_for_matching(gs1_product['product_name'])))
            if gs1_product.get('brand_name'):
                match_candidates.append(('legacy_brand', self.normalize_text_for_matching(gs1_product['brand_name'])))

            logger.info(f"Matching '{extracted_name}' against {len(match_candidates)} candidates")

            best_match = None
            best_score = 0.0

            for match_type, candidate_name in match_candidates:
                if not candidate_name:
                    continue

                # Exact match (highest score)
                if extracted_name_normalized == candidate_name:
                    logger.info(f"EXACT normalized match found: '{extracted_name}' == '{candidate_name}' ({match_type})")
                    return True, 1.0

                # Advanced word-based matching using meaningful words
                extracted_words = self.extract_meaningful_words(extracted_name_normalized)
                candidate_words = self.extract_meaningful_words(candidate_name)

                if extracted_words and candidate_words:
                    # Jaccard similarity (intersection over union)
                    intersection = len(extracted_words & candidate_words)
                    union = len(extracted_words | candidate_words)
                    jaccard_score = intersection / union if union > 0 else 0

                    # Containment score (how much of extracted is in candidate)
                    containment_score = intersection / len(extracted_words) if len(extracted_words) > 0 else 0

                    # Combined score with bias towards containment
                    combined_score = (jaccard_score * 0.6) + (containment_score * 0.4)

                    logger.info(f"Word match: '{extracted_name}' vs '{candidate_name}' ({match_type}) = {combined_score:.3f}")

                    if combined_score > best_score:
                        best_score = combined_score
                        best_match = (match_type, candidate_name)

                # Fuzzy string matching using difflib on normalized text
                similarity = difflib.SequenceMatcher(None, extracted_name_normalized, candidate_name).ratio()
                logger.info(f"String similarity: '{extracted_name}' vs '{candidate_name}' ({match_type}) = {similarity:.3f}")

                if similarity > best_score:
                    best_score = similarity
                    best_match = (match_type, candidate_name)

            # Dynamic threshold based on content language mix
            # More lenient for mixed Arabic/English content
            has_arabic = any('\u0600' <= char <= '\u06FF' for char in extracted_name)
            has_english = any(char.isascii() and char.isalpha() for char in extracted_name)

            if has_arabic and has_english:
                threshold = 0.55  # More lenient for mixed content
            elif has_arabic:
                threshold = 0.6   # Standard for Arabic
            else:
                threshold = 0.65  # Slightly stricter for English-only
            is_match = best_score >= threshold

            if best_match:
                logger.info(f"Best match for '{extracted_name}': {best_match[1]} ({best_match[0]}) with score {best_score:.3f} (threshold: {threshold:.2f}) - {'MATCH' if is_match else 'NO MATCH'}")
            else:
                logger.info(f"No good match found for '{extracted_name}' (best score: {best_score:.3f}, threshold: {threshold:.2f})")

            return is_match, best_score

        except Exception as e:
            logger.error(f"Error in bilingual matching: {e}")
            return False, 0.0

    def enhance_with_gtin_verification(self, validation_data):
        """Enhance validation results with GS1 GTIN verification"""
        try:
            logger.info("Starting GTIN verification enhancement")

            # Get extracted items from validation data
            extracted_items = validation_data.get('extracted_items', [])
            gtin_verification = []
            enhanced_discrepancies = list(validation_data.get('discrepancies', []))

            for item in extracted_items:
                gtin = item.get('extracted_gtin')
                if gtin and len(str(gtin)) == 13:
                    logger.info(f"Verifying GTIN: {gtin}")

                    # Get product info from GS1
                    gs1_product = self.gs1_validator.get_product_info(str(gtin))

                    gtin_verification_item = {
                        'gtin': gtin,
                        'extracted_name': item.get('extracted_name', ''),
                        'gs1_verified': gs1_product is not None,
                        'gs1_product_info': gs1_product
                    }

                    if gs1_product:
                        # Use advanced bilingual matching
                        extracted_name = item.get('extracted_name', '')
                        name_match, match_confidence = self.calculate_bilingual_match(extracted_name, gs1_product)

                        gtin_verification_item['name_match'] = name_match
                        gtin_verification_item['match_confidence'] = match_confidence

                        # Add discrepancy if names don't match
                        if not name_match:
                            enhanced_discrepancies.append({
                                'type': 'GTIN_NAME_MISMATCH',
                                'description': f'Product name mismatch for GTIN {gtin}',
                                'expected': f'GS1 verified: {gs1_product.get("product_name", "N/A")} ({gs1_product.get("brand_name", "N/A")})',
                                'actual': f'Document shows: {item.get("extracted_name", "N/A")}',
                                'gtin': gtin
                            })

                        logger.info(f"GTIN {gtin} verified: {gs1_product.get('product_name', 'N/A')}")
                    else:
                        gtin_verification_item['name_match'] = False
                        gtin_verification_item['match_confidence'] = 0.0
                        enhanced_discrepancies.append({
                            'type': 'GTIN_NOT_VERIFIED',
                            'description': f'GTIN {gtin} could not be verified in GS1 database',
                            'expected': 'Valid GTIN in GS1 registry',
                            'actual': f'GTIN {gtin} not found or invalid',
                            'gtin': gtin
                        })

                        logger.warning(f"GTIN {gtin} not found in GS1 database")

                    gtin_verification.append(gtin_verification_item)

            # Update validation result based on GTIN verification
            original_valid = validation_data.get('validation_result') == 'VALID'
            gtin_issues = len([v for v in gtin_verification if not v.get('name_match', False)])

            # If there are GTIN mismatches, mark as invalid
            if gtin_issues > 0 and original_valid:
                validation_data['validation_result'] = 'INVALID'
                logger.info(f"Validation marked INVALID due to {gtin_issues} GTIN verification issues")

            # Update summary
            summary = validation_data.get('summary', {})
            summary['gtins_verified'] = len([v for v in gtin_verification if v.get('gs1_verified', False)])
            summary['gtins_matched'] = len([v for v in gtin_verification if v.get('name_match', False)])
            summary['gtin_verification_issues'] = gtin_issues

            # Add GTIN verification data
            validation_data['gtin_verification'] = gtin_verification
            validation_data['discrepancies'] = enhanced_discrepancies
            validation_data['summary'] = summary

            logger.info(f"GTIN verification complete: {len(gtin_verification)} GTINs processed")
            return validation_data

        except Exception as e:
            logger.error(f"Error in GTIN verification: {e}")
            # Return original validation data if GTIN verification fails
            return validation_data

    def apply_conservative_missing_item_logic(self, validation_data, order_items):
        """Apply ultra-conservative logic to missing item detection"""
        try:
            logger.info("Applying conservative missing item logic")

            extracted_items = validation_data.get('extracted_items', [])
            discrepancies = list(validation_data.get('discrepancies', []))

            # Remove existing missing item discrepancies to re-evaluate them
            original_missing_discrepancies = []
            filtered_discrepancies = []

            for disc in discrepancies:
                if disc.get('type') == 'MISSING_ITEM':
                    original_missing_discrepancies.append(disc)
                else:
                    filtered_discrepancies.append(disc)

            # Ultra-conservative thresholds
            CONSERVATIVE_MATCH_THRESHOLD = 0.7  # Higher threshold for considering items matched
            MIN_CONFIDENCE_FOR_MISSING = 0.95   # Very high confidence required to mark as missing

            # Build comprehensive matching profile for each order item
            for order_item in order_items:
                order_sku = order_item.get('sku_id', '').lower().strip()
                order_name = order_item.get('name', '').lower().strip()
                order_quantity = order_item.get('quantity', 0)

                logger.info(f"Checking order item: {order_sku} - {order_name} (qty: {order_quantity})")

                # Find potential matches with multiple matching strategies
                potential_matches = []

                for extracted_item in extracted_items:
                    extracted_sku = extracted_item.get('extracted_sku', '').lower().strip()
                    extracted_name = extracted_item.get('extracted_name', '').lower().strip()
                    extracted_gtin = extracted_item.get('extracted_gtin')
                    match_confidence = extracted_item.get('match_confidence', 0)

                    # Strategy 1: Direct SKU match
                    if order_sku and extracted_sku and order_sku == extracted_sku:
                        potential_matches.append({
                            'strategy': 'direct_sku',
                            'confidence': 1.0,
                            'item': extracted_item
                        })
                        logger.info(f"Direct SKU match found: {order_sku}")

                    # Strategy 2: High confidence match from AI
                    elif match_confidence >= CONSERVATIVE_MATCH_THRESHOLD:
                        potential_matches.append({
                            'strategy': 'ai_high_confidence',
                            'confidence': match_confidence,
                            'item': extracted_item
                        })
                        logger.info(f"High confidence AI match: {match_confidence}")

                    # Strategy 3: GTIN verification match
                    if extracted_gtin:
                        gtin_verification = validation_data.get('gtin_verification', [])
                        gtin_info = next((g for g in gtin_verification if g.get('gtin') == extracted_gtin), None)
                        if gtin_info and gtin_info.get('name_match', False):
                            # Cross-check if this GTIN product matches our order item
                            gs1_product = gtin_info.get('gs1_product_info', {})
                            gs1_name = gs1_product.get('product_name', '').lower()

                            # Use bilingual matching for GTIN product name
                            if gs1_name:
                                gtin_name_match, gtin_match_score = self.calculate_bilingual_match(order_name, gs1_product)
                                if gtin_name_match and gtin_match_score >= CONSERVATIVE_MATCH_THRESHOLD:
                                    potential_matches.append({
                                        'strategy': 'gtin_verified',
                                        'confidence': gtin_match_score,
                                        'item': extracted_item,
                                        'gtin': extracted_gtin
                                    })
                                    logger.info(f"GTIN verified match: {extracted_gtin} with score {gtin_match_score}")

                    # Strategy 4: Fuzzy name matching (only as additional confirmation)
                    if order_name and extracted_name:
                        # Create a mock GS1 product structure for bilingual matching
                        mock_product = {
                            'product_names': {'primary': extracted_name, 'english': extracted_name},
                            'brand_names': {'primary': '', 'english': ''}
                        }
                        name_match, name_score = self.calculate_bilingual_match(order_name, mock_product)
                        if name_match and name_score >= CONSERVATIVE_MATCH_THRESHOLD:
                            potential_matches.append({
                                'strategy': 'fuzzy_name',
                                'confidence': name_score,
                                'item': extracted_item
                            })
                            logger.info(f"Fuzzy name match: {order_name} -> {extracted_name} with score {name_score}")

                # Conservative decision making
                best_match = None
                if potential_matches:
                    # Sort by confidence, prioritize direct matches
                    potential_matches.sort(key=lambda x: (x['confidence'], 1 if x['strategy'] == 'direct_sku' else 0), reverse=True)
                    best_match = potential_matches[0]

                    logger.info(f"Best match for {order_sku}: {best_match['strategy']} with confidence {best_match['confidence']}")

                # Ultra-conservative missing item logic
                should_mark_missing = False
                missing_confidence = 0.0

                if not potential_matches:
                    # Only mark as missing if we have very high confidence in extraction completeness
                    extraction_completeness = validation_data.get('confidence_score', 0)
                    overall_match_rate = len([item for item in extracted_items if item.get('match_confidence', 0) >= 0.8])
                    total_extracted = len(extracted_items)

                    if (extraction_completeness >= MIN_CONFIDENCE_FOR_MISSING and
                        total_extracted > 0 and
                        overall_match_rate / total_extracted >= 0.8):  # Most other items matched well

                        # Additional checks for missing item confidence
                        missing_confidence = min(extraction_completeness, 0.98)  # Cap at 98% to stay humble
                        should_mark_missing = True
                        logger.info(f"Conservative missing item detected: {order_sku} with {missing_confidence} confidence")
                    else:
                        logger.info(f"Not confident enough to mark {order_sku} as missing (extraction: {extraction_completeness}, match rate: {overall_match_rate}/{total_extracted})")

                # Add missing item discrepancy only if ultra-conservative criteria are met
                if should_mark_missing:
                    filtered_discrepancies.append({
                        'type': 'MISSING_ITEM',
                        'description': f'Order item not found in GRN with high confidence',
                        'expected': f'{order_item.get("name", "N/A")} (SKU: {order_sku}, Qty: {order_quantity})',
                        'actual': 'Not found in delivery document',
                        'confidence': missing_confidence,
                        'conservative_analysis': True
                    })

            # Update validation data with conservative analysis
            validation_data['discrepancies'] = filtered_discrepancies

            # Update summary
            summary = validation_data.get('summary', {})
            missing_items = len([d for d in filtered_discrepancies if d.get('type') == 'MISSING_ITEM'])
            summary['missing_items_conservative'] = missing_items
            summary['conservative_analysis_applied'] = True

            # Re-evaluate validation result
            if missing_items > 0 and validation_data.get('validation_result') == 'VALID':
                validation_data['validation_result'] = 'INVALID'
                logger.info(f"Validation marked INVALID due to {missing_items} conservatively detected missing items")

            validation_data['summary'] = summary
            logger.info(f"Conservative missing item logic complete: {missing_items} items marked missing")

            return validation_data

        except Exception as e:
            logger.error(f"Error in conservative missing item logic: {e}")
            return validation_data

    def store_validation_result(self, order_id, grn_image_url, validation_result, processing_time_seconds):
        """Store validation result in database"""
        try:
            # Handle both normal validation result and fallback response structures
            validation_data = validation_result.get('validation_data', validation_result)

            # Check if validation result already exists for this order
            existing_validation = ValidationResult.query.filter_by(
                order_id=order_id,
                grn_image_url=grn_image_url
            ).first()

            if existing_validation:
                # Update existing validation
                existing_validation.is_valid = validation_result.get('is_valid', False)
                existing_validation.has_document = validation_data.get('has_document', False)
                existing_validation.confidence_score = validation_result.get('confidence_score', 0)
                existing_validation.extracted_items = json.dumps(validation_data.get('extracted_items', []))
                existing_validation.discrepancies = json.dumps(validation_result.get('discrepancies', []))
                existing_validation.summary = json.dumps(validation_result.get('summary', {}))
                existing_validation.gtin_verification = json.dumps(validation_result.get('gtin_verification', []))
                existing_validation.ai_response = validation_result.get('ai_response', '')
                existing_validation.processing_time = processing_time_seconds
                existing_validation.is_reprocessed = True
                existing_validation.validation_date = datetime.now()

                logger.info(f"Updated existing validation result for order {order_id}")
            else:
                # Create new validation result
                validation_record = ValidationResult(
                    order_id=order_id,
                    grn_image_url=grn_image_url,
                    is_valid=validation_result.get('is_valid', False),
                    has_document=validation_data.get('has_document', False),
                    confidence_score=validation_result.get('confidence_score', 0),
                    extracted_items=json.dumps(validation_data.get('extracted_items', [])),
                    discrepancies=json.dumps(validation_result.get('discrepancies', [])),
                    summary=json.dumps(validation_result.get('summary', {})),
                    gtin_verification=json.dumps(validation_result.get('gtin_verification', [])),
                    ai_response=validation_result.get('ai_response', ''),
                    processing_time=processing_time_seconds
                )

                db.session.add(validation_record)
                logger.info(f"Created new validation result for order {order_id}")

            db.session.commit()
            logger.info(f"Successfully stored validation result for order {order_id} in database")
            return True

        except Exception as e:
            logger.error(f"Error storing validation result for order {order_id}: {e}")
            db.session.rollback()
            return False

    def get_stored_validation_result(self, order_id, grn_image_url=None):
        """Get stored validation result from database"""
        try:
            query = ValidationResult.query.filter_by(order_id=order_id)

            if grn_image_url:
                query = query.filter_by(grn_image_url=grn_image_url)

            # Get the most recent validation for this order
            validation = query.order_by(ValidationResult.validation_date.desc()).first()

            if validation:
                logger.info(f"Found stored validation result for order {order_id}")
                return validation.to_dict()
            else:
                logger.info(f"No stored validation result found for order {order_id}")
                return None

        except Exception as e:
            logger.error(f"Error getting stored validation result: {e}")
            return None

    def validate_grn_against_order(self, order_data, grn_image_url):
        """Validate GRN document against order data using Google AI"""
        if not self.api_key:
            return {
                'success': False,
                'error': 'Google AI API key not configured',
                'is_valid': False
            }

        try:
            validation_start_time = time.time()

            # Download and encode image
            logger.info(f"Downloading GRN image from: {grn_image_url}")
            image_base64, image_format = self.download_image(grn_image_url)
            if not image_base64:
                logger.error(f"Failed to download GRN image from: {grn_image_url}")
                return {
                    'success': False,
                    'error': 'Failed to download GRN image',
                    'is_valid': False
                }

            # Prepare order data for comparison
            order_items = []
            if 'lineItems' in order_data:
                for item in order_data['lineItems']:
                    order_item = {
                        'sku_id': item.get('id', ''),
                        'name': item.get('name', ''),
                        'quantity': item.get('quantity', 0),
                        'unit': item.get('quantityUnit', ''),
                        'weight': item.get('totalWeight', {}).get('value', 0) if item.get('totalWeight') else 0,
                        'weight_unit': item.get('totalWeight', {}).get('unit', '') if item.get('totalWeight') else ''
                    }
                    order_items.append(order_item)

            # Debug logging
            logger.info(f"Prepared {len(order_items)} order items for validation:")
            for item in order_items[:3]:  # Log first 3 items
                logger.info(f"  SKU: {item['sku_id']}, Name: {item['name']}, Qty: {item['quantity']} {item['unit']}")

            # Create enhanced prompt following PRD workflow requirements
            prompt = f"""
You are a professional GRN validation system following a structured workflow. Analyze this image systematically according to the Order Validation Workflow outlined below.

**STEP 1: DOCUMENT DETECTION (Critical First Step)**
Examine the image carefully and determine:
- Does this image contain a readable document (GRN, receipt, invoice, delivery note, etc.)?
- Is the document clear and readable with structured data/text visible?
- If NO document is detected or image is unclear/unreadable, set "has_document": false and "validation_result": "NO_DOCUMENT"

**STEP 2: DATA EXTRACTION (Only if document detected)**
If a document IS present, extract ALL visible items with maximum precision:
- Product names/descriptions (both Arabic and English if present)
- SKU codes/item codes/product IDs
- Quantities with units (boxes, units, kg, etc.)
- **GTIN/BARCODE NUMBERS** (13-digit codes starting with 622, 623, 624 for Egyptian products)
- Package configurations (e.g., 5+1)*4, 2*10, etc.)
- Unit of Measurement details

**STEP 3: ITEM MATCHING LOGIC (Following PRD Priority)**
For each extracted item, attempt matching using this EXACT priority order:
1. **PRIMARY MATCH: SKU** - Match order.sku_id with extracted_sku (exact match)
2. **SECONDARY MATCH: GTIN** - If no SKU match, use extracted_gtin for GS1 lookup
3. **FUZZY NAME MATCHING** - Match product names (Arabic/English bilingual support)

**STEP 4: QUANTITY VALIDATION WITH UOM HANDLING**
Once items are matched, validate quantities considering:
- Unit of Measurement discrepancies (e.g., "12 units" vs "1 box")
- Package configurations (e.g., "6 boxes" vs "6*(5+1) units")
- Weight vs count differences
- Partial deliveries vs full orders

**STEP 5: DISCREPANCY IDENTIFICATION**
Flag ALL discrepancies with specific types:
- MISSING_ITEM: In order but not found in GRN
- EXTRA_ITEM: In GRN but not in order
- QUANTITY_MISMATCH: Different quantities
- GTIN_NAME_MISMATCH: GTIN verified but names don't match
- GTIN_NOT_VERIFIED: GTIN not found in database
- UOM_MISMATCH: Unit of measurement issues

EXPECTED ORDER DATA:
{json.dumps(order_items, indent=2)}

CRITICAL MATCHING INSTRUCTIONS:
- Total Expected Items: {len(order_items)} different SKUs
- MUST match items by SKU first (exact match of sku_id field)
- MUST include full product name and unit of measurement (UOM) data in response
- Look for Egyptian GTIN codes: 13-digit numbers starting with 622, 623, 624
- Common brands: PAPIA, FAMILIA
- Package formats: (5+1)*4, 2*10, etc.
- For each order item above, you MUST attempt to find a matching item in the GRN document
- If you cannot match an item, it should be reported as MISSING_ITEM
- Product names may appear in Arabic in the GRN but are in English in the order data

REQUIRED OUTPUT FORMAT (JSON only):
{{
    "has_document": true or false,
    "document_description": "Brief description of document type found or why no document detected",
    "validation_result": "VALID" or "INVALID" or "NO_DOCUMENT",
    "confidence_score": 0.95,
    "extracted_items": [
        {{
            "extracted_sku": "SKU/item code from document or null",
            "extracted_gtin": "13-digit GTIN/barcode number or null",
            "extracted_name": "product name/description from document",
            "extracted_quantity": "quantity number from document",
            "extracted_unit": "unit of measurement (boxes, units, kg, etc.)",
            "extracted_weight": "weight value if available or null",
            "package_config": "package configuration like (5+1)*4 or null",
            "matched_order_sku": "matching order SKU or null",
            "match_method": "SKU_MATCH or GTIN_MATCH or NAME_MATCH or NONE",
            "match_confidence": 0.98,
            "quantity_equivalent": "calculated equivalent quantity in order units",
            "status": "MATCHED" or "EXTRA" or "QUANTITY_MISMATCH"
        }}
    ],
    "discrepancies": [
        {{
            "type": "MISSING_ITEM" or "EXTRA_ITEM" or "QUANTITY_MISMATCH" or "UOM_MISMATCH" or "GTIN_NAME_MISMATCH" or "GTIN_NOT_VERIFIED",
            "description": "Clear description of the specific issue",
            "expected": "what was expected from order",
            "actual": "what was found in GRN document",
            "sku_id": "relevant SKU if applicable",
            "gtin": "relevant GTIN if applicable",
            "severity": "HIGH" or "MEDIUM" or "LOW"
        }}
    ],
    "summary": {{
        "total_items_expected": {len(order_items)},
        "total_items_found": "number of items found in GRN (integer)",
        "items_perfectly_matched": "items with exact SKU/GTIN/quantity match (integer)",
        "items_with_discrepancies": "items with issues (integer)",
        "gtins_extracted": "number of GTIN codes found (integer)",
        "missing_items": "items in order but not in GRN (integer)",
        "extra_items": "items in GRN but not in order (integer)",
        "quantity_mismatches": "items with quantity differences (integer)"
    }},
    "uom_analysis": {{
        "conversions_attempted": "number of UoM conversions tried",
        "successful_conversions": "conversions that resolved discrepancies",
        "unresolved_uom_issues": "remaining UoM conflicts"
    }}
}}

CRITICAL REQUIREMENTS:
1. **DOCUMENT DETECTION FIRST** - If no readable document: has_document=false, validation_result="NO_DOCUMENT"
2. **FOLLOW PRD MATCHING PRIORITY** - SKU first, then GTIN, then fuzzy name matching
3. **UOM INTELLIGENCE** - Convert between units (boxes↔units, kg↔grams, etc.)
4. **GTIN EXTRACTION** - ALWAYS look for 13-digit barcodes/GTINs starting with 622/623/624 and include in extracted_gtin field
5. **PRECISE QUANTITY MATCHING** - Account for package configurations and include unit details
6. **BILINGUAL SUPPORT** - Handle Arabic/English product names
7. **SEVERITY ASSESSMENT** - Classify discrepancies by business impact
8. **COMPLETE DATA EXTRACTION** - For each item, MUST include sku, gtin, name, quantity, and unit fields
9. **SUMMARY ACCURACY** - Provide exact integer counts in summary section
10. Return ONLY valid JSON, no markdown or extra text
"""

            # Prepare request to Google AI
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": f"image/{image_format}",
                                "data": image_base64
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "topK": 1,
                    "topP": 0.8,
                    "maxOutputTokens": 4096
                }
            }

            headers = {
                "Content-Type": "application/json"
            }

            logger.info(f"Sending request to Google AI API with payload size: {len(str(payload))} chars")

            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                headers=headers,
                json=payload,
                timeout=60
            )

            logger.info(f"Google AI API response status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"Google AI API error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f'Google AI API error: {response.status_code} - {response.text[:200]}',
                    'is_valid': False
                }

            # Check if response has content
            if not response.content:
                logger.error("Empty response from Google AI API")
                return {
                    'success': False,
                    'error': 'Empty response from Google AI API',
                    'is_valid': False
                }

            logger.info(f"Google AI API response size: {len(response.content)} bytes")

            try:
                result = response.json()
                logger.info(f"Successfully parsed Google AI API response")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode Google AI API response: {e}")
                logger.error(f"Response status: {response.status_code}")
                logger.error(f"Response headers: {dict(response.headers)}")
                logger.error(f"Response content (first 1000 chars): {response.text[:1000]}")
                return {
                    'success': False,
                    'error': f'Invalid JSON response from Google AI API: {str(e)}',
                    'is_valid': False,
                    'debug_info': {
                        'status_code': response.status_code,
                        'content_type': response.headers.get('content-type', 'unknown'),
                        'content_length': len(response.content)
                    }
                }

            if 'candidates' not in result or not result['candidates']:
                return {
                    'success': False,
                    'error': 'No response from Google AI',
                    'is_valid': False
                }

            # Parse the AI response
            ai_response = result['candidates'][0]['content']['parts'][0]['text']

            # Clean and parse JSON response
            try:
                # Remove any markdown formatting
                ai_response = ai_response.strip()
                if ai_response.startswith('```json'):
                    ai_response = ai_response[7:]
                if ai_response.endswith('```'):
                    ai_response = ai_response[:-3]

                # Clean up common JSON issues
                ai_response = ai_response.strip()

                # Try to fix common JSON issues
                ai_response = self.fix_json_response(ai_response)

                # Clean BOM and other invisible characters
                ai_response = ai_response.encode('utf-8').decode('utf-8-sig').strip()

                # Debug the first and last few characters
                logger.info(f"JSON response starts with: {repr(ai_response[:50])}")
                logger.info(f"JSON response ends with: {repr(ai_response[-50:])}")
                logger.info(f"JSON response length: {len(ai_response)} chars")

                # Check if JSON appears truncated
                if not ai_response.rstrip().endswith('}'):
                    logger.warning("JSON response appears to be truncated (doesn't end with })")

                validation_data = json.loads(ai_response)

                # Enhance validation with GTIN verification from GS1
                enhanced_validation = self.enhance_with_gtin_verification(validation_data)

                # Apply enhanced quantity validation with UoM handling
                uom_enhanced_validation = self.validate_quantities_with_uom(enhanced_validation, order_items)

                # Apply ultra-conservative missing item detection logic
                final_validation = self.apply_conservative_missing_item_logic(uom_enhanced_validation, order_items)

                # Create result object
                result = {
                    'success': True,
                    'is_valid': final_validation.get('validation_result') == 'VALID',
                    'validation_data': final_validation,
                    'confidence_score': final_validation.get('confidence_score', 0),
                    'discrepancies': final_validation.get('discrepancies', []),
                    'summary': final_validation.get('summary', {}),
                    'ai_response': ai_response,
                    'gtin_verification': final_validation.get('gtin_verification', [])
                }

                # Store validation result in database
                order_id = order_data.get('id')
                if order_id:
                    processing_time = time.time() - validation_start_time
                    self.store_validation_result(order_id, grn_image_url, result, processing_time)

                return result

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                logger.error(f"Error at line {e.lineno}, column {e.colno}, char {e.pos}")
                logger.error(f"AI Response length: {len(ai_response)} chars")
                logger.error(f"AI Response first 200 chars: {repr(ai_response[:200])}")
                logger.error(f"AI Response around error position: {repr(ai_response[max(0, e.pos-50):e.pos+50])}")

                # Try alternative parsing methods
                try:
                    # Try with strict=False to handle Unicode better
                    validation_data = json.loads(ai_response, strict=False)
                    logger.info("Successfully parsed with strict=False")

                    # Continue with normal processing
                    enhanced_validation = self.enhance_with_gtin_verification(validation_data)
                    uom_enhanced_validation = self.validate_quantities_with_uom(enhanced_validation, order_items)
                    final_validation = self.apply_conservative_missing_item_logic(uom_enhanced_validation, order_items)

                    result = {
                        'success': True,
                        'is_valid': final_validation.get('validation_result', 'INVALID') == 'VALID',
                        'has_document': final_validation.get('has_document', False),
                        'confidence_score': final_validation.get('confidence_score', 0.0),
                        'ai_response': json.dumps(final_validation),
                        'extracted_items': final_validation.get('extracted_items', []),
                        'discrepancies': final_validation.get('discrepancies', []),
                        'summary': final_validation.get('summary', {}),
                        'processing_time': time.time() - validation_start_time
                    }

                    # Store validation result in database
                    order_id = order_data.get('id')
                    if order_id:
                        processing_time = time.time() - validation_start_time
                        self.store_validation_result(order_id, grn_image_url, result, processing_time)

                    return result

                except Exception as e2:
                    logger.error(f"Alternative parsing also failed: {e2}")
                    # Try to create a fallback response from partial data
                    fallback_response = self.create_fallback_response(ai_response)
                    if fallback_response:
                        # Store fallback validation result in database
                        order_id = order_data.get('id')
                        if order_id:
                            processing_time = time.time() - validation_start_time
                        self.store_validation_result(order_id, grn_image_url, fallback_response, processing_time)
                    return fallback_response

                return {
                    'success': False,
                    'error': f'Invalid JSON response from AI: {str(e)}',
                    'is_valid': False,
                    'ai_response': ai_response
                }

        except Exception as e:
            logger.error(f"Error validating GRN: {e}")
            return {
                'success': False,
                'error': str(e),
                'is_valid': False
            }

locus_auth = LocusAuth()
ai_validator = GoogleAIValidator()

@app.route('/')
def index():
    """Main route - directly show dashboard with provided token"""
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    # Get today's date for default filter
    today = datetime.now().strftime("%Y-%m-%d")
    selected_date = request.args.get('date', today)

    # Validate date format
    try:
        datetime.strptime(selected_date, "%Y-%m-%d")
    except ValueError:
        # If invalid date, redirect with error message
        flash(f"Invalid date format: {selected_date}. Please use YYYY-MM-DD format.", "error")
        return redirect(url_for('dashboard', date=today))

    fetch_all = request.args.get('all', 'true').lower() == 'true'  # Default to fetch all

    # Fetch all orders using bearer token
    orders_data = locus_auth.get_orders(
        BEARER_TOKEN,
        'illa-frontdoor',
        date=selected_date,
        fetch_all=fetch_all
    )

    # Enhance orders with validation summaries
    if orders_data and orders_data.get('orders'):
        for order in orders_data['orders']:
            order_id = order.get('id')
            if order_id:
                # Get validation summary for this order
                validation_summary = ai_validator.get_stored_validation_result(order_id)
                if validation_summary:
                    # Parse stored JSON fields if they're strings
                    try:
                        summary_data = json.loads(validation_summary.get('summary', '{}')) if isinstance(validation_summary.get('summary'), str) else validation_summary.get('summary', {})
                        discrepancies_data = json.loads(validation_summary.get('discrepancies', '[]')) if isinstance(validation_summary.get('discrepancies'), str) else validation_summary.get('discrepancies', [])
                    except json.JSONDecodeError:
                        summary_data = {}
                        discrepancies_data = []

                    # Default has_document to True for backward compatibility with older records
                    # Only set to False if explicitly stored as False
                    has_document = validation_summary.get('has_document')
                    if has_document is None:
                        has_document = True  # Default for older records

                    order['validation_summary'] = {
                        'has_validation': True,
                        'is_valid': validation_summary.get('is_valid', False),
                        'has_document': has_document,
                        'confidence_score': validation_summary.get('confidence_score', 0),
                        'validation_date': validation_summary.get('validation_date'),
                        'processing_time': validation_summary.get('processing_time', 0),
                        'summary': summary_data,
                        'discrepancies_count': len(discrepancies_data),
                        'gtins_verified': summary_data.get('gtins_verified', 0),
                        'gtins_matched': summary_data.get('gtins_matched', 0)
                    }
                else:
                    order['validation_summary'] = {
                        'has_validation': False
                    }

    return render_template('dashboard.html',
                         orders_data=orders_data,
                         selected_date=selected_date,
                         username='Amin',
                         fetch_all=fetch_all)

@app.route('/api/orders')
def api_orders():
    date = request.args.get('date')
    fetch_all = request.args.get('all', 'true').lower() == 'true'

    orders_data = locus_auth.get_orders(
        BEARER_TOKEN,
        'illa-frontdoor',
        date=date,
        fetch_all=fetch_all
    )

    return jsonify(orders_data or {'error': 'Failed to fetch orders'})

@app.route('/order/<order_id>')
def order_detail(order_id):
    """View detailed order information"""
    date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))

    # Fetch detailed order information using the new endpoint
    order_detail_data = locus_auth.get_order_detail(
        BEARER_TOKEN,
        'illa-frontdoor',
        order_id
    )

    if not order_detail_data:
        flash(f'Order {order_id} not found or failed to load', 'error')
        return redirect(url_for('dashboard'))

    return render_template('order_detail.html',
                         order=order_detail_data,
                         order_id=order_id,
                         date=date)

@app.route('/validate-order/<order_id>', methods=['POST'])
def validate_single_order(order_id):
    """Validate a single order against its GRN document"""
    try:
        # Get order detail
        order_detail_data = locus_auth.get_order_detail(
            BEARER_TOKEN,
            'illa-frontdoor',
            order_id
        )

        if not order_detail_data:
            return jsonify({
                'success': False,
                'error': f'Order {order_id} not found'
            })

        # Get GRN document URL - try multiple possible paths
        grn_url = None

        # Try different possible paths where the GRN might be stored
        possible_paths = [
            # Direct path
            ['orderMetadata', 'customerProofOfCompletion', 'Proof Of Delivery Document', 'Proof Of Delivery Document'],
            ['orderMetadata', 'customerProofOfCompletion', 'proofOfDeliveryDocument'],
            ['orderMetadata', 'customerProofOfCompletion', 'deliveryDocument'],
            # Alternative paths
            ['proofOfDelivery', 'document'],
            ['proofOfDelivery', 'documentUrl'],
            ['proofOfDelivery', 'deliveryDocument'],
            ['customerProofOfCompletion', 'deliveryDocument'],
            ['customerProofOfCompletion', 'document'],
        ]

        # Debug: Log the available proof keys
        proof_data = order_detail_data.get('orderMetadata', {}).get('customerProofOfCompletion', {})
        logger.info(f"Available proof keys for order {order_id}: {list(proof_data.keys())}")

        # Try each possible path
        for path in possible_paths:
            current_data = order_detail_data
            try:
                for key in path:
                    current_data = current_data[key]
                if isinstance(current_data, str) and current_data.startswith('http'):
                    grn_url = current_data
                    logger.info(f"Found GRN URL at path {' -> '.join(path)}: {grn_url}")
                    break
            except (KeyError, TypeError):
                continue

        # If still no URL, try to find any URL in the proof data
        if not grn_url and proof_data:
            def find_urls_recursive(obj, path=""):
                urls = []
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        new_path = f"{path}.{key}" if path else key
                        if isinstance(value, str) and value.startswith('http'):
                            urls.append((new_path, value))
                        elif isinstance(value, (dict, list)):
                            urls.extend(find_urls_recursive(value, new_path))
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        new_path = f"{path}[{i}]"
                        urls.extend(find_urls_recursive(item, new_path))
                return urls

            found_urls = find_urls_recursive(proof_data)
            logger.info(f"Found URLs in proof data: {found_urls}")

            if found_urls:
                grn_url = found_urls[0][1]  # Take the first URL found
                logger.info(f"Using first found URL: {grn_url}")

        if not grn_url:
            # Enhanced error message with available data structure
            return jsonify({
                'success': False,
                'error': 'No GRN document URL found for this order',
                'debug_info': {
                    'available_proof_keys': list(proof_data.keys()) if proof_data else [],
                    'orderMetadata_keys': list(order_detail_data.get('orderMetadata', {}).keys())
                }
            })

        # Check if there's a stored validation result for this order and GRN
        stored_result = ai_validator.get_stored_validation_result(order_id, grn_url)

        # If force reprocess is requested, skip stored result
        force_reprocess = False
        try:
            if request.is_json:
                json_data = request.get_json(silent=True)  # Don't raise exception on invalid JSON
                if json_data:
                    force_reprocess = json_data.get('force_reprocess', False)
            elif request.form:
                force_reprocess = request.form.get('force_reprocess', 'false').lower() == 'true'
        except Exception as e:
            logger.warning(f"Error parsing force_reprocess parameter: {e}")
            force_reprocess = False

        logger.info(f"Force reprocess requested: {force_reprocess} for order {order_id}")

        if stored_result and not force_reprocess:
            logger.info(f"Returning stored validation result for order {order_id}")

            # Parse stored data properly
            try:
                extracted_items = json.loads(stored_result.get('extracted_items', '[]')) if isinstance(stored_result.get('extracted_items'), str) else stored_result.get('extracted_items', [])
                discrepancies = json.loads(stored_result.get('discrepancies', '[]')) if isinstance(stored_result.get('discrepancies'), str) else stored_result.get('discrepancies', [])
                summary = json.loads(stored_result.get('summary', '{}')) if isinstance(stored_result.get('summary'), str) else stored_result.get('summary', {})
                gtin_verification = json.loads(stored_result.get('gtin_verification', '[]')) if isinstance(stored_result.get('gtin_verification'), str) else stored_result.get('gtin_verification', [])
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing stored validation data: {e}")
                extracted_items, discrepancies, summary, gtin_verification = [], [], {}, []

            # Determine validation result
            has_document = stored_result.get('has_document', True)  # Default to True for backward compatibility
            is_valid = stored_result.get('is_valid', False)

            if not has_document:
                validation_result = 'NO_DOCUMENT'
            elif is_valid:
                validation_result = 'VALID'
            else:
                validation_result = 'INVALID'

            return jsonify({
                'success': True,
                'is_valid': is_valid,
                'validation_data': {
                    'has_document': has_document,
                    'validation_result': validation_result,
                    'confidence_score': stored_result.get('confidence_score', 0),
                    'extracted_items': extracted_items,
                    'discrepancies': discrepancies,
                    'summary': summary,
                    'gtin_verification': gtin_verification
                },
                'confidence_score': stored_result.get('confidence_score', 0),
                'discrepancies': discrepancies,
                'summary': summary,
                'gtin_verification': gtin_verification,
                'cached': True,
                'validation_date': stored_result.get('validation_date'),
                'processing_time': stored_result.get('processing_time', 0)
            })

        # If no stored result or force reprocess, validate using Google AI
        logger.info(f"Processing new validation for order {order_id}")
        logger.info(f"Using GRN URL: {grn_url}")

        try:
            validation_result = ai_validator.validate_grn_against_order(order_detail_data, grn_url)
            logger.info(f"Validation completed for order {order_id}, success: {validation_result.get('success', False)}")
            return jsonify(validation_result)
        except Exception as e:
            logger.error(f"Exception during validation for order {order_id}: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Validation exception: {str(e)}',
                'is_valid': False
            })

    except Exception as e:
        logger.error(f"Error validating order {order_id}: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception details: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

def validate_single_order_worker(order_basic, date, force_reprocess=False):
    """Worker function to validate a single order in a thread"""
    try:
        order_id = order_basic.get('id')
        if not order_id:
            return {
                'order_id': 'unknown',
                'success': False,
                'error': 'No order ID found',
                'is_valid': False
            }

        # Get detailed order data
        order_detail_data = locus_auth.get_order_detail(
            BEARER_TOKEN,
            'illa-frontdoor',
            order_id
        )

        if not order_detail_data:
            return {
                'order_id': order_id,
                'success': False,
                'error': 'Could not fetch order details',
                'is_valid': False
            }

        # Get GRN document URL
        grn_url = None
        if (order_detail_data.get('orderMetadata', {}).get('customerProofOfCompletion', {}).get('Proof Of Delivery Document')):
            grn_url = order_detail_data['orderMetadata']['customerProofOfCompletion']['Proof Of Delivery Document']['Proof Of Delivery Document']

        if not grn_url:
            return {
                'order_id': order_id,
                'success': False,
                'error': 'No GRN document found',
                'is_valid': False
            }

        # Check for existing validation result to avoid unnecessary API calls
        if not force_reprocess:
            stored_result = ai_validator.get_stored_validation_result(order_id, grn_url)
            if stored_result:
                logger.info(f"Using stored validation result for order {order_id}")
                stored_result['order_id'] = order_id
                stored_result['from_cache'] = True
                return stored_result

        # Validate using Google AI with rate limiting (only if not cached or forced reprocess)
        logger.info(f"Calling Google AI API for order {order_id}")

        # Apply rate limiting and concurrency control
        with api_rate_limiter:  # Limit concurrent API calls
            rate_limit_api_call()  # Apply time-based rate limiting
            validation_result = ai_validator.validate_grn_against_order(order_detail_data, grn_url)

        validation_result['order_id'] = order_id
        validation_result['from_cache'] = False
        return validation_result

    except Exception as e:
        logger.error(f"Error validating order {order_basic.get('id', 'unknown')} in worker thread: {e}")
        return {
            'order_id': order_basic.get('id', 'unknown'),
            'success': False,
            'error': str(e),
            'is_valid': False,
            'from_cache': False
        }

@app.route('/validate-all-orders', methods=['POST'])
def validate_all_orders():
    """Validate all orders for today against their GRN documents using parallel processing with cost optimization"""
    try:
        date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))

        # Get parameters from request
        max_workers = 20
        validate_mode = 'unvalidated_only'  # Default to cost-effective mode
        force_reprocess = False

        try:
            if request.is_json:
                json_data = request.get_json(silent=True)
                if json_data:
                    max_workers = min(max(int(json_data.get('max_workers', 20)), 1), 50)  # Cap between 1-50
                    validate_mode = json_data.get('validate_mode', 'unvalidated_only')  # 'all' or 'unvalidated_only'
                    force_reprocess = json_data.get('force_reprocess', False)
        except Exception:
            pass  # Use defaults

        logger.info(f"Starting batch validation with {max_workers} threads, mode: {validate_mode}")

        # Get all orders
        orders_data = locus_auth.get_orders(
            BEARER_TOKEN,
            'illa-frontdoor',
            date=date,
            fetch_all=True
        )

        if not orders_data or not orders_data.get('orders'):
            return jsonify({
                'success': False,
                'error': 'No orders found'
            })

        all_orders = orders_data['orders']

        # Filter orders based on validation mode to minimize API costs
        orders_to_validate = []
        if validate_mode == 'unvalidated_only':
            logger.info("Filtering to only unvalidated orders to minimize API costs...")
            for order in all_orders:
                order_id = order.get('id')
                if order_id:
                    # Quick check for stored validation result
                    stored_result = ai_validator.get_stored_validation_result(order_id)
                    if not stored_result or force_reprocess:
                        orders_to_validate.append(order)
        else:
            orders_to_validate = all_orders

        total_orders = len(all_orders)
        orders_to_process = len(orders_to_validate)

        logger.info(f"Total orders: {total_orders}, Orders to validate: {orders_to_process}")

        if orders_to_process == 0:
            return jsonify({
                'success': True,
                'message': 'All orders already validated - no API calls needed!',
                'total_orders': total_orders,
                'processed': 0,
                'errors': 0,
                'skipped': total_orders,
                'results': [],
                'api_calls_saved': total_orders,
                'threads_used': 0
            })

        validation_results = []
        processed = 0
        errors = 0
        progress_lock = threading.Lock()

        # Use ThreadPoolExecutor for parallel processing with rate limiting
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit validation tasks only for orders that need validation
            future_to_order = {
                executor.submit(validate_single_order_worker, order, date, force_reprocess): order
                for order in orders_to_validate
            }

            # Collect results as they complete
            for future in as_completed(future_to_order):
                order = future_to_order[future]
                try:
                    result = future.result()
                    with progress_lock:
                        validation_results.append(result)
                        if result.get('success', False):
                            processed += 1
                        else:
                            errors += 1

                        # Log progress every 10 completions
                        total_completed = processed + errors
                        if total_completed % 10 == 0 or total_completed == orders_to_process:
                            logger.info(f"Progress: {total_completed}/{orders_to_process} orders completed")

                except Exception as e:
                    with progress_lock:
                        logger.error(f"Error processing future for order {order.get('id', 'unknown')}: {e}")
                        validation_results.append({
                            'order_id': order.get('id', 'unknown'),
                            'success': False,
                            'error': f'Thread execution error: {str(e)}',
                            'is_valid': False
                        })
                        errors += 1

        # Count API calls made vs cached results
        api_calls_made = sum(1 for result in validation_results if not result.get('from_cache', False))
        cached_results = sum(1 for result in validation_results if result.get('from_cache', False))
        skipped_orders = total_orders - orders_to_process

        logger.info(f"Batch validation completed: {processed} processed, {errors} errors")
        logger.info(f"API optimization: {api_calls_made} API calls made, {cached_results} from cache, {skipped_orders} skipped")

        return jsonify({
            'success': True,
            'total_orders': total_orders,
            'processed': processed,
            'errors': errors,
            'skipped': skipped_orders,
            'results': validation_results,
            'threads_used': max_workers,
            'api_calls_made': api_calls_made,
            'cached_results': cached_results,
            'validate_mode': validate_mode
        })

    except Exception as e:
        logger.error(f"Error validating all orders: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

# API endpoints for testing compatibility
@app.route('/api/login', methods=['POST'])
def api_login():
    """API endpoint for login - returns session info"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'Username and password required'
            }), 400

        # For this demo, we'll use a simple validation
        # In production, this would validate against actual user database
        if username and password:
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'username': username,
                    'role': 'user'
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid credentials'
            }), 401

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server error'
        }), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Web login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username and password:
            session['user'] = username
            flash('Login successful', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/api/orders/validation', methods=['POST'])
def api_order_validation():
    """API endpoint for order validation workflow"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')

        if not order_id:
            return jsonify({
                'success': False,
                'error': 'Order ID required'
            }), 400

        # Get order validation result
        validation_result = ai_validator.get_stored_validation_result(order_id)

        if validation_result:
            return jsonify({
                'success': True,
                'order_id': order_id,
                'validation': validation_result
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Order validation not found'
            }), 404

    except Exception as e:
        logger.error(f"Order validation API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/image/grn-analysis', methods=['POST'])
def api_image_grn_analysis():
    """API endpoint for GRN image analysis"""
    try:
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No image file provided'
            }), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No image file selected'
            }), 400

        # Process the image for GRN analysis
        from PIL import Image
        import io

        # Read image data
        image_data = file.read()
        image = Image.open(io.BytesIO(image_data))

        # For demo purposes, return mock analysis result
        analysis_result = {
            'success': True,
            'image_size': image.size,
            'format': image.format,
            'extracted_data': {
                'grn_number': 'GRN-2025-001',
                'items_detected': 5,
                'confidence_score': 0.85
            },
            'processing_time': '0.5s'
        }

        return jsonify(analysis_result), 200

    except ImportError:
        return jsonify({
            'success': False,
            'error': 'PIL module not available'
        }), 500
    except Exception as e:
        logger.error(f"Image analysis error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/data/export', methods=['GET'])
def api_data_export():
    """API endpoint for data export functionality"""
    try:
        export_format = request.args.get('format', 'json')
        date_filter = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))

        # Get orders for the specified date
        orders_data = locus_auth.get_orders(
            BEARER_TOKEN,
            'illa-frontdoor',
            date=date_filter,
            fetch_all=True
        )

        if not orders_data or not orders_data.get('orders'):
            return jsonify({
                'success': False,
                'error': 'No data to export'
            }), 200

        export_data = {
            'export_date': datetime.now().isoformat(),
            'filter_date': date_filter,
            'format': export_format,
            'total_orders': len(orders_data['orders']),
            'orders': orders_data['orders']
        }

        if export_format.lower() == 'csv':
            # For CSV format, return appropriate headers
            response = jsonify(export_data)
            response.headers['Content-Type'] = 'application/json'
            response.headers['Content-Disposition'] = f'attachment; filename=orders_{date_filter}.json'
            return response

        return jsonify(export_data), 200

    except Exception as e:
        logger.error(f"Data export error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Removed logout route - no authentication needed

if __name__ == '__main__':
    print("Starting Locus Assistant...")

    # Initialize database
    if not init_db_connection():
        print("Warning: Database initialization failed. Some features may not work correctly.")

    # Register additional routes (Tours and Heatmap)
    try:
        from app.routes import register_routes
        from app.config import DevelopmentConfig
        config = DevelopmentConfig()
        register_routes(app, config)
        print("Successfully registered Tours and Heatmap routes")
    except Exception as e:
        print(f"Warning: Could not register additional routes: {e}")

    app.run(debug=True, host='0.0.0.0', port=8080)
