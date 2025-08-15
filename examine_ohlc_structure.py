#!/usr/bin/env python3
"""
Examine the actual structure of OHLC data in trading snapshots.
"""

import sys
import os
import json

# Add the patterns directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'patterns', 'json_split'))

from common import get_cursor, log_info, log_error, log_success

def examine_ohlc_structure():
    """Examine the actual structure of OHLC data in trading snapshots."""
    
    try:
        log_info("Examining OHLC data structure...")
        
        with get_cursor() as cur:
            # Get one recent snapshot to examine structure
            query = """
            SELECT 
                symbol,
                snapshot_time,
                ohlc_all_json
            FROM trading_snapshots 
            WHERE ohlc_all_json IS NOT NULL
            ORDER BY snapshot_time DESC
            LIMIT 1;
            """
            
            cur.execute(query)
            row = cur.fetchone()
            
            if not row:
                log_error("No trading snapshots found")
                return
            
            if hasattr(row, 'keys'):  # RealDictCursor
                symbol = row['symbol']
                snapshot_time = row['snapshot_time']
                ohlc_json = row['ohlc_all_json']
            else:  # Regular cursor
                symbol, snapshot_time, ohlc_json = row
            
            print(f"\n📊 OHLC Data Structure Analysis")
            print(f"Symbol: {symbol}")
            print(f"Timestamp: {snapshot_time}")
            print("="*60)
            
            if ohlc_json:
                # Handle both string and dict cases
                if isinstance(ohlc_json, str):
                    ohlc_data = json.loads(ohlc_json)
                elif isinstance(ohlc_json, dict):
                    ohlc_data = ohlc_json
                else:
                    print("❌ Unknown data type for ohlc_json")
                    return
                
                # Pretty print the structure
                print("🔍 Top-level keys:")
                for key in ohlc_data.keys():
                    print(f"  - {key}: {type(ohlc_data[key])}")
                
                # If there's an 'ohlc' key, examine its structure
                if 'ohlc' in ohlc_data:
                    print(f"\n🔍 OHLC sub-structure:")
                    ohlc_sub = ohlc_data['ohlc']
                    if isinstance(ohlc_sub, dict):
                        for timeframe, data in ohlc_sub.items():
                            print(f"  - {timeframe}: {type(data)}")
                            if isinstance(data, dict) and data:
                                sample_keys = list(data.keys())[:5]
                                print(f"    Sample keys: {sample_keys}")
                                
                                # Check for max gain/loss fields
                                gain_loss_keys = [k for k in data.keys() if 'gain' in k.lower() or 'loss' in k.lower()]
                                if gain_loss_keys:
                                    print(f"    📈 Gain/Loss fields: {gain_loss_keys}")
                                    for key in gain_loss_keys:
                                        print(f"      {key}: {data[key]}")
                
                # Show a sample of the full structure (limited)
                print(f"\n📋 Full structure sample:")
                print(json.dumps(ohlc_data, indent=2, default=str)[:1000] + "...")
                
        log_success("Structure examination completed")
        
    except Exception as e:
        log_error(f"Error examining OHLC structure: {e}")

if __name__ == "__main__":
    examine_ohlc_structure()
