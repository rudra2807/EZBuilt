#!/usr/bin/env python3
"""Test script to verify routes are loaded"""
import sys
sys.path.insert(0, '.')

from src.apis.routes_connection import router as connection_router

print("Routes in connection_router:")
for route in connection_router.routes:
    print(f"  {route.methods} {route.path}")

print("\nLooking for aws-connections route:")
aws_conn_routes = [r for r in connection_router.routes if 'aws-connections' in r.path]
if aws_conn_routes:
    print(f"  ✓ Found: {aws_conn_routes[0].path}")
else:
    print("  ✗ NOT FOUND")
