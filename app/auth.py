import requests
import json
import logging
from datetime import datetime, timedelta
from models import Order, OrderLineItem, db

logger = logging.getLogger(__name__)

class LocusAuth:
    def __init__(self, config=None):
        if config:
            self.base_url = config.LOCUS_BASE_URL
            self.auth_url = config.LOCUS_AUTH_URL
            self.api_url = config.LOCUS_API_URL
        else:
            # Fallback to hardcoded values
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