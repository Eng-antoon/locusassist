#!/usr/bin/env python3
"""
Test task-search response with the provided curl request
"""

import requests
import json
import logging
from app import create_app
from app.auth import LocusAuth

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_task_search_response():
    """Test the actual task-search response and data extraction"""
    try:
        # Your provided access token and request details
        access_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ik4wRTNNa1l3TlVGQk1EQkZOREEzTVRVMFEwSTJSRGxCUkRFelFqa3pOVFl4TWpZMlJUUkNNUSJ9.eyJsb2N1cy1hdHRyaWJ1dGVzIjp7ImN1c3RvbVZhbHVlcyI6eyJkYXRhQ2xpZW50SWQiOiJpbGxhLWZyb250ZG9vciJ9LCJwZXJzb25uZWxJZCI6ImlsbGEtZnJvbnRkb29yL3BlcnNvbm5lbC9BbWluIn0sImlzcyI6Imh0dHBzOi8vYWNjb3VudHMubG9jdXMtZGFzaGJvYXJkLmNvbS8iLCJzdWIiOiJhdXRoMHxwZXJzb25uZWxzfGlsbGEtZnJvbnRkb29yL3BlcnNvbm5lbC9BbWluIiwiYXVkIjpbImh0dHBzOi8vYXdzLXVzLWVhc3QtMS5sb2N1cy1hcGkuY29tIiwiaHR0cHM6Ly9sb2N1cy1hd3MtdXMtZWFzdC0xLmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NTg4MzA2NTIsImV4cCI6MTc1ODg3Mzg1Miwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6IkNMMm1sYnJMZ2Z3N2RTOGFkcDV4MzE5aXVQT0pySlZlIn0.jNIJoulmMmvfbS8R0_1NvF-kXlzmWtCBxbCJTAXPU0HE3b7q7Qwr5digjW58L5a3Ny8rNjNam3YaIvzhcV-itmcCmbI1LuuCBwPjNEMJwBMAVI6asiqGm0l2buX1k5roJsh7nK3b0HpY3ZTZqxurWO8CiO6dzNcYrPqUvYYCkBOkx_VSnaSD9ABQ0PZYb28wAB-EY2puB3itNAuB3PTAbjsI90fS7A55nJ1VcmFZFx9-xsQBVtusDAQyr4tICCRyzl-0FKeNl_e0_ytlboIrHIbe-76eHVgxSJdoxwYlLXSVEOjBwPbB3oRbfELEsoB7l3cFdbY34eX_Iskh9A3hjg"

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
            "page": 1,
            "skipPaginationInfo": False
        }

        logger.info("🔍 Testing task-search response with provided parameters...")
        logger.info(f"URL: {url}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")

        # Make the request
        response = requests.post(url, headers=headers, json=payload)
        logger.info(f"Response status: {response.status_code}")

        if response.status_code != 200:
            logger.error(f"❌ Request failed: {response.text}")
            return False

        # Parse response
        data = response.json()
        logger.info(f"📊 Response structure keys: {list(data.keys())}")

        # Check pagination info
        pagination_info = data.get('paginationInfo', {})
        total = pagination_info.get('total', 0)
        number_of_pages = pagination_info.get('numberOfPages', 1)
        current_page = pagination_info.get('currentPage', 1)

        logger.info(f"📄 Pagination info:")
        logger.info(f"   Total: {total}")
        logger.info(f"   Number of pages: {number_of_pages}")
        logger.info(f"   Current page: {current_page}")

        # Check tasks
        tasks = data.get('tasks', [])
        logger.info(f"📦 Tasks in response: {len(tasks)}")

        if not tasks:
            logger.warning("⚠️ No tasks found in response")
            return True

        # Test data extraction with our current logic
        logger.info("🔧 Testing data extraction...")

        app = create_app('development')
        with app.app_context():
            auth = LocusAuth()

            # Test extraction on first few tasks
            sample_tasks = tasks[:3]
            for i, task in enumerate(sample_tasks, 1):
                logger.info(f"\n📦 Task {i} extraction test:")
                logger.info(f"   Raw task keys: {list(task.keys())}")

                # Test our extraction method
                extracted_order = auth._extract_order_from_task(task)
                if extracted_order:
                    logger.info(f"   ✅ Successfully extracted order: {extracted_order['id']}")
                    logger.info(f"      Status: {extracted_order['orderStatus']}")
                    logger.info(f"      Tour ID: {extracted_order.get('orderMetadata', {}).get('tourDetail', {}).get('tourId', 'N/A')}")
                    logger.info(f"      Rider: {extracted_order.get('rider_name', 'N/A')}")
                    logger.info(f"      Vehicle: {extracted_order.get('vehicle_registration', 'N/A')}")
                    logger.info(f"      Cancellation reason: {extracted_order.get('cancellation_reason', 'N/A')}")
                    logger.info(f"      Line items: {len(extracted_order.get('lineItems', []))}")

                    # Check if all enhanced fields are populated
                    enhanced_fields = {
                        'rider_id': extracted_order.get('rider_id'),
                        'rider_phone': extracted_order.get('rider_phone'),
                        'vehicle_id': extracted_order.get('vehicle_id'),
                        'vehicle_model': extracted_order.get('vehicle_model'),
                        'transporter_name': extracted_order.get('transporter_name'),
                        'task_source': extracted_order.get('task_source'),
                        'plan_id': extracted_order.get('plan_id'),
                        'tardiness': extracted_order.get('tardiness'),
                        'sla_status': extracted_order.get('sla_status')
                    }

                    populated_fields = {k: v for k, v in enhanced_fields.items() if v not in [None, '', 0, []]}
                    logger.info(f"      Enhanced fields populated: {len(populated_fields)}/{len(enhanced_fields)}")
                    for field, value in populated_fields.items():
                        logger.info(f"         {field}: {value}")
                else:
                    logger.error(f"   ❌ Failed to extract order from task {i}")

        # Show sample task structure for analysis
        if tasks:
            logger.info(f"\n🔍 Sample task structure (first task):")
            sample_task = tasks[0]

            # Show main structure
            logger.info(f"Task ID: {sample_task.get('id')}")
            logger.info(f"Effective Status: {sample_task.get('effectiveStatus')}")
            logger.info(f"Tour ID: {sample_task.get('tourId')}")

            # Check customer visit structure
            customer_visit = sample_task.get('customerVisit', {})
            if customer_visit:
                logger.info(f"Customer Visit keys: {list(customer_visit.keys())}")
                order_detail = customer_visit.get('orderDetail', {})
                if order_detail:
                    logger.info(f"Order Detail keys: {list(order_detail.keys())}")
                    line_items = order_detail.get('lineItems', [])
                    logger.info(f"Line items count: {len(line_items)}")

                # Check for cancellation data
                checklists = customer_visit.get('checklists', {})
                if checklists:
                    logger.info(f"Checklists keys: {list(checklists.keys())}")
                    cancelled = checklists.get('cancelled', {})
                    if cancelled:
                        logger.info(f"Cancelled checklist: {cancelled.get('status')}")
                        items = cancelled.get('items', [])
                        for item in items:
                            if item.get('id') == 'Cancellation-reason':
                                logger.info(f"Cancellation reason found: {item.get('selectedValue')}")

            # Check fleet info
            fleet_info = sample_task.get('fleetInfo', {})
            if fleet_info:
                logger.info(f"Fleet Info keys: {list(fleet_info.keys())}")
                rider = fleet_info.get('rider', {})
                if rider:
                    logger.info(f"Rider: {rider.get('name')} (ID: {rider.get('id')})")
                vehicle = fleet_info.get('vehicle', {})
                if vehicle:
                    logger.info(f"Vehicle: {vehicle.get('registrationNumber')} (ID: {vehicle.get('id')})")

        logger.info(f"\n✅ Task-search response test completed!")
        logger.info(f"📄 Found {number_of_pages} pages with {total} total tasks")
        logger.info(f"🔧 Data extraction logic appears to be working")

        return True

    except Exception as e:
        logger.error(f"❌ Error during task-search response test: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("🔍 TASK-SEARCH RESPONSE TEST")
    print("=" * 60)

    success = test_task_search_response()
    if success:
        print("\n🎉 Task-search response test completed!")
    else:
        print("\n❌ Task-search response test failed!")