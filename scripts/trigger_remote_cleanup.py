"""Trigger one-time cleanup on live Railway backend."""
import httpx
import time

URL = "https://backendscraper-production.up.railway.app/prospects/export/cleanup-no-phone"

print(f"Calling {URL}...")
try:
    res = httpx.post(URL, timeout=60.0)
    print(f"HTTP Status: {res.status_code}")
    print(f"Response: {res.text}")
except Exception as exc:
    print(f"Request error: {exc}")
