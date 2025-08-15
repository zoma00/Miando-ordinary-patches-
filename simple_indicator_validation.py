#!/usr/bin/env python3
"""
Simple indicator validation without pandas dependency.
"""

import sys
import os

# Add patterns directory to path
sys.path.insert(0, '/home/hazem/Miando/patterns/json_split')

try:
    from common import get_cursor
    
    print("🔍 Indicator Bot Calculation Validation")
    print("="*60)
    
    # 1. Check recent indicator calculations
    print("\n📊 Recent Indicator Data (XAUUSD M1):")
    print("-" * 85)
    with get_cursor(dict_cursor=False) as cur:
        cur.execute("""
            SELECT 
                open_time, 
                close_price,
                ROUND(rsi::numeric, 2) as rsi,
                ROUND(macd::numeric, 4) as macd,
                ROUND(adx::numeric, 2) as adx,
                ROUND(atr::numeric, 5) as atr
            FROM ohlc_data 
            WHERE symbol = 'XAUUSD' 
            AND timeframe = 'M1'
            AND rsi IS NOT NULL
            ORDER BY open_time DESC 
            LIMIT 10;
        """)
        
        recent_data = cur.fetchall()
        
        if recent_data:
            print("Time             | Close     | RSI   | MACD     | ADX   | ATR")
            print("-" * 85)
            for row in recent_data:
                time, close, rsi, macd, adx, atr = row
                time_str = time.strftime('%Y-%m-%d %H:%M')
                
                rsi_str = f"{rsi:5.1f}" if rsi is not None else "  N/A"
                macd_str = f"{macd:8.4f}" if macd is not None else "    N/A"
                adx_str = f"{adx:5.1f}" if adx is not None else "  N/A"
                atr_str = f"{atr:7.5f}" if atr is not None else "   N/A"
                
                print(f"{time_str} | {close:9.2f} | {rsi_str} | {macd_str} | {adx_str} | {atr_str}")
        else:
            print("❌ No recent XAUUSD M1 data with indicators found!")
    
    # 2. Check calculation coverage by symbol/timeframe
    print("\n📈 Current Indicator Coverage by Symbol:")
    print("-" * 70)
    with get_cursor(dict_cursor=False) as cur:
        cur.execute("""
            SELECT 
                symbol,
                timeframe,
                COUNT(*) as total_records,
                COUNT(rsi) as rsi_calculated,
                MAX(open_time) as latest_data,
                MAX(CASE WHEN rsi IS NOT NULL THEN open_time END) as latest_indicators,
                ROUND(COUNT(rsi) * 100.0 / COUNT(*), 1) as coverage_pct
            FROM ohlc_data 
            GROUP BY symbol, timeframe
            HAVING COUNT(rsi) > 0
            ORDER BY latest_indicators DESC
            LIMIT 15;
        """)
        
        coverage_data = cur.fetchall()
        
        print("Symbol   | TF  | Total | RSI Calc | Latest Data      | Latest Indicators | Cov%")
        print("-" * 70)
        
        for row in coverage_data:
            symbol, tf, total, rsi_calc, latest_data, latest_indicators, coverage = row
            
            latest_data_str = latest_data.strftime('%m-%d %H:%M') if latest_data else "N/A"
            latest_ind_str = latest_indicators.strftime('%m-%d %H:%M') if latest_indicators else "N/A"
            
            print(f"{symbol:<8} | {tf:<3} | {total:>5} | {rsi_calc:>8} | {latest_data_str:<16} | {latest_ind_str:<17} | {coverage:>4.1f}%")
    
    # 3. Check for data quality issues
    print("\n🔍 Data Quality Assessment:")
    print("-" * 50)
    with get_cursor(dict_cursor=False) as cur:
        # Check RSI range validity
        cur.execute("""
            SELECT 
                COUNT(*) as total_rsi,
                COUNT(CASE WHEN rsi < 0 OR rsi > 100 THEN 1 END) as invalid_rsi,
                MIN(rsi) as min_rsi,
                MAX(rsi) as max_rsi,
                AVG(rsi) as avg_rsi
            FROM ohlc_data 
            WHERE rsi IS NOT NULL;
        """)
        
        rsi_stats = cur.fetchone()
        total_rsi, invalid_rsi, min_rsi, max_rsi, avg_rsi = rsi_stats
        
        print(f"RSI Statistics:")
        print(f"  Total RSI values: {total_rsi}")
        print(f"  Invalid RSI (outside 0-100): {invalid_rsi}")
        print(f"  RSI Range: {min_rsi:.2f} to {max_rsi:.2f}")
        print(f"  Average RSI: {avg_rsi:.2f}")
        
        if invalid_rsi == 0:
            print("  ✅ All RSI values are within valid range")
        else:
            print(f"  ⚠️ Found {invalid_rsi} invalid RSI values")
        
        # Check for identical OHLC (suspicious test data)
        cur.execute("""
            SELECT COUNT(*) as identical_count
            FROM ohlc_data 
            WHERE open_price = high_price 
            AND high_price = low_price 
            AND low_price = close_price
            AND rsi IS NOT NULL;
        """)
        
        identical_count = cur.fetchone()[0]
        
        print(f"\nOHLC Data Quality:")
        if identical_count > 0:
            print(f"  ⚠️ Found {identical_count} records with identical OHLC prices (possible test data)")
        else:
            print(f"  ✅ No suspicious identical OHLC patterns found")
    
    # 4. Check calculation logic issues
    print("\n🧮 Technical Indicator Validation:")
    print("-" * 50)
    with get_cursor(dict_cursor=False) as cur:
        # Check if ATR is reasonable (should be > 0 for normal market data)
        cur.execute("""
            SELECT 
                COUNT(CASE WHEN atr <= 0 THEN 1 END) as zero_atr,
                COUNT(CASE WHEN atr IS NOT NULL THEN 1 END) as total_atr,
                AVG(atr) as avg_atr,
                MAX(atr) as max_atr
            FROM ohlc_data 
            WHERE atr IS NOT NULL;
        """)
        
        atr_stats = cur.fetchone()
        zero_atr, total_atr, avg_atr, max_atr = atr_stats
        
        print(f"ATR (Average True Range):")
        print(f"  Total ATR values: {total_atr}")
        print(f"  Zero/negative ATR: {zero_atr}")
        print(f"  Average ATR: {avg_atr:.5f}")
        print(f"  Max ATR: {max_atr:.5f}")
        
        if zero_atr == 0:
            print("  ✅ All ATR values are positive (normal)")
        else:
            print(f"  ⚠️ Found {zero_atr} zero/negative ATR values")
    
    # 5. Check bot processing status
    print("\n🤖 Indikator Bot Status:")
    print("-" * 30)
    with get_cursor(dict_cursor=False) as cur:
        # Find records that need indicator calculation
        cur.execute("""
            SELECT 
                symbol,
                timeframe,
                COUNT(*) as total_records,
                COUNT(CASE WHEN rsi IS NULL THEN 1 END) as missing_rsi
            FROM ohlc_data 
            WHERE open_time >= CURRENT_DATE - INTERVAL '3 days'
            GROUP BY symbol, timeframe
            HAVING COUNT(CASE WHEN rsi IS NULL THEN 1 END) > 0
            ORDER BY missing_rsi DESC
            LIMIT 10;
        """)
        
        missing_data = cur.fetchall()
        
        if missing_data:
            print("Symbols with missing indicators (last 3 days):")
            print("Symbol   | TF  | Total | Missing RSI")
            print("-" * 40)
            for symbol, tf, total, missing in missing_data:
                print(f"{symbol:<8} | {tf:<3} | {total:>5} | {missing:>11}")
        else:
            print("✅ All recent data has indicators calculated")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
