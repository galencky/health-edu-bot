#!/usr/bin/env python3
"""Test script to verify container environment"""

import sys
import os

print("=== Container Environment Test ===")
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")
print(f"Files in directory: {os.listdir('.')}")
print(f"Environment PORT: {os.getenv('PORT', 'not set')}")

# Test imports
try:
    import fastapi
    print("✓ FastAPI imported successfully")
except Exception as e:
    print(f"✗ FastAPI import failed: {e}")

try:
    import uvicorn
    print("✓ Uvicorn imported successfully")
except Exception as e:
    print(f"✗ Uvicorn import failed: {e}")

try:
    from main import app
    print("✓ Main app imported successfully")
except Exception as e:
    print(f"✗ Main app import failed: {e}")

print("\n=== Test Complete ===")