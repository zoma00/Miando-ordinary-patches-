#!/usr/bin/env python3

import sys
import os

# Add patterns directory to path
sys.path.insert(0, '/home/hazem/Miando/patterns/json_split')

try:
    from common import get_cursor
    
    print("🔍 Max Gain/Loss Data in Trading Snapshots")
    print("="*50)
    
    with get_cursor(dict_cursor=False) as cur:  # Use regular cursor, not dict cursor
        cur.execute("""
            SELECT symbol, snapshot_time, max_gain_pct_1h, max_loss_pct_1h 
            FROM trading_snapshots 
            WHERE max_gain_pct_1h IS NOT NULL 
            ORDER BY snapshot_time DESC 
            LIMIT 10;
        """)
        
        rows = cur.fetchall()
        
        if rows:
            print("Symbol   | Timestamp            | Max Gain %   | Max Loss %")
            print("-" * 60)
            for row in rows:
                symbol, timestamp, gain, loss = row
                # Handle timestamp - could be string or datetime
                if hasattr(timestamp, 'strftime'):
                    time_str = timestamp.strftime("%Y-%m-%d %H:%M")
                else:
                    time_str = str(timestamp)[:16]  # Truncate if string
                
                gain_val = float(gain) if gain is not None else 0.0
                loss_val = float(loss) if loss is not None else 0.0
                print(f"{symbol:<8} | {time_str:<20} | {gain_val:+8.4f}%    | {loss_val:+8.4f}%")
        else:
            print("No data found with max gain/loss calculations")
            
        # Check total count
        cur.execute("SELECT COUNT(*) FROM trading_snapshots WHERE max_gain_pct_1h IS NOT NULL;")
        count = cur.fetchone()[0]
        print(f"\nTotal records with max gain/loss: {count}")
        
        # Check coverage in last 24 hours
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(max_gain_pct_1h) as with_data
            FROM trading_snapshots 
            WHERE snapshot_time >= NOW() - INTERVAL '24 hours';
        """)
        
        coverage_row = cur.fetchone()
        total_snapshots, snapshots_with_data = coverage_row
        coverage_pct = (snapshots_with_data / total_snapshots * 100) if total_snapshots > 0 else 0
        
        print(f"Coverage (24h): {snapshots_with_data}/{total_snapshots} snapshots ({coverage_pct:.1f}%)")
        
except Exception as e:
    print(f"Error: {e}")
