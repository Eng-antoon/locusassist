#!/usr/bin/env python3

import requests
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import Config

def test_live_updates_endpoint():
    """Test the live updates endpoint directly to understand the response structure"""

    config = Config()

    url = "https://dash.locus-api.com/v1/client/illa-frontdoor/task-search?include=FLEET%2CLOCATION%2CCROSSDOCK&countsOnly=false&pageSize=50"
    headers = {
        "accept": "application/json",
        "accept-language": "en-US,en;q=0.9",
        "authorization": f"Bearer {config.BEARER_TOKEN}",
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

    # Test multiple scenarios
    test_cases = [
        {
            "name": "Page 1 with skipPaginationInfo=False",
            "payload": {
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
        },
        {
            "name": "Page 2 with skipPaginationInfo=False",
            "payload": {
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
                "page": 2,
                "skipPaginationInfo": False
            }
        },
        {
            "name": "Page 5 with skipPaginationInfo=False",
            "payload": {
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
                "page": 5,
                "skipPaginationInfo": False
            }
        }
    ]

    print("=" * 80)
    print("TESTING LIVE UPDATES ENDPOINT")
    print("=" * 80)

    for test_case in test_cases:
        print(f"\n🧪 {test_case['name']}")
        print("-" * 60)

        try:
            print(f"Request URL: {url}")
            print(f"Request Payload: {json.dumps(test_case['payload'], indent=2)}")

            response = requests.post(url, headers=headers, json=test_case['payload'])

            print(f"Response Status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()

                # Analyze the response structure
                print(f"Response Keys: {list(result.keys())}")

                tasks = result.get('tasks', [])
                print(f"Tasks Count: {len(tasks)}")

                # Check pagination info
                pagination_fields = ['numberOfPages', 'totalElements', 'currentPage', 'pageSize', 'totalPages', 'hasNext', 'hasPrevious']
                print("Pagination Info:")
                for field in pagination_fields:
                    if field in result:
                        print(f"  {field}: {result[field]}")

                # Show first few task IDs
                if tasks:
                    task_ids = [task.get('id', 'no-id') for task in tasks[:5]]
                    print(f"First 5 Task IDs: {task_ids}")

                    # Show structure of first task
                    print("First Task Keys:")
                    if tasks[0]:
                        print(f"  {list(tasks[0].keys())}")

                # Check if there are any other interesting fields
                other_fields = [k for k in result.keys() if k not in ['tasks'] + pagination_fields]
                if other_fields:
                    print(f"Other Fields: {other_fields}")
                    for field in other_fields:
                        print(f"  {field}: {result[field]}")

            else:
                print(f"Error Response: {response.text}")

        except Exception as e:
            print(f"Exception: {e}")

        print()

if __name__ == "__main__":
    test_live_updates_endpoint()