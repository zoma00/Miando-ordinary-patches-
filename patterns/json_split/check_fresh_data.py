#!/usr/bin/env python3
"""Quick check for fresh Pattern JSON data"""

from common import get_cursor
import json

with get_cursor(dict_cursor=True) as cur:
    cur.execute("""
        SELECT snapshot_time, 
               pattern_json->>'snapshot_time' as json_time, 
               pattern_json->>'session' as session, 
               pattern_json->>'spread' as spread
        FROM trading_snapshots 
        WHERE symbol = 'XAUUSD' AND pattern_json IS NOT NULL
        ORDER BY snapshot_time DESC 
        LIMIT 1
    """)
    result = cur.fetchone()
    if result:
        print('Latest Pattern JSON:')
        print(f'DB Timestamp: {result["snapshot_time"]}')
        print(f'JSON Timestamp: {result["json_time"]}')
        print(f'Session: {result["session"]}')
        print(f'Spread: {result["spread"]}')
        status = '✅ TODAY DATA' if '2025-08-09' in str(result['snapshot_time']) else '❌ OLD DATA'
        print(f'Status: {status}')
