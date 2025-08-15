#!/usr/bin/env python3
"""
Calculate max gain/loss for missing snapshots from August 8, 2025.
This script runs once and stops when complete.
"""

import sys
import os

# Add patterns directory to path
sys.path.insert(0, '/home/hazem/Miando/patterns/json_split')

from max_gain_loss_calc import calculate_historical_batch
from common import get_cursor, log_info, log_success, log_error

def calculate_missing_from_date(start_date='2025-08-08'):
    """Calculate missing max gain/loss data from a specific date."""
    
    print(f"🔍 Calculating max gain/loss data from {start_date}")
    print("="*60)
    
    try:
        # Get symbols that need calculation
        with get_cursor(dict_cursor=False) as cur:
            cur.execute("""
                SELECT symbol, 
                       COUNT(*) as total_snapshots,
                       COUNT(max_gain_pct_1h) as calculated,
                       COUNT(*) - COUNT(max_gain_pct_1h) as missing
                FROM trading_snapshots 
                WHERE snapshot_time >= %s
                AND ohlc_all_json IS NOT NULL
                GROUP BY symbol
                HAVING COUNT(*) - COUNT(max_gain_pct_1h) > 0
                ORDER BY missing DESC;
            """, (start_date,))
            
            symbols_data = cur.fetchall()
        
        if not symbols_data:
            print("✅ No missing calculations found!")
            return
        
        print("Symbol   | Total  | Calc   | Missing")
        print("-" * 35)
        
        total_missing = 0
        for row in symbols_data:
            symbol, total, calculated, missing = row
            print(f"{symbol:<8} | {total:<6} | {calculated:<6} | {missing:<7}")
            total_missing += missing
        
        print(f"\nTotal missing calculations: {total_missing}")
        print("\n🚀 Starting calculations...")
        
        # Process each symbol
        total_processed = 0
        for row in symbols_data:
            symbol, total, calculated, missing = row
            
            print(f"\n📊 Processing {symbol} ({missing} missing calculations)")
            print("-" * 40)
            
            # Calculate in batches until done
            symbol_processed = 0
            while True:
                batch_result = calculate_historical_batch(symbol, batch_size=25)
                
                if batch_result == 0:
                    break  # No more to process
                
                symbol_processed += batch_result
                total_processed += batch_result
                
                print(f"  ✅ Batch completed: {batch_result} snapshots")
                
                # Safety limit to prevent infinite loops
                if symbol_processed >= missing + 5:
                    break
            
            log_success(f"{symbol}: {symbol_processed} snapshots processed")
        
        print(f"\n🎉 CALCULATION COMPLETE!")
        print(f"Total snapshots processed: {total_processed}")
        
        # Final verification
        print(f"\n📊 Final verification:")
        with get_cursor(dict_cursor=False) as cur:
            cur.execute("""
                SELECT symbol, 
                       COUNT(*) as total_snapshots,
                       COUNT(max_gain_pct_1h) as calculated,
                       COUNT(*) - COUNT(max_gain_pct_1h) as missing
                FROM trading_snapshots 
                WHERE snapshot_time >= %s
                GROUP BY symbol
                ORDER BY symbol;
            """, (start_date,))
            
            final_data = cur.fetchall()
        
        print("Symbol   | Total  | Calc   | Missing")
        print("-" * 35)
        
        for row in final_data:
            symbol, total, calculated, missing = row
            status = "✅" if missing == 0 else "⚠️"
            print(f"{symbol:<8} | {total:<6} | {calculated:<6} | {missing:<7} {status}")
        
    except Exception as e:
        log_error(f"Error during calculation: {e}")

if __name__ == "__main__":
    calculate_missing_from_date('2025-08-08')
