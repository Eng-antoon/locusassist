#!/usr/bin/env python3
"""
Test fetching all pages from task-search endpoint
"""

import requests
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_all_pages_fetch():
    """Test fetching all pages from task-search"""
    try:
        # Your provided access token
        access_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ik4wRTNNa1l3TlVGQk1EQkZOREEzTVRVMFEwSTJSRGxCUkRFelFqa3pOVFl4TWpZMlJUUkNNUSJ9.eyJsb2N1cy1hdHRyaWJ1dGVzIjp7ImN1c3RvbVZhbHVlcyI6eyJkYXRhQ2xpZW50SWQiOiJpbGxhLWZyb250ZG9vciJ9LCJwZXJzb25uZWxJZCI6ImlsbGEtZnJvbnRkb29yL3BlcnNvbm5lbC9BbWluIn0sImlzcyI6Imh0dHBzOi8vYWNjb3VudHMubG9jdXMtZGFzaGJvYXJkLmNvbS8iLCJzdWIiOiJhdXRoMHxwZXJzb25uZWxzfGlsbGEtZnJvbnRkb29yL3BlcnNvbm5lbC9BbWluIiwiYXVkIjpbImh0dHBzOi8vYXdzLXVzLWVhc3QtMS5sb2N1cy1hcGkuY29tIiwiaHR0cHM6Ly9sb2N1cy1hd3MtdXMtZWFzdC0xLmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NTg4NzQxMjIsImV4cCI6MTc1ODkxNzMyMiwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6IkNMMm1sYnJMZ2Z3N2RTOGFkcDV4MzE5aXVQT0pySlZlIn0.lZGb9MynHmGDDUsPTT6PMfCosS3Dkzwd6vBEsneW3pn_w4rJjkby-jMSo8ljBrMhc9AypY43bX8Kfs86FZ2j3NNo_lUi9epSur1GyZf11S8GiH_lXlcHk-Kf-a47vimzo-ccmMJ-15UMYK9ekbWRUeg1-2Dbm-ENXkgIT-T58qh9FN7qf7zqOgPOFyLwBdCQLFF7su3Opzm7TTW1VLrt0_CBfczq_bcJ9sdl_iTYCTXlIBIwdeoqTwYXZoW7O9Ndprl9sp__h3_6QLHXnrdtEw8H3vcpeDc-Cke4iZZNvDdq8f3gIwEQVLyEAkrT_hpZfYFYDnc8xy0SQnQhiZ1mJw"

        url = "https://dash.locus-api.com/v1/client/illa-frontdoor/task-search?include=FLEET%2CLOCATION%2CCROSSDOCK&countsOnly=false&pageSize=50"

        headers = {
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': f'Bearer {access_token}',
            'content-type': 'application/json',
            'l-custom-user-agent': 'cerebro',
            'origin': 'https://illa-frontdoor.locus-dashboard.com',
            'priority': 'u=1, i',
            'referer': 'https://illa-frontdoor.locus-dashboard.com/',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
        }

        def get_page(page_num):
            payload = {
                "filters": [
                    {
                        "name": "teamId.teamId",
                        "operation": "EQUALS",
                        "value": None,
                        "values": ["101"],
                        "allowEmptyOrNull": False,
                        "caseSensitive": False
                    },
                    {
                        "name": "date",
                        "operation": "EQUALS",
                        "value": "2025-09-25",
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

            logger.info(f"📄 Fetching page {page_num}...")
            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                data = response.json()
                tasks = data.get('tasks', [])
                pagination_info = data.get('paginationInfo', {})

                logger.info(f"   ✅ Page {page_num}: {len(tasks)} tasks")
                logger.info(f"   📊 Pagination: {pagination_info}")

                return data
            else:
                logger.error(f"   ❌ Page {page_num} failed: {response.status_code}")
                return None

        logger.info("🔍 Testing complete pagination flow...")

        # Step 1: Get first page to determine total pages
        logger.info("📄 Fetching first page to get pagination info...")
        first_page = get_page(1)

        if not first_page:
            logger.error("❌ Failed to fetch first page")
            return False

        pagination_info = first_page.get('paginationInfo', {})
        total = pagination_info.get('total', 0)
        number_of_pages = pagination_info.get('numberOfPages', 1)

        logger.info(f"📊 Total tasks: {total}")
        logger.info(f"📊 Number of pages: {number_of_pages}")

        all_tasks = first_page.get('tasks', [])
        logger.info(f"📦 First page: {len(all_tasks)} tasks")

        # Step 2: Fetch remaining pages
        if number_of_pages > 1:
            logger.info(f"📄 Fetching remaining {number_of_pages - 1} pages...")

            for page_num in range(2, number_of_pages + 1):
                page_data = get_page(page_num)

                if page_data:
                    page_tasks = page_data.get('tasks', [])
                    all_tasks.extend(page_tasks)
                    logger.info(f"   📦 Page {page_num}: Added {len(page_tasks)} tasks (Total: {len(all_tasks)})")
                else:
                    logger.warning(f"   ⚠️ Failed to fetch page {page_num}")

        logger.info(f"\n✅ Complete fetch results:")
        logger.info(f"   📊 Total tasks fetched: {len(all_tasks)}")
        logger.info(f"   📊 Expected total: {total}")
        logger.info(f"   📊 Pages fetched: {number_of_pages}")

        # Test some task data
        if all_tasks:
            # Check for different statuses
            status_counts = {}
            cancelled_with_reasons = 0

            for task in all_tasks:
                status = task.get('effectiveStatus', 'UNKNOWN')
                status_counts[status] = status_counts.get(status, 0) + 1

                # Check cancellation reasons
                if status == 'CANCELLED':
                    customer_visit = task.get('customerVisit', {})
                    checklists = customer_visit.get('checklists', {})
                    cancelled = checklists.get('cancelled', {})
                    if cancelled.get('status') == 'CANCELLED':
                        items = cancelled.get('items', [])
                        for item in items:
                            if item.get('id') == 'Cancellation-reason' and item.get('selectedValue'):
                                cancelled_with_reasons += 1
                                break

            logger.info(f"\n📊 Status distribution:")
            for status, count in status_counts.items():
                logger.info(f"   {status}: {count}")

            logger.info(f"\n🚫 Cancellation data:")
            logger.info(f"   Cancelled orders: {status_counts.get('CANCELLED', 0)}")
            logger.info(f"   With cancellation reasons: {cancelled_with_reasons}")

        success = len(all_tasks) == total
        if success:
            logger.info(f"\n🎉 Successfully fetched all {total} tasks from {number_of_pages} pages!")
        else:
            logger.warning(f"\n⚠️ Expected {total} tasks but got {len(all_tasks)}")

        return success

    except Exception as e:
        logger.error(f"❌ Error during all pages fetch test: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("📄 ALL PAGES FETCH TEST")
    print("=" * 60)

    success = test_all_pages_fetch()
    if success:
        print("\n🎉 All pages fetch test completed successfully!")
        print("📝 Pagination logic working correctly.")
    else:
        print("\n❌ All pages fetch test failed!")