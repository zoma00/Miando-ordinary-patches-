#!/usr/bin/env python3
"""
Check max_gain_pct_1h coverage in ascending order to see what data is available.
"""

import sys
import os

# Add patterns directory to path
sys.path.insert(0, '/home/hazem/Miando/patterns/json_split')

try:
    from common import get_cursor
    
    print("📊 Max Gain/Loss Coverage Analysis (Ascending Order)")
    print("="*65)
    
    # 1. Show earliest calculated records
    print("\n🔍 EARLIEST Calculated Records (ascending order):")
    print("-" * 70)
    with get_cursor(dict_cursor=False) as cur:
        cur.execute("""
            SELECT symbol, snapshot_time, max_gain_pct_1h, max_loss_pct_1h
            FROM trading_snapshots 
            WHERE max_gain_pct_1h IS NOT NULL AND max_loss_pct_1h IS NOT NULL
            ORDER BY snapshot_time ASC
            LIMIT 15;
        """)
        
        early_records = cur.fetchall()
        
        if early_records:
            print("Symbol   | Timestamp            | Max Gain %   | Max Loss %")
            print("-" * 70)
            for row in early_records:
                symbol, timestamp, gain, loss = row
                time_str = timestamp.strftime("%Y-%m-%d %H:%M")
                gain_pct = gain * 100 if gain is not None else 0
                loss_pct = loss * 100 if loss is not None else 0
                print(f"{symbol:<8} | {time_str:<20} | {gain_pct:>+8.4f}%   | {loss_pct:>+8.4f}%")
        else:
            print("❌ No calculated records found!")
    
    # 2. Show latest calculated records
    print("\n🔍 LATEST Calculated Records (descending order):")
    print("-" * 70)
    with get_cursor(dict_cursor=False) as cur:
        cur.execute("""
            SELECT symbol, snapshot_time, max_gain_pct_1h, max_loss_pct_1h
            FROM trading_snapshots 
            WHERE max_gain_pct_1h IS NOT NULL AND max_loss_pct_1h IS NOT NULL
            ORDER BY snapshot_time DESC
            LIMIT 15;
        """)
        
        late_records = cur.fetchall()
        
        if late_records:
            print("Symbol   | Timestamp            | Max Gain %   | Max Loss %")
            print("-" * 70)
            for row in late_records:
                symbol, timestamp, gain, loss = row
                time_str = timestamp.strftime("%Y-%m-%d %H:%M")
                gain_pct = gain * 100 if gain is not None else 0
                loss_pct = loss * 100 if loss is not None else 0
                print(f"{symbol:<8} | {time_str:<20} | {gain_pct:>+8.4f}%   | {loss_pct:>+8.4f}%")
    
    # 3. Show coverage by date
    print("\n📅 Coverage by Date:")
    print("-" * 50)
    with get_cursor(dict_cursor=False) as cur:
        cur.execute("""
            SELECT 
                DATE(snapshot_time) as trade_date,
                symbol,
                COUNT(*) as total_snapshots,
                COUNT(max_gain_pct_1h) as calculated,
                COUNT(*) - COUNT(max_gain_pct_1h) as missing,
                ROUND(COUNT(max_gain_pct_1h) * 100.0 / COUNT(*), 1) as coverage_pct
            FROM trading_snapshots 
            WHERE ohlc_all_json IS NOT NULL
            GROUP BY DATE(snapshot_time), symbol
            ORDER BY trade_date ASC, symbol;
        """)
        
        coverage_data = cur.fetchall()
        
        print("Date       | Symbol   | Total | Calc | Miss | Coverage")
        print("-" * 50)
        
        for row in coverage_data:
            date, symbol, total, calculated, missing, coverage = row
            status = "✅" if missing == 0 else "⚠️" if coverage >= 80 else "❌"
            print(f"{date} | {symbol:<8} | {total:>5} | {calculated:>4} | {missing:>4} | {coverage:>6.1f}% {status}")
    
    # 4. Show time range of calculated data
    print("\n⏰ Time Range of Calculated Data:")
    print("-" * 40)
    with get_cursor(dict_cursor=False) as cur:
        cur.execute("""
            SELECT 
                symbol,
                MIN(snapshot_time) as earliest_calc,
                MAX(snapshot_time) as latest_calc,
                COUNT(*) as total_calculated
            FROM trading_snapshots 
            WHERE max_gain_pct_1h IS NOT NULL
            GROUP BY symbol
            ORDER BY symbol;
        """)
        
        range_data = cur.fetchall()
        
        for row in range_data:
            symbol, earliest, latest, count = row
            earliest_str = earliest.strftime("%Y-%m-%d %H:%M")
            latest_str = latest.strftime("%Y-%m-%d %H:%M")
            print(f"{symbol}: {count} records from {earliest_str} to {latest_str}")
    
    # 5. Show sample of NULL records (ascending order)
    print("\n🔍 Sample NULL Records (oldest first):")
    print("-" * 50)
    with get_cursor(dict_cursor=False) as cur:
        cur.execute("""
            SELECT symbol, snapshot_time, max_gain_pct_1h, max_loss_pct_1h
            FROM trading_snapshots 
            WHERE max_gain_pct_1h IS NULL OR max_loss_pct_1h IS NULL
            ORDER BY snapshot_time ASC
            LIMIT 10;
        """)
        
        null_records = cur.fetchall()
        
        if null_records:
            print("Symbol   | Timestamp            | Status")
            print("-" * 50)
            for row in null_records:
                symbol, timestamp, gain, loss = row
                time_str = timestamp.strftime("%Y-%m-%d %H:%M")
                print(f"{symbol:<8} | {time_str:<20} | NULL")
        else:
            print("✅ No NULL records found!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
