#!/usr/bin/env python3
"""
Smart gap filler for max gain/loss calculations.
This script identifies which snapshots can actually be calculated and fills only those.
"""

import sys
import os
from datetime import datetime, timedelta

# Add patterns directory to path
sys.path.insert(0, '/home/hazem/Miando/patterns/json_split')

from max_gain_loss_calc import calculate_historical_batch
from common import get_cursor, log_info, log_success, log_error

def check_data_availability():
    """Check which snapshots can actually be calculated."""
    
    print("🔍 Analyzing data availability for max gain/loss calculations")
    print("="*70)
    
    try:
        with get_cursor(dict_cursor=True) as cur:
            # Find snapshots that need calculation
            cur.execute("""
                SELECT 
                    ts.symbol,
                    ts.snapshot_time,
                    ts.max_gain_pct_1h,
                    ts.max_loss_pct_1h
                FROM trading_snapshots ts
                WHERE ts.max_gain_pct_1h IS NULL 
                AND ts.ohlc_all_json IS NOT NULL
                ORDER BY ts.symbol, ts.snapshot_time;
            """)
            
            missing_snapshots = cur.fetchall()
            
            print(f"Found {len(missing_snapshots)} snapshots with NULL max gain/loss")
            
            if not missing_snapshots:
                print("✅ No missing calculations found!")
                return
            
            # Check OHLC data availability for each missing snapshot
            print("\n🔍 Checking OHLC data availability...")
            print("Symbol   | Snapshot Time        | Future Data | Status")
            print("-" * 65)
            
            calculable = []
            insufficient_data = []
            
            for snapshot in missing_snapshots:
                symbol = snapshot['symbol']
                snapshot_time = snapshot['snapshot_time']
                
                # Check if we have 60 minutes of future OHLC data
                future_time = snapshot_time + timedelta(hours=1)
                
                cur.execute("""
                    SELECT COUNT(*) as future_candles
                    FROM ohlc_data 
                    WHERE symbol = %s 
                    AND timeframe = 'M1'
                    AND open_time > %s 
                    AND open_time <= %s;
                """, (symbol, snapshot_time, future_time))
                
                result = cur.fetchone()
                future_candles = result['future_candles']
                
                # Format timestamp for display
                time_str = snapshot_time.strftime("%Y-%m-%d %H:%M")
                
                if future_candles >= 60:  # We need at least 60 minutes of data
                    status = "✅ READY"
                    calculable.append(snapshot)
                else:
                    status = f"❌ Only {future_candles}min"
                    insufficient_data.append(snapshot)
                
                print(f"{symbol:<8} | {time_str:<20} | {future_candles:>3} minutes | {status}")
            
            print(f"\n📊 Summary:")
            print(f"  ✅ Ready to calculate: {len(calculable)}")
            print(f"  ❌ Insufficient data: {len(insufficient_data)}")
            
            if len(calculable) > 0:
                print(f"\n🚀 Would you like to calculate the {len(calculable)} ready snapshots?")
                
                # Group by symbol for processing
                by_symbol = {}
                for snap in calculable:
                    symbol = snap['symbol']
                    if symbol not in by_symbol:
                        by_symbol[symbol] = []
                    by_symbol[symbol].append(snap)
                
                for symbol, snapshots in by_symbol.items():
                    print(f"  {symbol}: {len(snapshots)} snapshots ready")
                
                return by_symbol
            else:
                print("\n⚠️  No snapshots are ready for calculation due to insufficient future data.")
                print("    This is normal for recent snapshots - they need 60 minutes of future OHLC data.")
                
    except Exception as e:
        log_error(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()

def calculate_ready_snapshots(by_symbol):
    """Calculate only the snapshots that have sufficient data."""
    
    print(f"\n🚀 Starting calculations for ready snapshots...")
    print("="*50)
    
    total_processed = 0
    
    for symbol, snapshots in by_symbol.items():
        print(f"\n📊 Processing {symbol} ({len(snapshots)} ready snapshots)")
        print("-" * 40)
        
        # Process in smaller batches to avoid overwhelming the system
        batch_size = 10
        symbol_processed = 0
        
        for i in range(0, len(snapshots), batch_size):
            batch_snapshots = snapshots[i:i+batch_size]
            
            print(f"  Processing batch {i//batch_size + 1}: {len(batch_snapshots)} snapshots")
            
            try:
                # Use the existing batch calculation function
                batch_result = calculate_historical_batch(symbol, batch_size=len(batch_snapshots))
                
                if batch_result > 0:
                    symbol_processed += batch_result
                    total_processed += batch_result
                    print(f"  ✅ Batch completed: {batch_result} snapshots calculated")
                else:
                    print(f"  ⚠️  Batch completed: 0 snapshots calculated (may be already done)")
                
            except Exception as e:
                log_error(f"Error processing batch for {symbol}: {e}")
        
        log_success(f"{symbol}: {symbol_processed} snapshots processed")
    
    print(f"\n🎉 CALCULATION COMPLETE!")
    print(f"Total snapshots successfully calculated: {total_processed}")
    
    return total_processed

def show_final_status():
    """Show final status after calculations."""
    
    print(f"\n📊 Final Database Status:")
    print("="*40)
    
    try:
        with get_cursor(dict_cursor=False) as cur:
            cur.execute("""
                SELECT 
                    symbol,
                    COUNT(*) as total_snapshots,
                    COUNT(max_gain_pct_1h) as calculated,
                    COUNT(*) - COUNT(max_gain_pct_1h) as still_missing
                FROM trading_snapshots 
                WHERE ohlc_all_json IS NOT NULL
                GROUP BY symbol
                ORDER BY symbol;
            """)
            
            final_data = cur.fetchall()
        
        print("Symbol   | Total  | Calculated | Still Missing | Coverage")
        print("-" * 55)
        
        for row in final_data:
            symbol, total, calculated, missing = row
            coverage = (calculated / total) * 100 if total > 0 else 0
            status = "✅" if missing == 0 else "⚠️"
            print(f"{symbol:<8} | {total:<6} | {calculated:<10} | {missing:<13} | {coverage:>6.1f}% {status}")
            
    except Exception as e:
        log_error(f"Error showing final status: {e}")

if __name__ == "__main__":
    # Step 1: Analyze what can be calculated
    ready_snapshots = check_data_availability()
    
    if ready_snapshots:
        # Step 2: Calculate only the ready ones
        processed = calculate_ready_snapshots(ready_snapshots)
        
        # Step 3: Show final status
        show_final_status()
        
        if processed > 0:
            print(f"\n✅ Success! Calculated {processed} snapshots.")
            print("📝 Note: Remaining NULL values are likely recent snapshots")
            print("   that don't have 60 minutes of future OHLC data yet.")
        else:
            print(f"\n⚠️  No new calculations were made.")
            print("   This might mean the snapshots are already calculated")
            print("   or there are data availability issues.")
    else:
        print(f"\n📝 All missing snapshots require future OHLC data that isn't available yet.")
        print("   This is normal behavior - the system will calculate them automatically")
        print("   once enough future data becomes available.")
