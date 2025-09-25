#!/usr/bin/env python3
"""
Simple test script to verify Google AI API connection
"""
import requests
import json

# Your API key
API_KEY = "AIzaSyAj4Y69sbfXSNKHHSu0YOot2R9kLOmFhQI"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"

def test_google_ai_api():
    """Test basic Google AI API connection"""
    print("Testing Google AI API connection...")
    print(f"API Key: {API_KEY[:10]}...")
    print(f"API URL: {API_URL}")

    # Simple test payload
    payload = {
        "contents": [{
            "parts": [{"text": "Hello, can you respond with 'API is working'?"}]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "topK": 1,
            "topP": 1.0,
            "maxOutputTokens": 50
        }
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        print("\nSending request...")
        response = requests.post(
            f"{API_URL}?key={API_KEY}",
            headers=headers,
            json=payload,
            timeout=30
        )

        print(f"Response Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Content Length: {len(response.content)}")

        if response.status_code == 200:
            try:
                result = response.json()
                print(f"Response JSON: {json.dumps(result, indent=2)}")
                print("✅ API Test PASSED!")
            except json.JSONDecodeError as e:
                print(f"❌ Failed to decode JSON response: {e}")
                print(f"Raw response: {response.text[:1000]}")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Error response: {response.text[:1000]}")

    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except requests.exceptions.ConnectionError:
        print("❌ Connection error")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_google_ai_api()