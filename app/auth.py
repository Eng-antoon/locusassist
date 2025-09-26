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

                    # Check if order already exists and update or create accordingly
                    existing_order = Order.query.filter_by(id=order_id).first()
                    if existing_order:
                        # Update existing order using data protection service
                        self._update_existing_order_record(existing_order, order_data, client_id, order_date)
                    else:
                        # Create new order
                        self._create_new_order_record(order_data, client_id, order_date)

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
        """Fetch all pages of orders from task-search API"""
        url = f"{self.base_url}/v1/client/{client_id}/task-search?include=FLEET%2CLOCATION%2CCROSSDOCK&countsOnly=false&pageSize=50"
        headers = {
            "accept": "application/json",
            "accept-language": "en-US,en;q=0.9",
            "authorization": f"Bearer {access_token}",
            "content-type": "application/json",
            "l-custom-user-agent": "cerebro",
            "priority": "u=1, i",
            "sec-ch-ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Google Chrome\";v=\"138\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Linux\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site"
        }

        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        logger.info(f"REFRESH API: Fetching from task-search {url} for date {date}")

        def get_page(page_num):
            payload = {
                "filters": [
                    {
                        "name": "teamId.teamId",
                        "operation": "EQUALS",
                        "value": None,
                        "values": [team_id],
                        "allowEmptyOrNull": False,
                        "caseSensitive": False
                    },
                    {
                        "name": "date",
                        "operation": "EQUALS",
                        "value": date,
                        "values": [],
                        "allowEmptyOrNull": False,
                        "caseSensitive": False
                    }
                ],
                "complexFilters": None,
                "sortingInfo": None,
                "size": 50,
                "page": page_num,
                "skipPaginationInfo": False
            }

            logger.info(f"REFRESH API: Making request to page {page_num} with payload: {payload}")
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            tasks = result.get('tasks', [])
            logger.info(f"REFRESH API: Page {page_num} response - tasks length: {len(tasks)}")
            return result

        # Fetch all pages
        page = 1
        all_tasks = []
        consecutive_empty_pages = 0

        while page <= 20 and consecutive_empty_pages < 3:  # Stop after 3 consecutive empty pages
            logger.info(f"REFRESH API: Fetching page {page}...")
            page_data = get_page(page)

            tasks = page_data.get('tasks', [])

            if not tasks:
                logger.info(f"REFRESH API: No tasks found on page {page}")
                consecutive_empty_pages += 1
                page += 1
                continue

            consecutive_empty_pages = 0
            all_tasks.extend(tasks)
            logger.info(f"REFRESH API: Page {page}: {len(tasks)} tasks (Total so far: {len(all_tasks)})")

            if len(tasks) < 50:  # Less than page size means last page
                break
            page += 1

        logger.info(f"REFRESH API: Fetched total {len(all_tasks)} tasks from {page-1} pages")

        # Convert tasks to order format
        all_orders = []
        for task in all_tasks:
            order = self._extract_order_from_task(task)
            if order:
                all_orders.append(order)

        logger.info(f"REFRESH API: Converted {len(all_orders)} tasks to order format")

        return {
            "orders": all_orders,
            "totalCount": len(all_orders)
        }

    def _fetch_single_page_from_api(self, access_token, client_id, team_id, date):
        """Fetch single page of orders from task-search API"""
        url = f"{self.base_url}/v1/client/{client_id}/task-search?include=FLEET%2CLOCATION%2CCROSSDOCK&countsOnly=false&pageSize=50"
        headers = {
            "accept": "application/json",
            "accept-language": "en-US,en;q=0.9",
            "authorization": f"Bearer {access_token}",
            "content-type": "application/json",
            "l-custom-user-agent": "cerebro",
            "priority": "u=1, i",
            "sec-ch-ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Google Chrome\";v=\"138\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Linux\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site"
        }

        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        payload = {
            "filters": [
                {
                    "name": "teamId.teamId",
                    "operation": "EQUALS",
                    "value": None,
                    "values": [team_id],
                    "allowEmptyOrNull": False,
                    "caseSensitive": False
                },
                {
                    "name": "date",
                    "operation": "EQUALS",
                    "value": date,
                    "values": [],
                    "allowEmptyOrNull": False,
                    "caseSensitive": False
                }
            ],
            "complexFilters": None,
            "sortingInfo": None,
            "size": 50,
            "page": 1,
            "skipPaginationInfo": False
        }

        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        page_data = response.json()

        tasks = page_data.get('tasks', [])

        # Convert tasks to order format
        orders = []
        for task in tasks:
            order = self._extract_order_from_task(task)
            if order:
                orders.append(order)

        return {
            "orders": orders,
            "totalCount": len(orders)
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

            url = f"{self.base_url}/v1/client/{client_id}/task-search?include=FLEET%2CLOCATION%2CCROSSDOCK&countsOnly=false&pageSize=50"
            headers = {
                "accept": "application/json",
                "accept-language": "en-US,en;q=0.9",
                "authorization": f"Bearer {access_token}",
                "content-type": "application/json",
                "l-custom-user-agent": "cerebro",
                "priority": "u=1, i",
                "sec-ch-ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Google Chrome\";v=\"138\"",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "\"Linux\"",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "cross-site"
            }

            if not date:
                date = datetime.now().strftime("%Y-%m-%d")

            def get_page(page_num):
                # Base filters (team and date) for task-search
                filters = [
                    {
                        "name": "teamId.teamId",
                        "operation": "EQUALS",
                        "value": None,
                        "values": [team_id],
                        "allowEmptyOrNull": False,
                        "caseSensitive": False
                    },
                    {
                        "name": "date",
                        "operation": "EQUALS",
                        "value": date,
                        "values": [],
                        "allowEmptyOrNull": False,
                        "caseSensitive": False
                    }
                ]

                # Note: task-search doesn't filter by orderStatus like order-search does
                # Instead, we'll get all tasks and filter by effectiveStatus if needed

                payload = {
                    "filters": filters,
                    "complexFilters": None,
                    "sortingInfo": None,
                    "size": 50,
                    "page": page_num,
                    "skipPaginationInfo": False
                }

                logger.debug(f"Making API request to {url}")
                logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
                response = requests.post(url, headers=headers, json=payload)
                logger.info(f"API response status: {response.status_code}")
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"API response keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
                    if isinstance(result, dict):
                        # Check task-search API response structure
                        tasks_length = len(result.get('tasks', []))
                        pagination_info = result.get('paginationInfo', {})
                        total_elements = pagination_info.get('total', 0)
                        number_of_pages = pagination_info.get('numberOfPages', 1)
                        current_page = pagination_info.get('currentPage', page_num)
                        logger.info(f"Tasks length: {tasks_length}, Total elements: {total_elements}, Number of pages: {number_of_pages}, Current page: {current_page}")

                    # Convert tasks to orders format
                    tasks = result.get('tasks', [])
                    orders = []
                    for task in tasks:
                        order = self._extract_order_from_task(task)
                        if order:
                            # Filter by order status if requested
                            if order_statuses:
                                if order.get('orderStatus') in order_statuses:
                                    orders.append(order)
                            else:
                                orders.append(order)

                    # Update result to match expected format
                    result['orders'] = orders
                    result['paginationInfo'] = {
                        'total': total_elements,
                        'totalElements': total_elements,  # Keep both for compatibility
                        'numberOfPages': number_of_pages,
                        'currentPage': current_page
                    }
                    logger.info(f"Converted {len(orders)} tasks to orders (filtered from {tasks_length} tasks)")
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

            # Fetch first page to get numberOfPages info
            logger.info(f"ORDER SEARCH: Fetching first page to get pagination info...")
            first_page_data = get_page(1)

            if not first_page_data:
                logger.error("ORDER SEARCH: Failed to fetch first page")
                return None

            all_orders = first_page_data.get('orders', [])
            pagination_info = first_page_data.get('paginationInfo', {})
            number_of_pages = pagination_info.get('numberOfPages', 1)
            total_elements = pagination_info.get('total', pagination_info.get('totalElements', len(all_orders)))

            status_msg = f"all statuses" if not order_statuses else ", ".join(order_statuses)
            logger.info(f"ORDER SEARCH: Starting to fetch all orders for date: {date} (statuses: {status_msg})")
            logger.info(f"ORDER SEARCH: First page fetched: {len(all_orders)} orders")
            logger.info(f"ORDER SEARCH: Total pages to fetch: {number_of_pages}, Total elements: {total_elements}")

            # Fetch remaining pages if there are more than 1 page
            if number_of_pages and number_of_pages > 1:
                for page_num in range(2, number_of_pages + 1):
                    logger.info(f"ORDER SEARCH: Fetching page {page_num} of {number_of_pages}...")
                    page_data = get_page(page_num)

                    if page_data:
                        orders_in_page_data = page_data.get('orders', [])
                        if orders_in_page_data:
                            all_orders.extend(orders_in_page_data)
                            logger.info(f"ORDER SEARCH: Page {page_num}: Added {len(orders_in_page_data)} orders (Total so far: {len(all_orders)})")
                        else:
                            logger.warning(f"ORDER SEARCH: No orders found in page {page_num}")
                    else:
                        logger.warning(f"ORDER SEARCH: Failed to fetch page {page_num}")
                        break

            total_fetched = len(all_orders)

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
                "pagesFetched": number_of_pages or 1,
                "statusTotals": status_totals,
                "requestedStatuses": order_statuses,
                "totalElements": total_elements
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

    def get_task_detail(self, access_token, client_id, task_id):
        """Fetch detailed task information by task ID - provides richer data than order endpoint"""
        try:
            url = f"{self.api_url}/v1/client/{client_id}/task/{task_id}"
            headers = {
                "accept": "application/json",
                "authorization": f"Bearer {access_token}",
                "l-custom-user-agent": "cerebro",
            }

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error fetching task detail {task_id}: HTTP {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting task detail {task_id}: {e}")
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
                logger.info(f"SMART REFRESH: Successfully merged {len(fresh_orders_data['orders'])} orders to database")

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
        """Merge orders to database with data protection - update existing (respecting isModified flags), add new ones"""
        try:
            from app.data_protection import data_protection_service

            order_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            orders = orders_data.get('orders', [])

            updated_count = 0
            added_count = 0
            protected_count = 0

            logger.info(f"SMART MERGE: Processing {len(orders)} orders for {date_str}")

            for order_data in orders:
                order_id = order_data.get('id')
                if not order_id:
                    continue

                # Check if order already exists
                existing_order = Order.query.filter_by(id=order_id).first()

                if existing_order:
                    # Check if this order has been manually modified
                    if existing_order.is_modified:
                        protected_fields = data_protection_service.get_protected_fields(existing_order)
                        logger.info(f"PROTECTED ORDER: {order_id} has {len(protected_fields)} protected fields: {protected_fields}")
                        protected_count += 1

                    # Use data protection service to safely update
                    data_protection_service.safe_update_order(existing_order, order_data, client_id, order_date)
                    updated_count += 1
                    logger.debug(f"Updated existing order: {order_id}")
                else:
                    # Add new order
                    self._create_new_order_record(order_data, client_id, order_date)
                    added_count += 1
                    logger.debug(f"Added new order: {order_id}")

            db.session.commit()
            logger.info(f"SMART MERGE COMPLETE: {updated_count} updated, {added_count} added, {protected_count} had protected fields")

            # Log protection summary for monitoring
            if protected_count > 0:
                logger.info(f"DATA PROTECTION: Successfully protected {protected_count} manually modified orders from API overwrites")

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

        # Create order instance
        order = Order(
            id=order_id,
            client_id=client_id,
            date=order_date,
            order_status=order_status,
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

            # Extract coordinates if available
            latLng = location.get('latLng', {})
            if latLng and isinstance(latLng, dict):
                lat = latLng.get('lat') or latLng.get('latitude')
                lng = latLng.get('lng') or latLng.get('longitude')
                logger.info(f"[COORDINATES] Creating new order {order_id}: lat={lat}, lng={lng}")
                if lat is not None:
                    try:
                        order.location_latitude = float(lat)
                        logger.info(f"[COORDINATES] Successfully set latitude {lat} for new order {order_id}")
                    except (ValueError, TypeError):
                        logger.warning(f"[COORDINATES] Invalid latitude value for new order {order_id}: {lat}")
                if lng is not None:
                    try:
                        order.location_longitude = float(lng)
                        logger.info(f"[COORDINATES] Successfully set longitude {lng} for new order {order_id}")
                    except (ValueError, TypeError):
                        logger.warning(f"[COORDINATES] Invalid longitude value for new order {order_id}: {lng}")
            else:
                logger.warning(f"[COORDINATES] No latLng data found for new order {order_id}")

        # Extract tour/delivery data (defensive programming)
        order_metadata = order_data.get('orderMetadata')
        if order_metadata and isinstance(order_metadata, dict):
            tour_detail = order_metadata.get('tourDetail')
            if tour_detail and isinstance(tour_detail, dict):
                order.rider_name = tour_detail.get('riderName')
                order.vehicle_registration = tour_detail.get('vehicleRegistrationNumber')

                # Extract tour data
                tour_id = tour_detail.get('tourId')
                if tour_id:
                    from models import Tour
                    order.tour_id = tour_id

                    # Parse tour ID components
                    tour_date, plan_id, tour_name, tour_number = Tour.parse_tour_id(tour_id)
                    if tour_date:
                        order.tour_date = tour_date
                        order.tour_plan_id = plan_id
                        order.tour_name = tour_name
                        order.tour_number = tour_number or 0

            # Extract completion data
            completion_time = order_metadata.get('homebaseCompleteOn')
            if completion_time:
                try:
                    order.completed_on = datetime.fromisoformat(completion_time.replace('Z', '+00:00'))
                except:
                    pass

        # Extract enhanced data from task-search
        if 'rider_id' in order_data:
            order.rider_id = order_data.get('rider_id')
        if 'rider_phone' in order_data:
            order.rider_phone = order_data.get('rider_phone')
        if 'vehicle_id' in order_data:
            order.vehicle_id = order_data.get('vehicle_id')
        if 'vehicle_model' in order_data:
            order.vehicle_model = order_data.get('vehicle_model')
        if 'transporter_name' in order_data:
            order.transporter_name = order_data.get('transporter_name')

        # Task-specific data
        if 'task_source' in order_data:
            order.task_source = order_data.get('task_source')
        if 'plan_id' in order_data:
            order.plan_id = order_data.get('plan_id')
        if 'planned_tour_name' in order_data:
            order.planned_tour_name = order_data.get('planned_tour_name')
        if 'sequence_in_batch' in order_data:
            order.sequence_in_batch = order_data.get('sequence_in_batch')
        if 'partially_delivered' in order_data:
            order.partially_delivered = order_data.get('partially_delivered')
        if 'reassigned' in order_data:
            order.reassigned = order_data.get('reassigned')
        if 'rejected' in order_data:
            order.rejected = order_data.get('rejected')
        if 'unassigned' in order_data:
            order.unassigned = order_data.get('unassigned')

        # Performance metrics
        if 'tardiness' in order_data:
            order.tardiness = order_data.get('tardiness')
        if 'sla_status' in order_data:
            order.sla_status = order_data.get('sla_status')
        if 'amount_collected' in order_data:
            order.amount_collected = order_data.get('amount_collected')
        if 'effective_tat' in order_data:
            order.effective_tat = order_data.get('effective_tat')
        if 'allowed_dwell_time' in order_data:
            order.allowed_dwell_time = order_data.get('allowed_dwell_time')

        # Time tracking
        if 'eta_updated_on' in order_data and order_data.get('eta_updated_on'):
            try:
                order.eta_updated_on = datetime.fromisoformat(order_data['eta_updated_on'].replace('Z', '+00:00'))
            except:
                pass
        if 'tour_updated_on' in order_data and order_data.get('tour_updated_on'):
            try:
                order.tour_updated_on = datetime.fromisoformat(order_data['tour_updated_on'].replace('Z', '+00:00'))
            except:
                pass
        if 'initial_assignment_at' in order_data and order_data.get('initial_assignment_at'):
            try:
                order.initial_assignment_at = datetime.fromisoformat(order_data['initial_assignment_at'].replace('Z', '+00:00'))
            except:
                pass
        if 'initial_assignment_by' in order_data:
            assignment_by = order_data.get('initial_assignment_by')
            order.initial_assignment_by = json.dumps(assignment_by) if isinstance(assignment_by, dict) else assignment_by

        # Additional metadata
        if 'task_time_slot' in order_data:
            order.task_time_slot = order_data.get('task_time_slot')
        if 'skills' in order_data:
            order.skills = json.dumps(order_data.get('skills', []))
        if 'tags' in order_data:
            order.tags = json.dumps(order_data.get('tags', []))
        if 'custom_fields' in order_data:
            order.custom_fields = json.dumps(order_data.get('custom_fields', {}))
        if 'cancellation_reason' in order_data:
            order.cancellation_reason = order_data.get('cancellation_reason')

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

    def _update_existing_order_record(self, existing_order, order_data, client_id, order_date):
        """Helper method to update an existing order record with data protection"""
        from app.data_protection import data_protection_service

        # Use the data protection service to safely update the order
        data_protection_service.safe_update_order(existing_order, order_data, client_id, order_date)

    def _extract_order_from_task(self, task):
        """Extract order data from task data format"""
        try:
            if not task:
                return None

            # Get basic task info
            task_id = task.get('id')
            if not task_id:
                return None

            # Get customer visit data which contains order information
            customer_visit = task.get('customerVisit', {})
            if not customer_visit:
                return None

            # Extract order detail from customer visit
            order_detail = customer_visit.get('orderDetail', {})

            # Get status information - prioritize effective status from task level
            effective_status = task.get('effectiveStatus', 'UNKNOWN')
            task_status = task.get('status', {})

            # Use task effective status as order status without mapping
            order_status = effective_status

            # Get location data
            location = customer_visit.get('location', {})
            location_name = location.get('name', '')
            location_address = ''
            location_city = ''
            location_country_code = ''

            address = location.get('address', {})
            if address:
                location_address = address.get('formattedAddress', '')
                location_city = address.get('city', '')
                location_country_code = address.get('countryCode', '')

            # Extract coordinates from location.latLng for the order structure
            location_lat_lng = {}
            latLng = location.get('latLng', {})
            if latLng and isinstance(latLng, dict):
                lat = latLng.get('lat')
                lng = latLng.get('lng')
                if lat is not None and lng is not None:
                    location_lat_lng = {
                        'lat': lat,
                        'lng': lng,
                        'accuracy': latLng.get('accuracy', 0)
                    }

            # Get tour information from task
            tour_id = ''
            tour_metadata = task.get('tourId')
            if tour_metadata:
                if isinstance(tour_metadata, dict):
                    tour_id = tour_metadata.get('tourId', '')
                else:
                    tour_id = str(tour_metadata)

            # Get fleet/rider information
            fleet_info = task.get('fleetInfo', {})
            rider_name = ''
            rider_id = ''
            rider_phone = ''
            vehicle_registration = ''
            vehicle_id = ''
            vehicle_model = ''
            transporter_name = ''

            if fleet_info:
                # Rider information
                rider = fleet_info.get('rider', {})
                if rider:
                    rider_name = rider.get('name', '')
                    rider_id = rider.get('id', '')
                    phone_info = rider.get('phoneNumber', {})
                    if phone_info:
                        rider_phone = phone_info.get('phoneNumber', '')

                # Vehicle information
                vehicle = fleet_info.get('vehicle', {})
                if vehicle:
                    vehicle_id = vehicle.get('id', '')
                    vehicle_registration = vehicle.get('registrationNumber', '')

                vehicle_model_info = fleet_info.get('vehicleModel', {})
                if vehicle_model_info:
                    vehicle_model = vehicle_model_info.get('name', '')

                # Transporter information
                transporter = fleet_info.get('transporter', {})
                if transporter:
                    transporter_name = transporter.get('name', '')

            # Get line items from order detail
            line_items = order_detail.get('lineItems', [])

            # Process line items to match expected format
            processed_line_items = []
            for item in line_items:
                transaction_status = item.get('transactionStatus', {})
                processed_item = {
                    'skuId': item.get('id', ''),  # Use skuId instead of id to match expected format
                    'name': item.get('name', ''),
                    'quantity': item.get('quantity', 0),
                    'quantityUnit': item.get('quantityUnit', ''),
                    'transactedQuantity': transaction_status.get('transactedQuantity', 0),
                    'transactionStatus': transaction_status.get('status', '')
                }
                processed_line_items.append(processed_item)

            # Get task-specific data
            task_source = task.get('taskSource', '')

            # Handle planId which can be string or dict
            plan_id_data = task.get('planId', '')
            if isinstance(plan_id_data, dict):
                plan_id = plan_id_data.get('planId', '')
            else:
                plan_id = str(plan_id_data) if plan_id_data else ''

            planned_tour_name = task.get('plannedTourName', '')
            sequence_in_batch = task.get('sequenceInBatch', 0)
            partially_delivered = task.get('partiallyDelivered', False)
            reassigned = task.get('reassigned', False)
            rejected = task.get('rejected', False)
            unassigned = task.get('unassigned', False)

            # Get performance metrics
            task_summary = task.get('summary', {})
            customer_summary = customer_visit.get('summary', {})

            tardiness = task_summary.get('tardiness', 0) or customer_summary.get('tardiness', 0)
            sla_status = task_summary.get('slaStatus', '') or customer_summary.get('slaStatus', '')

            amount_collected = 0
            if 'amountCollected' in customer_summary:
                amount_info = customer_summary.get('amountCollected', {})
                if isinstance(amount_info, dict):
                    amount_collected = amount_info.get('amount', 0)

            effective_tat = customer_summary.get('effectiveTat', 0)
            allowed_dwell_time = customer_summary.get('allowedDwellTime', 0)

            # Get time tracking data
            eta_updated_on = task.get('etaUpdatedOn', '')
            tour_updated_on = task.get('tourUpdatedOn', '')
            initial_assignment_at = task.get('initialAssignmentAt', '')
            initial_assignment_by = task.get('initialAssignmentBy', '')

            # Get additional metadata
            task_time_slot = task.get('taskTimeSlotAsString', '')
            skills = task.get('skills', [])
            tags = task.get('tags', [])
            custom_fields = task.get('customFields', {})

            # Extract cancellation reason if order is cancelled
            cancellation_reason = None
            if order_status == 'CANCELLED':
                checklists = customer_visit.get('checklists', {})
                cancelled_checklist = checklists.get('cancelled', {})
                if cancelled_checklist.get('status') == 'CANCELLED':
                    cancelled_items = cancelled_checklist.get('items', [])
                    for item in cancelled_items:
                        if item.get('id') == 'Cancellation-reason':
                            cancellation_reason = item.get('selectedValue')
                            break

            # Create order data structure matching the expected format
            order = {
                'id': task_id,
                'orderStatus': order_status,
                'status': order_status,  # For compatibility
                'date': task.get('date', ''),
                'location': {
                    'name': location_name,
                    'address': {
                        'formattedAddress': location_address,
                        'city': location_city,
                        'countryCode': location_country_code
                    },
                    'latLng': location_lat_lng
                },
                'lineItems': processed_line_items,
                'orderMetadata': {
                    'tourDetail': {
                        'tourId': tour_id,
                        'riderName': rider_name,
                        'vehicleRegistrationNumber': vehicle_registration
                    } if tour_id or rider_name or vehicle_registration else {}
                },
                # Enhanced fleet/rider data
                'rider_id': rider_id,
                'rider_phone': rider_phone,
                'vehicle_id': vehicle_id,
                'vehicle_model': vehicle_model,
                'transporter_name': transporter_name,
                # Task-specific data
                'task_source': task_source,
                'plan_id': plan_id,
                'planned_tour_name': planned_tour_name,
                'sequence_in_batch': sequence_in_batch,
                'partially_delivered': partially_delivered,
                'reassigned': reassigned,
                'rejected': rejected,
                'unassigned': unassigned,
                # Performance metrics
                'tardiness': tardiness,
                'sla_status': sla_status,
                'amount_collected': amount_collected,
                'effective_tat': effective_tat,
                'allowed_dwell_time': allowed_dwell_time,
                # Time tracking
                'eta_updated_on': eta_updated_on,
                'tour_updated_on': tour_updated_on,
                'initial_assignment_at': initial_assignment_at,
                'initial_assignment_by': initial_assignment_by,
                # Additional metadata
                'task_time_slot': task_time_slot,
                'skills': skills,
                'tags': tags,
                'custom_fields': custom_fields,
                # Cancellation information
                'cancellation_reason': cancellation_reason
            }

            # Store completion data if available
            if task_status and task_status.get('triggerTime'):
                try:
                    from datetime import datetime
                    completion_time = task_status.get('triggerTime')
                    order['completed_on'] = completion_time
                except:
                    pass

            logger.debug(f"Extracted order {task_id} with status {effective_status} -> {order_status}")
            return order

        except Exception as e:
            logger.error(f"Error extracting order from task: {e}")
            logger.debug(f"Task data keys: {list(task.keys()) if isinstance(task, dict) else 'not a dict'}")
            return None


