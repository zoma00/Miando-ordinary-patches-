#!/usr/bin/env python3
"""Test script to demonstrate force-fresh vs regular mode"""

import sys
sys.path.append('.')

from common import get_latest_m1_time
from pattern_json_live import calculate_spread_from_latest_m1
from datetime import datetime

symbol = 'XAUUSD'

print("=== Testing get_latest_m1_time() Function ===")
print()

print("🔄 Regular Mode (may use cached data):")
regular_time = get_latest_m1_time(symbol, force_fresh=False)
print(f"Latest M1 time: {regular_time}")

print()
print("✨ Force Fresh Mode (bypasses caching):")
fresh_time = get_latest_m1_time(symbol, force_fresh=True)
print(f"Latest M1 time: {fresh_time}")

print()
print("=== Comparison ===")
if regular_time != fresh_time:
    print("❌ DIFFERENCE DETECTED!")
    print(f"Regular mode: {regular_time}")
    print(f"Fresh mode:   {fresh_time}")
    print("💡 This confirms the caching issue was resolved with force_fresh=True")
else:
    print("✅ Both modes return the same result")
    print(f"Time: {regular_time}")

print()
print("=== Testing Spread Calculation ===")
if fresh_time:
    regular_spread = calculate_spread_from_latest_m1(symbol, fresh_time, force_fresh=False)
    fresh_spread = calculate_spread_from_latest_m1(symbol, fresh_time, force_fresh=True)
    print(f"Regular spread: {regular_spread}")
    print(f"Fresh spread:   {fresh_spread}")
