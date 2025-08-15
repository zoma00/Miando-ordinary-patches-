#!/usr/bin/env python3
"""
Display max gain/loss percentages from trading snapshots table.
"""

import sys
import os

# Add the patterns directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
patterns_dir = os.path.join(current_dir, 'patterns', 'json_split')
sys.path.insert(0, patterns_dir)

from common import get_cursor, log_info, log_error, log_success

def display_max_gain_loss_data():
    """Display max gain/loss percentages from trading snapshots."""
    
    try:
        log_info("Retrieving max gain/loss data from trading snapshots...")
        
        with get_cursor() as cur:
            # Query max gain/loss data
            cur.execute("""
                SELECT 
                    symbol,
                    snapshot_time,
                    max_gain_pct_1h,
                    max_loss_pct_1h
                FROM trading_snapshots 
                WHERE max_gain_pct_1h IS NOT NULL 
                AND max_loss_pct_1h IS NOT NULL
                ORDER BY snapshot_time DESC
                LIMIT 50;
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                print("❌ No max gain/loss data found in trading snapshots")
                return
            
            print("\n" + "="*70)
            print("MAX GAIN/LOSS DATA FROM TRADING SNAPSHOTS (1H)")
            print("="*70)
            print(f"{'Symbol':<8} | {'Timestamp':<20} | {'Max Gain %':<12} | {'Max Loss %':<12}")
            print("-" * 70)
            
            total_snapshots = 0
            avg_gain = 0
            avg_loss = 0
            max_gain_seen = float('-inf')
            max_loss_seen = float('inf')
            
            for row in rows:
                if hasattr(row, 'keys'):
                    symbol = row['symbol']
                    snapshot_time = row['snapshot_time']
                    max_gain = row['max_gain_pct_1h']
                    max_loss = row['max_loss_pct_1h']
                else:
                    symbol, snapshot_time, max_gain, max_loss = row
                
                if max_gain is not None and max_loss is not None:
                    time_str = snapshot_time.strftime("%Y-%m-%d %H:%M")
                    print(f"{symbol:<8} | {time_str:<20} | {max_gain:+8.4f}%    | {max_loss:+8.4f}%")
                    
                    # Calculate statistics
                    total_snapshots += 1
                    avg_gain += max_gain
                    avg_loss += max_loss
                    max_gain_seen = max(max_gain_seen, max_gain)
                    max_loss_seen = min(max_loss_seen, max_loss)
            
            print("-" * 70)
            
            if total_snapshots > 0:
                avg_gain /= total_snapshots
                avg_loss /= total_snapshots
                
                print(f"\n📊 STATISTICS (based on {total_snapshots} snapshots):")
                print(f"   Average Max Gain: {avg_gain:+.4f}%")
                print(f"   Average Max Loss: {avg_loss:+.4f}%")
                print(f"   Highest Gain:     {max_gain_seen:+.4f}%")
                print(f"   Lowest Loss:      {max_loss_seen:+.4f}%")
                print(f"   Average Range:    {avg_gain - avg_loss:.4f}%")
            
            log_success(f"Successfully retrieved {total_snapshots} records with max gain/loss data")
            
            # Also check recent data coverage
            cur.execute("""
                SELECT COUNT(*) as total_snapshots,
                       COUNT(max_gain_pct_1h) as with_gain_loss,
                       ROUND((COUNT(max_gain_pct_1h)::float / COUNT(*)::float) * 100, 2) as coverage_pct
                FROM trading_snapshots 
                WHERE snapshot_time >= NOW() - INTERVAL '24 hours';
            """)
            
            coverage_row = cur.fetchone()
            if coverage_row:
                if hasattr(coverage_row, 'keys'):
                    total = coverage_row['total_snapshots']
                    with_data = coverage_row['with_gain_loss']
                    coverage = coverage_row['coverage_pct']
                else:
                    total, with_data, coverage = coverage_row
                
                print(f"\n📈 DATA COVERAGE (last 24 hours):")
                print(f"   Total snapshots: {total}")
                print(f"   With gain/loss data: {with_data}")
                print(f"   Coverage: {coverage}%")
                
                if coverage < 100:
                    print(f"\n💡 To calculate missing data, run:")
                    print(f"   cd patterns/json_split && python max_gain_loss_calc.py")
            
    except Exception as e:
        log_error(f"Error retrieving max gain/loss data: {e}")

if __name__ == "__main__":
    display_max_gain_loss_data()
