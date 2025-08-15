#!/usr/bin/env python3
"""
Investigate why symbols have different record counts.
"""

import sys
import os

# Add patterns directory to path
sys.path.insert(0, '/home/hazem/Miando/patterns/json_split')

try:
    from common import get_cursor
    
    print("🔍 Data Collection Investigation - Why Different Record Counts?")
    print("="*70)
    
    with get_cursor(dict_cursor=False) as cur:
        # 1. Check data collection periods by symbol
        print("\n📅 Data Collection Periods by Symbol:")
        print("-" * 70)
        
        cur.execute("""
            SELECT 
                symbol,
                COUNT(*) as total_records,
                MIN(open_time) as first_record,
                MAX(open_time) as last_record,
                EXTRACT(DAYS FROM (MAX(open_time) - MIN(open_time))) + 1 as days_span
            FROM ohlc_data 
            GROUP BY symbol
            ORDER BY total_records DESC;
        """)
        
        symbol_data = cur.fetchall()
        
        print("Symbol   | Records | First Record     | Last Record      | Days")
        print("-" * 70)
        
        for row in symbol_data:
            symbol, records, first, last, days = row
            first_str = first.strftime('%Y-%m-%d %H:%M') if first else 'N/A'
            last_str = last.strftime('%Y-%m-%d %H:%M') if last else 'N/A'
            print(f"{symbol:<8} | {records:>7,} | {first_str} | {last_str} | {days:>4.0f}")
        
        # 2. Check M1 data specifically (where the big differences are)
        print("\n📊 M1 Timeframe Analysis:")
        print("-" * 60)
        
        cur.execute("""
            SELECT 
                symbol,
                COUNT(*) as m1_records,
                MIN(open_time) as first_m1,
                MAX(open_time) as last_m1,
                EXTRACT(DAYS FROM (MAX(open_time) - MIN(open_time))) + 1 as m1_days
            FROM ohlc_data 
            WHERE timeframe = 'M1'
            GROUP BY symbol
            ORDER BY m1_records DESC;
        """)
        
        m1_data = cur.fetchall()
        
        print("Symbol   | M1 Records | First M1         | Last M1          | Days")
        print("-" * 60)
        
        for row in m1_data:
            symbol, records, first, last, days = row
            first_str = first.strftime('%Y-%m-%d %H:%M') if first else 'N/A'
            last_str = last.strftime('%Y-%m-%d %H:%M') if last else 'N/A'
            print(f"{symbol:<8} | {records:>10,} | {first_str} | {last_str} | {days:>4.0f}")
        
        # 3. Check if there are different timeframes available per symbol
        print("\n📈 Timeframes Available by Symbol:")
        print("-" * 50)
        
        cur.execute("""
            SELECT 
                symbol,
                timeframe,
                COUNT(*) as records
            FROM ohlc_data 
            GROUP BY symbol, timeframe
            ORDER BY symbol, timeframe;
        """)
        
        tf_data = cur.fetchall()
        
        current_symbol = ""
        for row in tf_data:
            symbol, tf, records = row
            if symbol != current_symbol:
                if current_symbol != "":
                    print()
                print(f"{symbol}:")
                current_symbol = symbol
            print(f"  {tf}: {records:,} records")
        
        # 4. Check for data quality issues
        print(f"\n🔍 Data Quality Check:")
        print("-" * 40)
        
        cur.execute("""
            SELECT 
                symbol,
                COUNT(*) as total_records,
                COUNT(DISTINCT open_time, timeframe) as unique_time_tf,
                COUNT(*) - COUNT(DISTINCT open_time, timeframe) as duplicates
            FROM ohlc_data 
            GROUP BY symbol
            HAVING COUNT(*) - COUNT(DISTINCT open_time, timeframe) > 0
            ORDER BY duplicates DESC;
        """)
        
        dup_data = cur.fetchall()
        
        if dup_data:
            print("Found duplicate records:")
            print("Symbol   | Total | Unique | Duplicates")
            print("-" * 40)
            for row in dup_data:
                symbol, total, unique, dups = row
                print(f"{symbol:<8} | {total:>5} | {unique:>6} | {dups:>10}")
        else:
            print("✅ No duplicate records found")

        # 5. Check for missing timeframes
        print(f"\n📊 Missing Timeframes Analysis:")
        print("-" * 40)
        
        cur.execute("""
            WITH symbol_tf_matrix AS (
                SELECT DISTINCT s.symbol, tf.timeframe
                FROM (SELECT DISTINCT symbol FROM ohlc_data) s
                CROSS JOIN (SELECT DISTINCT timeframe FROM ohlc_data) tf
            ),
            actual_data AS (
                SELECT symbol, timeframe, COUNT(*) as records
                FROM ohlc_data
                GROUP BY symbol, timeframe
            )
            SELECT 
                m.symbol,
                m.timeframe,
                COALESCE(a.records, 0) as records
            FROM symbol_tf_matrix m
            LEFT JOIN actual_data a ON m.symbol = a.symbol AND m.timeframe = a.timeframe
            WHERE COALESCE(a.records, 0) = 0
            ORDER BY m.symbol, m.timeframe;
        """)
        
        missing_tf = cur.fetchall()
        
        if missing_tf:
            print("Missing timeframes:")
            print("Symbol   | Timeframe")
            print("-" * 20)
            for row in missing_tf:
                symbol, tf, records = row
                print(f"{symbol:<8} | {tf}")
        else:
            print("✅ All symbols have all timeframes")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
