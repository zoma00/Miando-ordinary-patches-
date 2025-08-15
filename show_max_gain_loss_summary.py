#!/usr/bin/env python3
"""
Comprehensive summary of max gain/loss data from August 8, 2025.
"""

import sys
import os

# Add patterns directory to path
sys.path.insert(0, '/home/hazem/Miando/patterns/json_split')

from common import get_cursor, log_info, log_success

def show_comprehensive_summary():
    """Show comprehensive summary of max gain/loss data."""
    
    print("📊 MAX GAIN/LOSS SUMMARY FROM AUGUST 8, 2025")
    print("="*60)
    
    try:
        with get_cursor(dict_cursor=False) as cur:
            # Overall statistics
            cur.execute("""
                SELECT 
                    COUNT(*) as total_snapshots,
                    COUNT(max_gain_pct_1h) as calculated,
                    COUNT(*) - COUNT(max_gain_pct_1h) as missing,
                    MIN(snapshot_time) as earliest,
                    MAX(snapshot_time) as latest
                FROM trading_snapshots 
                WHERE snapshot_time >= '2025-08-08';
            """)
            
            total, calculated, missing, earliest, latest = cur.fetchone()
            coverage = (calculated / total * 100) if total > 0 else 0
            
            print(f"📈 OVERALL STATISTICS (from Aug 8, 2025):")
            print(f"   Total snapshots: {total}")
            print(f"   Calculated: {calculated}")
            print(f"   Missing: {missing}")
            print(f"   Coverage: {coverage:.1f}%")
            print(f"   Date range: {earliest} to {latest}")
            
            # By symbol breakdown
            print(f"\n📊 BY SYMBOL:")
            cur.execute("""
                SELECT symbol, 
                       COUNT(*) as total_snapshots,
                       COUNT(max_gain_pct_1h) as calculated,
                       COUNT(*) - COUNT(max_gain_pct_1h) as missing,
                       ROUND(AVG(max_gain_pct_1h), 4) as avg_gain,
                       ROUND(AVG(max_loss_pct_1h), 4) as avg_loss,
                       MAX(max_gain_pct_1h) as max_gain,
                       MIN(max_loss_pct_1h) as max_loss
                FROM trading_snapshots 
                WHERE snapshot_time >= '2025-08-08'
                GROUP BY symbol
                ORDER BY calculated DESC;
            """)
            
            symbol_data = cur.fetchall()
            
            print(f"{'Symbol':<8} | {'Total':<6} | {'Calc':<6} | {'Miss':<5} | {'Avg Gain':<9} | {'Avg Loss':<9} | {'Max Gain':<9} | {'Max Loss':<9}")
            print("-" * 85)
            
            for row in symbol_data:
                symbol, total, calculated, missing, avg_gain, avg_loss, max_gain, max_loss = row
                avg_gain_str = f"{avg_gain:+.4f}%" if avg_gain is not None else "N/A"
                avg_loss_str = f"{avg_loss:+.4f}%" if avg_loss is not None else "N/A"
                max_gain_str = f"{max_gain:+.4f}%" if max_gain is not None else "N/A"
                max_loss_str = f"{max_loss:+.4f}%" if max_loss is not None else "N/A"
                
                print(f"{symbol:<8} | {total:<6} | {calculated:<6} | {missing:<5} | {avg_gain_str:<9} | {avg_loss_str:<9} | {max_gain_str:<9} | {max_loss_str:<9}")
            
            # Recent samples
            print(f"\n📋 RECENT SAMPLES (Last 20 calculated):")
            cur.execute("""
                SELECT symbol, snapshot_time, max_gain_pct_1h, max_loss_pct_1h
                FROM trading_snapshots 
                WHERE max_gain_pct_1h IS NOT NULL 
                AND snapshot_time >= '2025-08-08'
                ORDER BY snapshot_time DESC 
                LIMIT 20;
            """)
            
            recent_data = cur.fetchall()
            
            print(f"{'Symbol':<8} | {'Timestamp':<17} | {'Max Gain':<10} | {'Max Loss':<10}")
            print("-" * 55)
            
            for row in recent_data:
                symbol, timestamp, gain, loss = row
                time_str = timestamp.strftime("%m-%d %H:%M") if hasattr(timestamp, 'strftime') else str(timestamp)[:11]
                gain_str = f"{float(gain):+.4f}%" if gain is not None else "N/A"
                loss_str = f"{float(loss):+.4f}%" if loss is not None else "N/A"
                print(f"{symbol:<8} | {time_str:<17} | {gain_str:<10} | {loss_str:<10}")
            
            print(f"\n✅ SUCCESS! Max gain/loss data has been calculated and saved to the database.")
            print(f"📊 Total records with data: {calculated}")
            
            if missing > 0:
                print(f"\n⚠️  Note: {missing} snapshots couldn't be calculated (likely due to insufficient future data)")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    show_comprehensive_summary()
