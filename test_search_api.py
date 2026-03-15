
import requests
import json

try:
    # Test api/options
    print("Testing /api/options...")
    response = requests.get("http://127.0.0.1:5000/api/options")
    if response.status_code == 200:
        data = response.json()
        print(f"Success! Fonts: {len(data['fonts'])}, Authors: {len(data['authors'])}, Books: {len(data['books'])}")
    else:
        print(f"Failed to get options: {response.status_code}")

    # Test api/search with a common character like '书' (book) or just empty to see if it works
    print("\nTesting /api/search with han='书'...")
    response = requests.get("http://127.0.0.1:5000/api/search?han=书")
    if response.status_code == 200:
        data = response.json()
        print(f"Success! Total results: {data['total']}")
        if data['results']:
            print(f"First result: {data['results'][0]}")
    else:
        print(f"Failed to search: {response.status_code}")

except Exception as e:
    print(f"Error during test: {e}")
