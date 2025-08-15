#!/usr/bin/env python3
"""
Direct SQL query to check all missing indicators across all symbols.
"""

import sys
import os

# Add patterns directory to path
sys.path.insert(0, '/home/hazem/Miando/patterns/json_split')

try:
    from common import get_cursor
    
    print("🔍 COMPLETE Missing Indicators Analysis")
    print("="*80)
    
    with get_cursor(dict_cursor=False) as cur:
        # 1. All symbols/timeframes with missing indicators
        print("\n📊 ALL Symbols with Missing Indicators:")
        print("-" * 80)
        
        cur.execute("""
            SELECT 
                symbol,
                timeframe,
                COUNT(*) as total_records,
                COUNT(rsi) as rsi_calculated,
                COUNT(*) - COUNT(rsi) as rsi_missing,
                ROUND(COUNT(rsi) * 100.0 / COUNT(*), 1) as coverage_pct
            FROM ohlc_data 
            GROUP BY symbol, timeframe
            HAVING COUNT(*) - COUNT(rsi) > 0
            ORDER BY rsi_missing DESC;
        """)
        
        missing_data = cur.fetchall()
        
        print("Symbol   | TF  | Total | RSI Calc | Missing | Coverage%")
        print("-" * 60)
        
        total_missing = 0
        for row in missing_data:
            symbol, tf, total, calculated, missing, coverage = row
            total_missing += missing
            print(f"{symbol:<8} | {tf:<3} | {total:>5} | {calculated:>8} | {missing:>7} | {coverage:>8.1f}%")
        
        print(f"\nTOTAL missing RSI calculations: {total_missing:,}")
        
        # 2. Recent data (last 24 hours)
        print("\n📅 Missing Indicators - Last 24 Hours:")
        print("-" * 60)
        
        cur.execute("""
            SELECT 
                symbol,
                timeframe,
                COUNT(*) as total_records,
                COUNT(rsi) as rsi_calculated,
                COUNT(*) - COUNT(rsi) as rsi_missing
            FROM ohlc_data 
            WHERE open_time >= NOW() - INTERVAL '24 hours'
            GROUP BY symbol, timeframe
            HAVING COUNT(*) - COUNT(rsi) > 0
            ORDER BY rsi_missing DESC;
        """)
        
        recent_missing = cur.fetchall()
        
        if recent_missing:
            print("Symbol   | TF  | Total | RSI Calc | Missing")
            print("-" * 45)
            
            for row in recent_missing:
                symbol, tf, total, calculated, missing = row
                print(f"{symbol:<8} | {tf:<3} | {total:>5} | {calculated:>8} | {missing:>7}")
        else:
            print("✅ No missing indicators in last 24 hours!")
        
        # 3. Check by date range
        print("\n📅 Missing Indicators by Date:")
        print("-" * 50)
        
        cur.execute("""
            SELECT 
                DATE(open_time) as trade_date,
                COUNT(*) as total_records,
                COUNT(rsi) as rsi_calculated,
                COUNT(*) - COUNT(rsi) as rsi_missing
            FROM ohlc_data 
            WHERE open_time >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY DATE(open_time)
            ORDER BY trade_date DESC;
        """)
        
        daily_missing = cur.fetchall()
        
        print("Date       | Total | RSI Calc | Missing")
        print("-" * 40)
        
        for row in daily_missing:
            date, total, calculated, missing = row
            print(f"{date} | {total:>5} | {calculated:>8} | {missing:>7}")
        
        # 4. Symbols that need immediate attention
        print("\n🚨 Priority Symbols (>1000 missing indicators):")
        print("-" * 60)
        
        cur.execute("""
            SELECT 
                symbol,
                timeframe,
                COUNT(*) - COUNT(rsi) as rsi_missing,
                MAX(open_time) as latest_data,
                MAX(CASE WHEN rsi IS NOT NULL THEN open_time END) as latest_indicators
            FROM ohlc_data 
            GROUP BY symbol, timeframe
            HAVING COUNT(*) - COUNT(rsi) > 1000
            ORDER BY rsi_missing DESC;
        """)
        
        priority_data = cur.fetchall()
        
        if priority_data:
            print("Symbol   | TF  | Missing | Latest Data      | Latest Indicators")
            print("-" * 60)
            
            for row in priority_data:
                symbol, tf, missing, latest_data, latest_indicators = row
                latest_data_str = latest_data.strftime('%m-%d %H:%M') if latest_data else "N/A"
                latest_ind_str = latest_indicators.strftime('%m-%d %H:%M') if latest_indicators else "NONE"
                
                print(f"{symbol:<8} | {tf:<3} | {missing:>7} | {latest_data_str:<16} | {latest_ind_str}")
        else:
            print("✅ No symbols with >1000 missing indicators!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
