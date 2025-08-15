#!/usr/bin/env python3
"""
Validate the indikator_bot calculations by checking sample data and formulas.
"""

import sys
import os
import pandas as pd
import numpy as np

# Add patterns directory to path
sys.path.insert(0, '/home/hazem/Miando/patterns/json_split')

try:
    from common import get_cursor
    
    print("🔍 Indicator Calculation Validation")
    print("="*60)
    
    # 1. Get sample data for validation
    print("\n📊 Sample OHLC Data with Indicators:")
    print("-" * 100)
    with get_cursor(dict_cursor=False) as cur:
        cur.execute("""
            SELECT 
                symbol, timeframe, open_time, 
                open_price, high_price, low_price, close_price, volume,
                ROUND(rsi::numeric, 2) as rsi,
                ROUND(macd::numeric, 4) as macd,
                ROUND(adx::numeric, 2) as adx,
                ROUND(atr::numeric, 5) as atr,
                ROUND(bb_middle::numeric, 5) as bb_mid
            FROM ohlc_data 
            WHERE rsi IS NOT NULL 
            AND symbol = 'XAUUSD' 
            AND timeframe = 'M1'
            ORDER BY open_time DESC 
            LIMIT 10;
        """)
        
        recent_data = cur.fetchall()
        
        if recent_data:
            print("Time             | Open    | High    | Low     | Close   | Vol  | RSI  | MACD   | ADX  | ATR    | BB_Mid")
            print("-" * 100)
            for row in recent_data:
                symbol, tf, time, o, h, l, c, vol, rsi, macd, adx, atr, bb = row
                time_str = time.strftime('%H:%M')
                vol_str = f"{vol:4.0f}" if vol is not None else " N/A"
                rsi_str = f"{rsi:4.1f}" if rsi is not None else " N/A"
                macd_str = f"{macd:6.4f}" if macd is not None else "  N/A"
                adx_str = f"{adx:4.1f}" if adx is not None else " N/A"
                atr_str = f"{atr:6.5f}" if atr is not None else "   N/A"
                bb_str = f"{bb:7.2f}" if bb is not None else "   N/A"
                
                print(f"{time_str}       | {o:7.2f} | {h:7.2f} | {l:7.2f} | {c:7.2f} | {vol_str} | {rsi_str} | {macd_str} | {adx_str} | {atr_str} | {bb_str}")
        else:
            print("❌ No recent data with indicators found!")
    
    # 2. Manual RSI calculation validation
    print("\n🧮 Manual RSI Calculation Check:")
    print("-" * 50)
    with get_cursor(dict_cursor=False) as cur:
        cur.execute("""
            SELECT open_time, close_price, rsi
            FROM ohlc_data 
            WHERE symbol = 'XAUUSD' 
            AND timeframe = 'M1'
            AND rsi IS NOT NULL
            ORDER BY open_time DESC 
            LIMIT 20;
        """)
        
        rsi_data = cur.fetchall()
        
        if len(rsi_data) >= 15:
            # Get last 15 close prices for RSI calculation
            closes = [row[1] for row in reversed(rsi_data[:15])]
            stored_rsi = rsi_data[0][2]  # Most recent RSI from DB
            
            # Manual RSI calculation
            deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
            gains = [max(0, delta) for delta in deltas]
            losses = [max(0, -delta) for delta in deltas]
            
            # Simple moving average approach (14 period)
            avg_gain = sum(gains) / len(gains)
            avg_loss = sum(losses) / len(losses)
            
            if avg_loss != 0:
                rs = avg_gain / avg_loss
                manual_rsi = 100 - (100 / (1 + rs))
                
                print(f"Stored RSI:    {stored_rsi:.2f}")
                print(f"Manual RSI:    {manual_rsi:.2f}")
                print(f"Difference:    {abs(stored_rsi - manual_rsi):.2f}")
                
                if abs(stored_rsi - manual_rsi) < 5:
                    print("✅ RSI calculation appears correct")
                else:
                    print("⚠️ RSI calculation may have issues")
            else:
                print("⚠️ Cannot validate RSI - no losses in period")
        else:
            print("❌ Not enough data for RSI validation")
    
    # 3. Check for suspicious patterns
    print("\n🔍 Data Quality Checks:")
    print("-" * 40)
    with get_cursor(dict_cursor=False) as cur:
        # Check for identical prices (suspicious)
        cur.execute("""
            SELECT symbol, timeframe, COUNT(*) as count
            FROM ohlc_data 
            WHERE open_price = high_price 
            AND high_price = low_price 
            AND low_price = close_price
            AND rsi IS NOT NULL
            GROUP BY symbol, timeframe
            HAVING COUNT(*) > 10
            ORDER BY count DESC;
        """)
        
        identical_data = cur.fetchall()
        
        if identical_data:
            print("⚠️ Found suspicious identical OHLC prices:")
            for symbol, tf, count in identical_data:
                print(f"  {symbol} {tf}: {count} records with identical OHLC")
        else:
            print("✅ No suspicious identical OHLC patterns found")
        
        # Check RSI range
        cur.execute("""
            SELECT 
                MIN(rsi) as min_rsi,
                MAX(rsi) as max_rsi,
                COUNT(CASE WHEN rsi < 0 OR rsi > 100 THEN 1 END) as invalid_rsi
            FROM ohlc_data 
            WHERE rsi IS NOT NULL;
        """)
        
        rsi_stats = cur.fetchone()
        min_rsi, max_rsi, invalid_rsi = rsi_stats
        
        print(f"\nRSI Range: {min_rsi:.2f} to {max_rsi:.2f}")
        if invalid_rsi > 0:
            print(f"⚠️ Found {invalid_rsi} RSI values outside 0-100 range")
        else:
            print("✅ All RSI values within valid range (0-100)")
    
    # 4. Check calculation consistency
    print("\n🔄 Calculation Consistency Check:")
    print("-" * 45)
    with get_cursor(dict_cursor=False) as cur:
        # Check if indicators are being calculated for recent data
        cur.execute("""
            SELECT 
                symbol,
                timeframe,
                MAX(open_time) as latest_data,
                MAX(CASE WHEN rsi IS NOT NULL THEN open_time END) as latest_indicators
            FROM ohlc_data 
            GROUP BY symbol, timeframe
            HAVING MAX(open_time) > MAX(CASE WHEN rsi IS NOT NULL THEN open_time END)
            ORDER BY symbol, timeframe;
        """)
        
        lag_data = cur.fetchall()
        
        if lag_data:
            print("⚠️ Indicators lagging behind data:")
            for symbol, tf, latest_data, latest_indicators in lag_data:
                if latest_indicators:
                    lag_minutes = (latest_data - latest_indicators).total_seconds() / 60
                    print(f"  {symbol} {tf}: {lag_minutes:.0f} minutes behind")
                else:
                    print(f"  {symbol} {tf}: No indicators calculated yet")
        else:
            print("✅ Indicators are up-to-date with latest data")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
