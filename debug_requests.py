
import requests
import os

BASE_URL = "http://127.0.0.1:8080"

def test_url(path):
    url = f"{BASE_URL}{path}"
    try:
        print(f"Testing {url}...")
        r = requests.get(url, allow_redirects=True)
        print(f"Status: {r.status_code}")
        print(f"Type: {r.headers.get('content-type')}")
        print(f"Len: {len(r.content)}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_url("/static/img/no_thumb.png")
    test_url("/thumb/99999999") # Should redirect
