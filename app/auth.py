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

    def cache_orders_to_database(self, orders_data, client_id, date_str, cache_key_suffix="ALL"):
        """Cache orders data to database"""
        try:
            order_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            # Get orders from the response - our format uses 'orders' key after processing API 'content'
            orders = orders_data.get('orders', [])

            if not orders:
                logger.info("No orders data to cache")
                return

            logger.info(f"Caching {len(orders)} orders to database for date {date_str} (cache key: {cache_key_suffix})")

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

                        # Extract location data (defensive programming)
                        location = order_data.get('location')
                        if location and isinstance(location, dict):
                            order.location_name = location.get('name')
                            address = location.get('address')
                            if address and isinstance(address, dict):
                                order.location_address = address.get('formattedAddress')
                                order.location_city = address.get('city')
                                order.location_country_code = address.get('countryCode')

                        # Extract tour/delivery data (defensive programming)
                        order_metadata = order_data.get('orderMetadata')
                        if order_metadata and isinstance(order_metadata, dict):
                            tour_detail = order_metadata.get('tourDetail')
                            if tour_detail and isinstance(tour_detail, dict):
                                order.rider_name = tour_detail.get('riderName')
                                order.vehicle_registration = tour_detail.get('vehicleRegistrationNumber')

                            # Extract completion data
                            completion_time = order_metadata.get('homebaseCompleteOn')
                            if completion_time:
                                try:
                                    order.completed_on = datetime.fromisoformat(completion_time.replace('Z', '+00:00'))
                                except:
                                    pass

                        db.session.add(order)

                        # Cache line items (defensive programming)
                        if order_metadata and isinstance(order_metadata, dict):
                            line_items = order_metadata.get('lineItems')
                            if line_items and isinstance(line_items, list):
                                for item_data in line_items:
                                    if item_data and isinstance(item_data, dict):
                                        # Safe extraction with defensive programming
                                        transaction_status_obj = item_data.get('transactionStatus')
                                        transacted_quantity = 0
                                        transaction_status_str = ''

                                        if transaction_status_obj and isinstance(transaction_status_obj, dict):
                                            transacted_quantity = transaction_status_obj.get('transactedQuantity', 0)
                                            transaction_status_str = transaction_status_obj.get('status', '')

                                        line_item = OrderLineItem(
                                            order_id=order_id,
                                            sku_id=item_data.get('id', ''),
                                            name=item_data.get('name', ''),
                                            quantity=item_data.get('quantity', 0),
                                            quantity_unit=item_data.get('quantityUnit', ''),
                                            transacted_quantity=transacted_quantity,
                                            transaction_status=transaction_status_str
                                        )
                                        db.session.add(line_item)

                except Exception as e:
                    order_id_for_error = order_data.get('id', 'unknown') if isinstance(order_data, dict) else 'invalid_data'
                    logger.error(f"Error caching order {order_id_for_error}: {e}")
                    logger.debug(f"Problematic order data keys: {list(order_data.keys()) if isinstance(order_data, dict) else 'not a dict'}")
                    continue

            # Only commit if we have a valid db session
            try:
                db.session.commit()
                logger.info(f"Successfully cached {len(orders)} orders to database")
            except Exception as commit_error:
                logger.warning(f"Could not commit to database: {commit_error}")

        except Exception as e:
            logger.error(f"Error caching orders to database: {e}")
            try:
                db.session.rollback()
            except:
                pass  # In case there's no valid session

    def clear_orders_cache(self, client_id, date_str):
        """Clear cached orders from database for a specific date"""
        try:
            from models import OrderLineItem
            order_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            # First, find all orders for this date and client
            orders_to_delete = Order.query.filter_by(client_id=client_id, date=order_date).all()
            order_ids = [order.id for order in orders_to_delete]

            if not order_ids:
                logger.info(f"No orders found to clear for date {date_str}")
                return True

            # Delete related OrderLineItems first to avoid foreign key constraints
            line_items_deleted = OrderLineItem.query.filter(OrderLineItem.order_id.in_(order_ids)).delete(synchronize_session=False)

            # Then delete the orders
            orders_deleted = Order.query.filter_by(client_id=client_id, date=order_date).delete()

            db.session.commit()
            logger.info(f"Cleared {orders_deleted} cached orders and {line_items_deleted} line items for date {date_str}")
            return True
        except Exception as e:
            logger.error(f"Error clearing orders cache: {e}")
            db.session.rollback()
            return False

    def get_orders_from_database(self, client_id, date_str, cache_key_suffix="ALL"):
        """Get cached orders from database"""
        try:
            order_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            # For now, we'll return all cached orders and let the calling code filter
            # In the future, we could enhance this to store cache keys per status combination
            orders = Order.query.filter_by(client_id=client_id, date=order_date).all()

            if not orders:
                return None

            logger.info(f"Found {len(orders)} cached orders for date {date_str} (cache key: {cache_key_suffix})")

            # Convert to API format
            orders_data = []
            status_totals = {}

            for order in orders:
                try:
                    order_dict = json.loads(order.raw_data) if order.raw_data else {}

                    # If specific statuses requested, filter the cached data
                    if cache_key_suffix != "ALL":
                        requested_statuses = cache_key_suffix.split("_")
                        if order_dict.get('orderStatus') not in requested_statuses:
                            continue

                    orders_data.append(order_dict)

                    # Calculate status totals
                    status = order_dict.get('orderStatus', 'UNKNOWN')
                    status_totals[status] = status_totals.get(status, 0) + 1

                except:
                    logger.error(f"Error parsing cached order data for {order.id}")
                    continue

            # If after filtering we have no orders, return None to force fresh fetch
            if not orders_data and cache_key_suffix != "ALL":
                return None

            return {
                "orders": orders_data,
                "totalCount": len(orders_data),
                "cached": True,
                "statusTotals": status_totals,
                "requestedStatuses": cache_key_suffix.split("_") if cache_key_suffix != "ALL" else None
            }

        except Exception as e:
            logger.error(f"Error getting cached orders: {e}")
            return None

    def refresh_orders_force_fresh(self, access_token, client_id="illa-frontdoor", team_id="101", date=None, fetch_all=True):
        """Force refresh orders by clearing cache and fetching fresh data from API - like viewing a new date."""
        try:
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")

            logger.info(f"REFRESH: Clearing cache and fetching fresh orders for {date}...")

            # Step 1: Clear existing cache for this date
            self.clear_orders_cache(client_id, date)

            # Step 2: Fetch fresh data from API (same logic as normal get_orders but force API)
            fresh_orders_data = self._fetch_orders_from_api(access_token, client_id, team_id, date, fetch_all)

            if not fresh_orders_data or not fresh_orders_data.get('orders'):
                logger.warning("No fresh orders received from API during refresh")
                return {'orders': [], 'totalCount': 0, 'new_orders_count': 0}

            # Step 3: Cache the fresh data to database
            self.cache_orders_to_database(fresh_orders_data, client_id, date)

            logger.info(f"REFRESH: Successfully fetched {len(fresh_orders_data['orders'])} fresh orders from API and cached them")

            return {
                'orders': fresh_orders_data['orders'],
                'totalCount': fresh_orders_data.get('totalCount', len(fresh_orders_data['orders'])),
                'cached': False,
                'new_orders_count': fresh_orders_data.get('totalCount', len(fresh_orders_data['orders']))  # All are "new" since we cleared cache
            }

        except Exception as e:
            logger.error(f"Error during force refresh: {e}")
            # If refresh fails, try to return any existing data
            return self.get_orders_from_database(client_id, date) or {'orders': [], 'totalCount': 0, 'new_orders_count': 0}

    def _fetch_orders_from_api(self, access_token, client_id, team_id, date, fetch_all):
        """Internal method to fetch orders directly from API (no caching)"""
        logger.info(f"Fetching orders from API for date: {date}")

        if fetch_all:
            return self._fetch_all_orders_from_api(access_token, client_id, team_id, date)
        else:
            return self._fetch_single_page_from_api(access_token, client_id, team_id, date)

    def _fetch_all_orders_from_api(self, access_token, client_id, team_id, date):
        """Fetch all pages of orders from API"""
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

        logger.info(f"REFRESH API: Fetching from {url} for date range {date} to {next_date}")

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
                ]
            }

            logger.info(f"REFRESH API: Making request to page {page_num} with payload: {payload}")
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            logger.info(f"REFRESH API: Page {page_num} response - content length: {len(result.get('content', []))}, totalElements: {result.get('totalElements', 0)}")
            return result

        # Fetch all pages
        page = 1
        all_orders = []

        while True:
            logger.info(f"REFRESH API: Fetching page {page}...")
            page_data = get_page(page)

            orders = page_data.get('content', [])
            total_elements = page_data.get('totalElements', 0)

            if not orders:
                logger.info(f"REFRESH API: No orders found on page {page} (totalElements: {total_elements})")
                break

            all_orders.extend(orders)
            logger.info(f"REFRESH API: Page {page}: {len(orders)} orders (Total so far: {len(all_orders)})")

            # Check if there are more pages
            if len(orders) < 50:  # Less than page size means last page
                break
            page += 1

        logger.info(f"REFRESH API: Fetched total {len(all_orders)} orders from {page} pages")

        return {
            "orders": all_orders,
            "totalCount": len(all_orders)
        }

    def _fetch_single_page_from_api(self, access_token, client_id, team_id, date):
        """Fetch single page of orders from API"""
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

        payload = {
            "page": 1,
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
            ]
        }

        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        page_data = response.json()

        return {
            "orders": page_data.get('content', []),
            "totalCount": page_data.get('totalElements', 0)
        }

    def get_orders(self, access_token, client_id="illa-frontdoor", team_id="101", date=None, fetch_all=False, force_refresh=False, order_statuses=None):
        """Fetch orders data - can fetch all pages or single page. Uses database caching.

        Args:
            order_statuses: List of statuses to filter by, or None for all statuses
                          e.g., ["COMPLETED"] or ["EXECUTING", "ASSIGNED"] or None for all
        """
        try:
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")

            # Create a cache key that includes order statuses for proper caching
            cache_key_suffix = "_".join(sorted(order_statuses)) if order_statuses else "ALL"

            # If force_refresh is False, try to get from database cache first
            if not force_refresh:
                cached_orders = self.get_orders_from_database(client_id, date, cache_key_suffix)
                if cached_orders:
                    logger.info(f"Returning {len(cached_orders['orders'])} cached orders for {date} (statuses: {cache_key_suffix})")
                    return cached_orders

            # If no cached data OR force_refresh=True, fetch from API
            if force_refresh:
                logger.info(f"FORCE REFRESH: Fetching fresh data from API for {date} (statuses: {cache_key_suffix})")
            else:
                logger.info(f"No cached orders found for {date} (statuses: {cache_key_suffix}). Fetching from API...")

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
                # Base filters (team and date)
                filters = [
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
                ]

                # Add order status filter only if specific statuses are requested
                if order_statuses:
                    filters.append({
                        "name": "orderStatus",
                        "operation": "EQUALS",
                        "value": None,
                        "values": order_statuses,
                        "allowEmptyOrNull": False,
                        "caseSensitive": False
                    })

                payload = {
                    "page": page_num,
                    "size": 50,
                    "sortingInfo": [],
                    "filters": filters,
                    "complexFilters": None
                }

                logger.debug(f"Making API request to {url}")
                logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
                response = requests.post(url, headers=headers, json=payload)
                logger.info(f"API response status: {response.status_code}")
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"API response keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
                    if isinstance(result, dict):
                        # Check actual API response structure
                        orders_length = len(result.get('orders', []))
                        content_length = len(result.get('content', []))
                        total_elements = result.get('totalElements', 0)
                        pagination_info = result.get('paginationInfo', {})
                        logger.info(f"Orders length: {orders_length}, Content length: {content_length}, Total elements: {total_elements}")
                        logger.info(f"Pagination info: {pagination_info}")
                    return result
                else:
                    logger.error(f"API request failed with status {response.status_code}: {response.text}")
                return None

            if not fetch_all:
                # Return single page
                page_data = get_page(1)
                if page_data:
                    # Convert API response format to our expected format
                    orders = page_data.get('orders', [])
                    pagination_info = page_data.get('paginationInfo', {})
                    response_data = {
                        "orders": orders,
                        "totalCount": len(orders),  # For single page, count the orders we got
                        "pagesFetched": 1,
                        "paginationInfo": pagination_info
                    }
                    # Cache the fetched data (skip if no app context for debug/testing)
                    try:
                        self.cache_orders_to_database(response_data, client_id, date, cache_key_suffix)
                    except Exception as cache_error:
                        logger.warning(f"Skipping single page caching due to error: {cache_error}")
                    return response_data
                return None

            # Fetch all pages
            all_orders = []
            page = 1
            total_fetched = 0

            status_msg = f"all statuses" if not order_statuses else ", ".join(order_statuses)
            logger.info(f"Starting to fetch all orders for date: {date} (statuses: {status_msg})")

            while True:
                logger.info(f"Fetching page {page}...")
                page_data = get_page(page)

                if not page_data:
                    logger.info(f"No response data at page {page}")
                    break

                # API returns orders in 'orders' key (based on actual API response)
                orders_in_page_data = page_data.get('orders', [])
                pagination_info = page_data.get('paginationInfo', {})

                orders_in_page = len(orders_in_page_data)

                if orders_in_page == 0:
                    logger.info(f"No orders found at page {page} (paginationInfo: {pagination_info})")
                    logger.debug(f"Page data keys: {list(page_data.keys()) if isinstance(page_data, dict) else 'not a dict'}")
                    break

                all_orders.extend(orders_in_page_data)
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

            logger.info(f"Total orders fetched: {total_fetched} (statuses: {status_msg})")

            # Calculate status totals
            status_totals = {}
            if all_orders:
                for order in all_orders:
                    status = order.get('orderStatus', 'UNKNOWN')
                    status_totals[status] = status_totals.get(status, 0) + 1

            # Create response data
            response_data = {
                "orders": all_orders,
                "totalCount": total_fetched,
                "pagesFetched": page - 1,
                "statusTotals": status_totals,
                "requestedStatuses": order_statuses
            }

            # Cache the fetched data (skip if no app context for debug/testing)
            if all_orders:
                try:
                    self.cache_orders_to_database(response_data, client_id, date, cache_key_suffix)
                except Exception as cache_error:
                    logger.warning(f"Skipping caching due to error: {cache_error}")

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

    def refresh_orders_smart_merge(self, access_token, client_id="illa-frontdoor", team_id="101", date=None, fetch_all=True, order_statuses=None):
        """Smart refresh: fetches fresh data and merges with database without deleting existing records"""
        try:
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")

            cache_key_suffix = "_".join(sorted(order_statuses)) if order_statuses else "ALL"
            status_msg = f"all statuses" if not order_statuses else ", ".join(order_statuses)
            logger.info(f"SMART REFRESH: Fetching fresh data from API for {date} (statuses: {status_msg})")

            # Step 1: Fetch fresh data from API using force_refresh=True
            fresh_orders_data = self.get_orders(access_token, client_id, team_id, date, fetch_all, force_refresh=True, order_statuses=order_statuses)

            if fresh_orders_data and fresh_orders_data.get('orders'):
                # Step 2: Smart merge - this will update existing records or add new ones
                self.smart_merge_orders_to_database(fresh_orders_data, client_id, date)
                logger.info(f"SMART REFRESH: Successfully merged {len(fresh_orders_data['orders'])} orders from API with database")

                # Return merged data from database
                return self.get_orders_from_database(client_id, date, cache_key_suffix)
            else:
                logger.warning("No fresh orders received from API during smart refresh")
                # Return existing database data
                return self.get_orders_from_database(client_id, date, cache_key_suffix) or {'orders': [], 'totalCount': 0}

        except Exception as e:
            logger.error(f"Error during smart refresh: {e}")
            # Return existing database data as fallback
            return self.get_orders_from_database(client_id, date, cache_key_suffix) or {'orders': [], 'totalCount': 0}

    def smart_merge_orders_to_database(self, orders_data, client_id, date_str):
        """Merge orders to database - update existing, add new ones"""
        try:
            from models import OrderLineItem

            order_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            orders = orders_data.get('orders', [])

            updated_count = 0
            added_count = 0

            for order_data in orders:
                order_id = order_data.get('id')
                if not order_id:
                    continue

                # Check if order already exists
                existing_order = Order.query.filter_by(id=order_id).first()

                if existing_order:
                    # Update existing order - only update if data has changed
                    new_raw_data = json.dumps(order_data)
                    if existing_order.raw_data != new_raw_data:
                        existing_order.raw_data = new_raw_data
                        existing_order.order_status = order_data.get('orderStatus', '')
                        # Update other fields as needed
                        location = order_data.get('location', {})
                        current_tour = order_data.get('currentTour', {})

                        existing_order.location_name = location.get('name', '')
                        existing_order.location_address = location.get('address', '')
                        existing_order.location_city = location.get('city', '')
                        existing_order.location_country_code = location.get('countryCode', '')
                        existing_order.rider_name = current_tour.get('riderName', '')
                        existing_order.vehicle_registration = current_tour.get('vehicleRegistration', '')

                        if order_data.get('completedOn'):
                            try:
                                existing_order.completed_on = datetime.fromisoformat(order_data['completedOn'].replace('Z', '+00:00'))
                            except:
                                pass

                        updated_count += 1
                        logger.info(f"Updated existing order: {order_id}")
                else:
                    # Add new order
                    self._create_new_order_record(order_data, client_id, order_date)
                    added_count += 1
                    logger.info(f"Added new order: {order_id}")

            db.session.commit()
            logger.info(f"Smart merge completed: {updated_count} updated, {added_count} added")
            return True

        except Exception as e:
            logger.error(f"Error in smart merge: {e}")
            db.session.rollback()
            return False

    def _create_new_order_record(self, order_data, client_id, order_date):
        """Helper method to create a new order record"""
        from models import OrderLineItem

        order_id = order_data.get('id')

        # Extract order information
        order_status = order_data.get('orderStatus', '')
        location = order_data.get('location', {})
        current_tour = order_data.get('currentTour', {})

        completed_on = None
        if order_data.get('completedOn'):
            try:
                completed_on = datetime.fromisoformat(order_data['completedOn'].replace('Z', '+00:00'))
            except:
                pass

        # Create order
        order = Order(
            id=order_id,
            client_id=client_id,
            date=order_date,
            order_status=order_status,
            location_name=location.get('name', ''),
            location_address=location.get('address', ''),
            location_city=location.get('city', ''),
            location_country_code=location.get('countryCode', ''),
            rider_name=current_tour.get('riderName', ''),
            vehicle_registration=current_tour.get('vehicleRegistration', ''),
            completed_on=completed_on,
            raw_data=json.dumps(order_data)
        )

        db.session.add(order)

        # Add line items if they exist
        line_items = order_data.get('lineItems', [])
        for item in line_items:
            line_item = OrderLineItem(
                order_id=order_id,
                sku_id=item.get('skuId', ''),
                name=item.get('name', ''),
                quantity=item.get('quantity', 0),
                quantity_unit=item.get('quantityUnit', ''),
                transacted_quantity=item.get('transactedQuantity'),
                transaction_status=item.get('transactionStatus', '')
            )
            db.session.add(line_item)