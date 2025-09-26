#!/usr/bin/env python3
"""
Test raw task API data to look for location coordinates that might not be extracted
"""

import requests
import json
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def search_nested_dict(data, search_terms, path=""):
    """Recursively search nested dictionary for keys containing search terms"""
    results = []

    if isinstance(data, dict):
        for key, value in data.items():
            new_path = f"{path}.{key}" if path else key

            # Check if key contains any search terms
            key_lower = key.lower()
            for term in search_terms:
                if term in key_lower:
                    results.append({
                        'path': new_path,
                        'key': key,
                        'value': value,
                        'type': type(value).__name__
                    })
                    break

            # Recursively search nested structures
            if isinstance(value, (dict, list)):
                results.extend(search_nested_dict(value, search_terms, new_path))

    elif isinstance(data, list):
        for i, item in enumerate(data):
            new_path = f"{path}[{i}]"
            results.extend(search_nested_dict(item, search_terms, new_path))

    return results

def test_raw_task_coordinates():
    """Test raw task API data to find coordinate information"""
    try:
        # Your provided access token
        access_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ik4wRTNNa1l3TlVGQk1EQkZOREEzTVRVMFEwSTJSRGxCUkRFelFqa3pOVFl4TWpZMlJUUkNNUSJ9.eyJsb2N1cy1hdHRyaWJ1dGVzIjp7ImN1c3RvbVZhbHVlcyI6eyJkYXRhQ2xpZW50SWQiOiJpbGxhLWZyb250ZG9vciJ9LCJwZXJzb25uZWxJZCI6ImlsbGEtZnJvbnRkb29yL3BlcnNvbm5lbC9BbWluIn0sImlzcyI6Imh0dHBzOi8vYWNjb3VudHMubG9jdXMtZGFzaGJvYXJkLmNvbS8iLCJzdWIiOiJhdXRoMHxwZXJzb25uZWxzfGlsbGEtZnJvbnRkb29yL3BlcnNvbm5lbC9BbWluIiwiYXVkIjpbImh0dHBzOi8vYXdzLXVzLWVhc3QtMS5sb2N1cy1hcGkuY29tIiwiaHR0cHM6Ly9sb2N1cy1hd3MtdXMtZWFzdC0xLmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NTg4MzA2NTIsImV4cCI6MTc1ODg3Mzg1Miwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6IkNMMm1sYnJMZ2Z3N2RTOGFkcDV4MzE5aXVQT0pySlZlIn0.jNIJoulmMmvfbS8R0_1NvF-kXlzmWtCBxbCJTAXPU0HE3b7q7Qwr5digjW58L5a3Ry8rNjNam3YaIvzhcV-itmcCmbI1LuuCBwPjNEMJwBMAVI6asiqGm0l2buX1k5roJsh7nK3b0HpY3ZTZqxurWO8CiO6dzNcYrPqUvYYCkBOkx_VSnaSD9ABQ0PZYb28wAB-EY2puB3itNAuB3PTAbjsI90fS7A55nJ1VcmFZFx9-xsQBVtusDAQyr4tICCRyzl-0FKeNl_e0_ytlboIrHIbe-76eHVgxSJdoxwYlLXSVEOjBwPbB3oRbfELEsoB7l3cFdbY34eX_Iskh9A3hjg"

        url = "https://dash.locus-api.com/v1/client/illa-frontdoor/task-search?include=FLEET%2CLOCATION%2CCROSSDOCK&countsOnly=false&pageSize=10"

        headers = {
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': f'Bearer {access_token}',
            'content-type': 'application/json',
            'l-custom-user-agent': 'cerebro'
        }

        # Use yesterday's date
        yesterday = datetime.now() - timedelta(days=1)
        date = yesterday.strftime("%Y-%m-%d")

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
                    "value": date,
                    "values": [],
                    "allowEmptyOrNull": False,
                    "caseSensitive": False
                }
            ],
            "complexFilters": None,
            "sortingInfo": None,
            "size": 10,
            "page": 1,
            "skipPaginationInfo": False
        }

        logger.info("🔍 Testing raw task API for coordinate information...")
        logger.info(f"📅 Date: {date}")
        logger.info(f"URL: {url}")

        # Make the request
        response = requests.post(url, headers=headers, json=payload)
        logger.info(f"Response status: {response.status_code}")

        if response.status_code != 200:
            logger.error(f"❌ Request failed: {response.text}")
            return False

        # Parse response
        data = response.json()
        tasks = data.get('tasks', [])
        logger.info(f"📦 Found {len(tasks)} tasks to analyze")

        if not tasks:
            logger.warning("⚠️ No tasks found in response")
            return True

        # Search terms related to coordinates and location
        coordinate_terms = [
            'lat', 'lng', 'latitude', 'longitude', 'coord', 'geo', 'position',
            'point', 'location', 'address', 'chosen', 'geometry'
        ]

        # Analyze first few tasks
        for i, task in enumerate(tasks[:3], 1):
            logger.info(f"\n🔍 TASK {i} COORDINATE ANALYSIS")
            logger.info("=" * 50)
            logger.info(f"Task ID: {task.get('id')}")
            logger.info(f"Effective Status: {task.get('effectiveStatus')}")

            # Search for coordinate-related fields in the entire task structure
            coordinate_findings = search_nested_dict(task, coordinate_terms)

            if coordinate_findings:
                logger.info(f"🗺️ Found {len(coordinate_findings)} coordinate-related fields:")
                for finding in coordinate_findings:
                    logger.info(f"   📍 {finding['path']}")
                    logger.info(f"      Key: {finding['key']}")
                    logger.info(f"      Type: {finding['type']}")

                    # Show value if it's not too complex
                    if finding['type'] in ['str', 'int', 'float', 'bool']:
                        logger.info(f"      Value: {finding['value']}")
                    elif finding['type'] == 'dict' and len(str(finding['value'])) < 200:
                        logger.info(f"      Value: {finding['value']}")
                    elif finding['type'] == 'list' and len(finding['value']) < 5:
                        logger.info(f"      Value: {finding['value']}")
                    else:
                        logger.info(f"      Value: [Complex {finding['type']} - {len(str(finding['value']))} chars]")
                    logger.info("")
            else:
                logger.info("❌ No coordinate-related fields found in task structure")

            # Special focus on location-related structures
            logger.info(f"\n🏢 LOCATION STRUCTURES ANALYSIS:")

            # Check customerVisit.location
            customer_visit = task.get('customerVisit', {})
            if customer_visit:
                logger.info(f"   Customer Visit keys: {list(customer_visit.keys())}")

                # location field
                location = customer_visit.get('location', {})
                if location:
                    logger.info(f"   📍 Location structure: {list(location.keys())}")
                    if isinstance(location, dict):
                        logger.info(f"      Location details: {json.dumps(location, indent=6)[:500]}...")

                # chosenLocation field
                chosen_location = customer_visit.get('chosenLocation', {})
                if chosen_location:
                    logger.info(f"   📍 Chosen Location structure: {list(chosen_location.keys())}")
                    if isinstance(chosen_location, dict):
                        logger.info(f"      Chosen Location details: {json.dumps(chosen_location, indent=6)[:500]}...")

                # locationId field
                location_id = customer_visit.get('locationId', {})
                if location_id:
                    logger.info(f"   📍 Location ID structure: {list(location_id.keys())}")
                    if isinstance(location_id, dict):
                        logger.info(f"      Location ID details: {json.dumps(location_id, indent=6)[:500]}...")

            # Check task-level location fields
            task_location_fields = {k: v for k, v in task.items() if 'location' in k.lower()}
            if task_location_fields:
                logger.info(f"   📍 Task-level location fields: {list(task_location_fields.keys())}")
                for k, v in task_location_fields.items():
                    if isinstance(v, dict) and len(str(v)) < 300:
                        logger.info(f"      {k}: {v}")
                    else:
                        logger.info(f"      {k}: [Complex structure]")

        logger.info(f"\n✅ Raw task coordinate analysis completed!")
        return True

    except Exception as e:
        logger.error(f"❌ Error during raw task coordinate analysis: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == '__main__':
    print("=" * 70)
    print("🔍 RAW TASK API COORDINATE ANALYSIS")
    print("=" * 70)

    success = test_raw_task_coordinates()
    if success:
        print("\n🎉 Raw task coordinate analysis completed!")
    else:
        print("\n❌ Raw task coordinate analysis failed!")