#!/usr/bin/env python3
"""
Check max gain and max loss percentages for 1-hour timeframe in trading snapshots.
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Add the patterns directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'patterns', 'json_split'))

from common import get_cursor, log_info, log_error, log_success

def check_max_gain_loss_h1():
    """Check max gain/loss percentages for H1 timeframe in trading snapshots."""
    
    try:
        log_info("Checking max gain/loss percentages for H1 timeframe...")
        
        with get_cursor() as cur:
            # Query to get recent trading snapshots
            query = """
            SELECT 
                symbol,
                snapshot_time,
                ohlc_all_json
            FROM trading_snapshots 
            WHERE snapshot_time >= NOW() - INTERVAL '24 hours'
            AND ohlc_all_json IS NOT NULL
            ORDER BY snapshot_time DESC
            LIMIT 20;
            """
            
            cur.execute(query)
            rows = cur.fetchall()
            
            if not rows:
                log_error("No trading snapshots found in the last 24 hours")
                return
            
            log_success(f"Found {len(rows)} trading snapshots in the last 24 hours")
            print("\n" + "="*80)
            print("MAX GAIN/LOSS ANALYSIS FOR H1 TIMEFRAME")
            print("="*80)
            print(f"{'Symbol':<8} | {'Timestamp':<20} | {'Max Gain %':<12} | {'Max Loss %':<12}")
            print("-" * 80)
            
            found_data = False
            
            for row in rows:
                if hasattr(row, 'keys'):  # RealDictCursor
                    symbol = row['symbol']
                    snapshot_time = row['snapshot_time']
                    ohlc_json = row['ohlc_all_json']
                else:  # Regular cursor
                    symbol, snapshot_time, ohlc_json = row
                
                if ohlc_json:
                    try:
                        # Handle both string and dict cases
                        if isinstance(ohlc_json, str):
                            ohlc_data = json.loads(ohlc_json)
                        elif isinstance(ohlc_json, dict):
                            ohlc_data = ohlc_json
                        else:
                            ohlc_data = None
                        
                        # Check if H1 data exists
                        if ohlc_data and 'H1' in ohlc_data and isinstance(ohlc_data['H1'], dict):
                            h1_data = ohlc_data['H1']
                            
                            # Look for max gain/loss fields
                            max_gain = None
                            max_loss = None
                            
                            # Check various possible field names
                            gain_fields = ['max_gain_pct_1h', 'max_gain_pct', 'max_gain_percentage']
                            loss_fields = ['max_loss_pct_1h', 'max_loss_pct', 'max_loss_percentage']
                            
                            for field in gain_fields:
                                if field in h1_data:
                                    max_gain = h1_data[field]
                                    break
                            
                            for field in loss_fields:
                                if field in h1_data:
                                    max_loss = h1_data[field]
                                    break
                            
                            if max_gain is not None and max_loss is not None:
                                found_data = True
                                time_str = snapshot_time.strftime("%Y-%m-%d %H:%M")
                                print(f"{symbol:<8} | {time_str:<20} | {max_gain:+8.4f}%    | {max_loss:+8.4f}%")
                            else:
                                # Show what fields are available in H1 data
                                available_fields = list(h1_data.keys())
                                time_str = snapshot_time.strftime("%Y-%m-%d %H:%M")
                                print(f"{symbol:<8} | {time_str:<20} | No max gain/loss data")
                                print(f"         | Available H1 fields: {', '.join(available_fields[:5])}...")
                        else:
                            time_str = snapshot_time.strftime("%Y-%m-%d %H:%M")
                            print(f"{symbol:<8} | {time_str:<20} | No H1 data found")
                            
                            # Show what timeframes are available
                            if ohlc_data and isinstance(ohlc_data, dict):
                                timeframes = list(ohlc_data.keys())
                                print(f"         | Available timeframes: {', '.join(timeframes)}")
                            
                    except json.JSONDecodeError as e:
                        time_str = snapshot_time.strftime("%Y-%m-%d %H:%M")
                        print(f"{symbol:<8} | {time_str:<20} | JSON decode error: {e}")
                else:
                    time_str = snapshot_time.strftime("%Y-%m-%d %H:%M")
                    print(f"{symbol:<8} | {time_str:<20} | No OHLC JSON data")
            
            print("-" * 80)
            
            if not found_data:
                print("\n⚠️  No max gain/loss percentage data found in H1 timeframes")
                print("💡 This might indicate:")
                print("   1. The max_gain_loss_calc.py module needs to be run")
                print("   2. The field names might be different")
                print("   3. The calculation logic needs to be implemented")
                
                # Let's check if max_gain_loss_calc.py exists
                calc_script = os.path.join(os.path.dirname(__file__), 'patterns', 'json_split', 'max_gain_loss_calc.py')
                if os.path.exists(calc_script):
                    print(f"\n🔧 Found calculation script: {calc_script}")
                    print("   Try running: python patterns/json_split/max_gain_loss_calc.py")
                else:
                    print(f"\n❌ Calculation script not found: {calc_script}")
            else:
                print(f"\n✅ Successfully found max gain/loss data for recent snapshots")
        
    except Exception as e:
        log_error(f"Error checking max gain/loss data: {e}")
        return False

if __name__ == "__main__":
    check_max_gain_loss_h1()
