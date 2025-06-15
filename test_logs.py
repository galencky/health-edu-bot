#!/usr/bin/env python3
"""Test script to verify logging works in Container Manager"""
import sys
import time

print("TEST: Starting log test", flush=True)
print("TEST: This should appear in Container Manager", file=sys.stdout, flush=True)
print("TEST: This is stderr", file=sys.stderr, flush=True)

for i in range(5):
    print(f"TEST: Message {i+1}/5", flush=True)
    time.sleep(1)

print("TEST: Log test complete", flush=True)