#!/usr/bin/env python3
"""
Check total rows for all symbols across all timeframes.
"""

import sys
import os

# Add patterns directory to path
sys.path.insert(0, '/home/hazem/Miando/patterns/json_split')

try:
    from common import get_cursor
    
    print("📊 Complete OHLC Data Inventory - All Symbols & Timeframes")
    print("="*80)
    
    with get_cursor(dict_cursor=False) as cur:
        # 1. Total rows by symbol and timeframe
        print("\n📈 Total Records by Symbol & Timeframe:")
        print("-" * 80)
        
        cur.execute("""
            SELECT 
                symbol,
                timeframe,
                COUNT(*) as total_records,
                MIN(open_time) as earliest_data,
                MAX(open_time) as latest_data,
                COUNT(rsi) as indicators_calculated,
                ROUND(COUNT(rsi) * 100.0 / COUNT(*), 1) as coverage_pct
            FROM ohlc_data 
            GROUP BY symbol, timeframe
            ORDER BY symbol, 
                     CASE timeframe 
                         WHEN 'M1' THEN 1 
                         WHEN 'M5' THEN 2 
                         WHEN 'M15' THEN 3 
                         WHEN 'M30' THEN 4 
                         WHEN 'H1' THEN 5 
                         WHEN 'H4' THEN 6 
                         WHEN 'D1' THEN 7 
                         ELSE 8 
                     END;
        """)
        
        all_data = cur.fetchall()
        
        print("Symbol   | TF  | Records | Earliest         | Latest           | Indicators | Coverage")
        print("-" * 80)
        
        current_symbol = ""
        symbol_totals = {}
        
        for row in all_data:
            symbol, tf, total, earliest, latest, indicators, coverage = row
            
            # Track symbol totals
            if symbol not in symbol_totals:
                symbol_totals[symbol] = 0
            symbol_totals[symbol] += total
            
            # Add separator for new symbol
            if symbol != current_symbol:
                if current_symbol != "":
                    print("-" * 80)
                current_symbol = symbol
            
            earliest_str = earliest.strftime('%Y-%m-%d %H:%M') if earliest else "N/A"
            latest_str = latest.strftime('%Y-%m-%d %H:%M') if latest else "N/A"
            
            print(f"{symbol:<8} | {tf:<3} | {total:>7,} | {earliest_str} | {latest_str} | {indicators:>10,} | {coverage:>6.1f}%")
        
        # 2. Summary by symbol
        print("\n" + "="*80)
        print("📊 SUMMARY - Total Records by Symbol:")
        print("-" * 50)
        
        total_all_records = 0
        for symbol, total in sorted(symbol_totals.items()):
            total_all_records += total
            print(f"{symbol:<8} | {total:>12,} records")
        
        print("-" * 50)
        print(f"{'TOTAL':<8} | {total_all_records:>12,} records")
        
        # 3. Summary by timeframe
        print("\n📊 SUMMARY - Total Records by Timeframe:")
        print("-" * 50)
        
        cur.execute("""
            SELECT 
                timeframe,
                COUNT(*) as total_records,
                COUNT(DISTINCT symbol) as symbols_count
            FROM ohlc_data 
            GROUP BY timeframe
            ORDER BY CASE timeframe 
                         WHEN 'M1' THEN 1 
                         WHEN 'M5' THEN 2 
                         WHEN 'M15' THEN 3 
                         WHEN 'M30' THEN 4 
                         WHEN 'H1' THEN 5 
                         WHEN 'H4' THEN 6 
                         WHEN 'D1' THEN 7 
                         ELSE 8 
                     END;
        """)
        
        timeframe_data = cur.fetchall()
        
        print("Timeframe | Total Records | Symbols")
        print("-" * 40)
        
        for row in timeframe_data:
            tf, total, symbols = row
            print(f"{tf:<9} | {total:>13,} | {symbols:>7}")
        
        # 4. Data density analysis
        print("\n📊 Data Density Analysis (Records per Day):")
        print("-" * 60)
        
        cur.execute("""
            SELECT 
                symbol,
                timeframe,
                COUNT(*) as total_records,
                EXTRACT(DAYS FROM (MAX(open_time) - MIN(open_time))) + 1 as days_span,
                ROUND(COUNT(*)::numeric / (EXTRACT(DAYS FROM (MAX(open_time) - MIN(open_time))) + 1), 1) as records_per_day
            FROM ohlc_data 
            GROUP BY symbol, timeframe
            HAVING COUNT(*) > 100
            ORDER BY records_per_day DESC;
        """)
        
        density_data = cur.fetchall()
        
        print("Symbol   | TF  | Records | Days | Records/Day")
        print("-" * 50)
        
        for row in density_data:
            symbol, tf, records, days, per_day = row
            print(f"{symbol:<8} | {tf:<3} | {records:>7,} | {days:>4.0f} | {per_day:>10.1f}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
