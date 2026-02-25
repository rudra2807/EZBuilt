#!/usr/bin/env python3
"""Test the aws-connections endpoint directly"""
import asyncio
import sys
sys.path.insert(0, '.')

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

print("Testing /api/user/test-user/aws-connections endpoint...")
response = client.get("/api/user/test-user/aws-connections")
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")

print("\nAll registered routes:")
for route in app.routes:
    if hasattr(route, 'path'):
        print(f"  {route.methods if hasattr(route, 'methods') else 'N/A'} {route.path}")
