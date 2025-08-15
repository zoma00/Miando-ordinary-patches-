#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Force Fresh Pattern JSON Generation
Manually create a Pattern JSON with today's latest data to resolve caching issue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from common import get_cursor, log_info, log_success, log_error
import json

def force_fresh_pattern_json():
    """Force generate Pattern JSON with absolute latest data"""
    try:
        log_info("🔄 FORCING Fresh Pattern JSON Generation...")
        
        with get_cursor(dict_cursor=True) as cur:
            # Get ABSOLUTE latest M1 data (bypass any caching)
            cur.execute("""
                SELECT 
                    symbol,
                    open_time,
                    close_price,
                    high_price,
                    low_price,
                    open_time::date as data_date,
                    EXTRACT(hour FROM open_time) as utc_hour
                FROM ohlc_data
                WHERE symbol = 'XAUUSD' AND timeframe = 'M1'
                ORDER BY open_time DESC
                LIMIT 1
            """)
            
            latest = cur.fetchone()
            if not latest:
                log_error("No M1 data found")
                return
                
            log_info(f"📅 Latest M1 data: {latest['open_time']} (Date: {latest['data_date']})")
            
            # Calculate fresh spread
            spread = round(max(0.01, (float(latest['high_price']) - float(latest['low_price'])) * 0.1), 2)
            
            # Determine session
            hour = int(latest['utc_hour'])
            if 22 <= hour <= 23 or 0 <= hour <= 6:
                session = "Sydney"
            elif 7 <= hour <= 14:
                session = "London"
            elif 15 <= hour <= 21:
                session = "New York"
            else:
                session = "Unknown"
                
            log_info(f"🌏 Session: {session} (Hour: {hour})")
            log_info(f"💰 Spread: {spread}")
            
            # Create minimal fresh Pattern JSON
            fresh_pattern_json = {
                "symbol": "XAUUSD",
                "snapshot_time": latest['open_time'].isoformat(),
                "session": session,
                "spread": spread,
                "volatility": "fresh_data",
                "news_event": False,
                "data_freshness": "force_generated",
                "generation_time": datetime.utcnow().isoformat()
            }
            
            # Insert fresh Pattern JSON
            json_string = json.dumps(fresh_pattern_json)
            cur.execute("""
                INSERT INTO trading_snapshots (symbol, snapshot_time, snapshot_json, pattern_json)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (symbol, snapshot_time) 
                DO UPDATE SET 
                    pattern_json = EXCLUDED.pattern_json,
                    snapshot_json = EXCLUDED.snapshot_json
            """, ("XAUUSD", latest['open_time'], json_string, json_string))
            
            log_success(f"✅ Fresh Pattern JSON created for {latest['open_time']}")
            log_success(f"📊 Data: Session={session}, Spread={spread}, Date={latest['data_date']}")
            
    except Exception as e:
        log_error(f"Failed to force fresh Pattern JSON: {e}")

if __name__ == "__main__":
    force_fresh_pattern_json()
